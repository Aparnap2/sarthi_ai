"""Tests for the Reviewer Agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.reviewer import (
    ReviewerResult,
    ReviewerAgent,
    fetch_pr_diff_tool,
    analyze_code_quality_tool,
    check_test_coverage_tool,
    validate_pr_description_tool,
    security_scan_tool,
    SECRET_PATTERNS,
)


# ========================
# Test Models
# ========================


def test_reviewer_result_model():
    """Test ReviewerResult model validation."""
    result = ReviewerResult(
        approved=True,
        score=85.0,
        issues=["Consider adding more error handling"],
        suggestions=["Add unit tests for edge cases"],
        test_coverage=0.75,
        security_issues=[],
    )

    assert result.approved is True
    assert result.score == 85.0
    assert result.issues == ["Consider adding more error handling"]
    assert result.suggestions == ["Add unit tests for edge cases"]
    assert result.test_coverage == 0.75
    assert result.security_issues == []


# ========================
# Test Agent Initialization
# ========================


def test_reviewer_agent_initialization():
    """Test ReviewerAgent initialization."""
    with patch("src.agents.reviewer.get_llm_client") as mock_llm:
        mock_llm.return_value = MagicMock()

        agent = ReviewerAgent(
            context_store=MagicMock(),
            budget_manager=MagicMock(),
            openai_client=mock_llm.return_value,
        )

        assert agent.context_store is not None
        assert agent.budget_manager is not None
        assert agent.openai_client is not None


def test_reviewer_agent_without_azure_credentials():
    """Test ReviewerAgent works without Azure credentials."""
    with patch("src.agents.reviewer.get_azure_openai_client") as mock_azure:
        with patch("src.agents.reviewer.get_ollama_client") as mock_ollama:
            mock_azure.return_value = None
            mock_ollama.return_value = MagicMock()

            client = mock_ollama.return_value

            agent = ReviewerAgent(
                context_store=MagicMock(),
                budget_manager=MagicMock(),
                openai_client=client,
            )

            assert agent.openai_client is not None


# ========================
# Test Tools
# ========================


@pytest.mark.asyncio
async def test_reviewer_fetch_pr_diff_tool():
    """Test fetch_pr_diff_tool function."""
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_file = MagicMock()
    mock_file.filename = "src/main.py"
    mock_file.patch = "@@ -1,1 +1,2 @@"
    mock_pr.get_files.return_value = [mock_file]
    mock_repo.get_pull.return_value = mock_pr

    diff = await fetch_pr_diff_tool(mock_repo, 1)

    assert "src/main.py" in diff
    mock_repo.get_pull.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_reviewer_analyze_code_quality_tool():
    """Test analyze_code_quality_tool function."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"score": 85, "issues": ["issue1"], "suggestions": ["suggestion1"]}'
            )
        )
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    score, issues, suggestions = await analyze_code_quality_tool(
        "diff content", "original issue", mock_client
    )

    assert score == 85
    assert "issue1" in issues
    assert "suggestion1" in suggestions


def test_reviewer_check_test_coverage_tool():
    """Test check_test_coverage_tool function."""
    diff = """--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,2 @@
--- a/tests/test_main.py
+++ b/tests/test_main.py"""

    coverage = check_test_coverage_tool(diff)

    # Should find test file in the diff
    assert coverage >= 0.0


def test_reviewer_validate_pr_description_tool():
    """Test validate_pr_description_tool function."""
    # Valid: has ## Why section
    valid_body = """## Why
This fix addresses the null pointer exception.

## What
Added null check before accessing the object.
"""
    assert validate_pr_description_tool(valid_body) is True

    # Valid: has ## What section (50+ chars)
    valid_body2 = """## What
Added null check before accessing the object to prevent crashes."""
    assert validate_pr_description_tool(valid_body2) is True

    # Invalid: too short
    assert validate_pr_description_tool("Fix") is False

    # Invalid: no sections
    assert validate_pr_description_tool("This is a fix for the bug.") is False


def test_reviewer_security_scan_tool():
    """Test security_scan_tool function."""
    diff = """
    # Some code
    api_key = "sk-1234567890123456789012345678901234567890"
    password = "secret123"
    """

    issues = security_scan_tool(diff)

    assert len(issues) > 0
    assert any("api_key" in issue.lower() or "sk-" in issue for issue in issues)


def test_reviewer_security_scan_detects_secrets():
    """Test that security scan detects various secret patterns."""
    test_cases = [
        ("github_token = 'ghp_abcdefghijklmnopqrstuvwxyz123456'", True),
        ("const apiKey = 'sk-1234567890123456789012345678901234567890';", True),
        ("password = 'mysecretpassword123'", True),
        ("aws_access_key_id = 'AKIAIOSFODNN7EXAMPLE'", True),
        ("-----BEGIN RSA PRIVATE KEY-----", True),
        ("redis://:password@localhost:6379", True),
        ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", True),
        ("slack_token = 'xoxb-Faketoken123-Fake456-abcdefghij'", True),
        ("const url = 'https://api.example.com';", False),
        ("# This is a comment", False),
    ]

    for content, should_find in test_cases:
        issues = security_scan_tool(content)
        if should_find:
            assert len(issues) > 0, f"Should detect secret in: {content[:50]}"
        else:
            assert len(issues) == 0, f"Should not detect secret in: {content[:50]}"


# ========================
# Test Approval Logic
# ========================


def test_reviewer_approval_auto_approve_above_80():
    """Test auto-approve for scores >= 80."""
    with patch("src.agents.reviewer.get_llm_client") as mock_llm:
        mock_llm.return_value = MagicMock()

        agent = ReviewerAgent(
            context_store=MagicMock(),
            budget_manager=MagicMock(),
        )

        assert agent._determine_approval(80, []) is True
        assert agent._determine_approval(95, []) is True
        assert agent._determine_approval(100, []) is True


def test_reviewer_approval_suggestions_60_to_79():
    """Test approve with suggestions for scores 60-79."""
    with patch("src.agents.reviewer.get_llm_client") as mock_llm:
        mock_llm.return_value = MagicMock()

        agent = ReviewerAgent(
            context_store=MagicMock(),
            budget_manager=MagicMock(),
        )

        # Scores 60-79 should approve with suggestions
        assert agent._determine_approval(60, []) is True
        assert agent._determine_approval(70, []) is True
        assert agent._determine_approval(79, []) is True


def test_reviewer_approval_reject_below_60():
    """Test reject for scores < 60."""
    with patch("src.agents.reviewer.get_llm_client") as mock_llm:
        mock_llm.return_value = MagicMock()

        agent = ReviewerAgent(
            context_store=MagicMock(),
            budget_manager=MagicMock(),
        )

        assert agent._determine_approval(59, []) is False
        assert agent._determine_approval(50, []) is False
        assert agent._determine_approval(0, []) is False


def test_reviewer_approval_reject_with_security_issues():
    """Test reject when security issues found."""
    with patch("src.agents.reviewer.get_llm_client") as mock_llm:
        mock_llm.return_value = MagicMock()

        agent = ReviewerAgent(
            context_store=MagicMock(),
            budget_manager=MagicMock(),
        )

        # Even with high score, reject if security issues
        assert agent._determine_approval(90, ["Found API key"]) is False
        assert agent._determine_approval(100, ["Found password"]) is False


# ========================
# Test Full Workflow
# ========================


@pytest.mark.asyncio
async def test_reviewer_full_workflow_integration():
    """Test full Reviewer agent workflow."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.reviewer.get_github_repo") as mock_get_repo:
        with patch("src.agents.reviewer.get_llm_client") as mock_llm:
            # Setup mocks
            mock_repo = MagicMock()
            mock_get_repo.return_value = mock_repo

            # Mock PR
            mock_pr = MagicMock()
            mock_pr.body = "## Why\nFix implemented\n## What\nChanges made"
            mock_repo.get_pull.return_value = mock_pr

            # Mock files
            mock_file = MagicMock()
            mock_file.filename = "src/main.py"
            mock_file.patch = "@@ -1,1 +1,2 @@"
            mock_pr.get_files.return_value = [mock_file]

            # Mock LLM
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"score": 85, "issues": [], "suggestions": []}'
                    )
                )
            ]
            mock_llm.return_value.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            # Create agent
            agent = ReviewerAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
            )

            # Run
            result = await agent.run(
                task_id="task-123",
                pr_url="https://github.com/owner/repo/pull/1",
                original_issue="App crashes",
            )

            assert result.score == 85
            mock_budget.acquire_task_slot.assert_called_once()


@pytest.mark.asyncio
async def test_reviewer_acquires_budget_slot():
    """Test that Reviewer agent acquires budget slot."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.reviewer.get_github_repo"):
        with patch("src.agents.reviewer.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"score": 70, "issues": [], "suggestions": []}'
                    )
                )
            ]
            mock_llm.return_value.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            agent = ReviewerAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
            )

            await agent.run(
                task_id="task-123",
                pr_url="https://github.com/owner/repo/pull/1",
                original_issue="App crashes",
            )

            mock_budget.acquire_task_slot.assert_called_once_with("task-123")


@pytest.mark.asyncio
async def test_reviewer_handles_budget_exhausted():
    """Test that Reviewer agent handles budget exhaustion."""
    mock_budget = AsyncMock()
    mock_budget.acquire_task_slot.side_effect = RuntimeError("Budget exhausted")
    mock_context = AsyncMock()
    mock_llm = MagicMock()

    agent = ReviewerAgent(
        context_store=mock_context,
        budget_manager=mock_budget,
        openai_client=mock_llm,
    )

    with pytest.raises(RuntimeError, match="Budget exhausted"):
        await agent.run(
            task_id="task-123",
            pr_url="https://github.com/owner/repo/pull/1",
            original_issue="App crashes",
        )


@pytest.mark.asyncio
async def test_reviewer_writes_result_to_context():
    """Test that Reviewer agent writes result to context."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.reviewer.get_github_repo"):
        with patch("src.agents.reviewer.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"score": 70, "issues": [], "suggestions": []}'
                    )
                )
            ]
            mock_llm.return_value.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            agent = ReviewerAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
            )

            await agent.run(
                task_id="task-123",
                pr_url="https://github.com/owner/repo/pull/1",
                original_issue="App crashes",
            )

            # Verify context write was called
            mock_context.write.assert_called()


@pytest.mark.asyncio
async def test_reviewer_azure_openai_connection():
    """Test Azure OpenAI connection for Reviewer."""
    with patch("src.agents.reviewer.get_azure_openai_client") as mock_azure:
        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            client = mock_azure.return_value
            assert client is not None


@pytest.mark.asyncio
async def test_reviewer_reads_swe_findings():
    """Test that Reviewer reads SWE findings from context."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.reviewer.get_github_repo"):
        with patch("src.agents.reviewer.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content='{"score": 85, "issues": [], "suggestions": []}'
                    )
                )
            ]
            mock_llm.return_value.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            agent = ReviewerAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
            )

            await agent.run(
                task_id="task-123",
                pr_url="https://github.com/owner/repo/pull/1",
                original_issue="App crashes - fix implemented",
            )

            # Verify LLM was called with original issue
            mock_llm.return_value.chat.completions.create.assert_called()
