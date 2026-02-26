"""Tests for the SWE Agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.agents.swe import (
    SWEInput,
    SWEResult,
    SWEAgent,
    create_branch_tool,
    modify_file_tool,
    create_pr_tool,
    trigger_ci_tool,
    get_github_repo,
    get_llm_client,
)


# ========================
# Test Models
# ========================


def test_swe_result_model():
    """Test SWEResult model validation."""
    result = SWEResult(
        pr_url="https://github.com/owner/repo/pull/1",
        pr_number=1,
        branch_name="fix/task-123",
        files_changed=["src/main.py"],
        ci_status="pending",
        confidence=0.85,
    )

    assert result.pr_url == "https://github.com/owner/repo/pull/1"
    assert result.pr_number == 1
    assert result.branch_name == "fix/task-123"
    assert result.files_changed == ["src/main.py"]
    assert result.ci_status == "pending"
    assert result.confidence == 0.85


def test_swe_input_model():
    """Test SWEInput model validation."""
    input_data = SWEInput(
        task_id="task-123",
        feedback_text="App crashes on login",
        researcher_findings={"root_cause": "null pointer"},
        sre_findings={"priority": "HIGH"},
    )

    assert input_data.task_id == "task-123"
    assert input_data.feedback_text == "App crashes on login"
    assert input_data.researcher_findings == {"root_cause": "null pointer"}
    assert input_data.sre_findings == {"priority": "HIGH"}


# ========================
# Test Agent Initialization
# ========================


def test_swe_agent_initialization():
    """Test SWEAgent initialization with all dependencies."""
    with patch("src.agents.swe.get_llm_client") as mock_llm:
        with patch("src.agents.swe.ContextStore") as mock_context:
            with patch("src.agents.swe.TokenBudgetManager") as mock_budget:
                mock_llm.return_value = MagicMock()
                mock_context.return_value = MagicMock()
                mock_budget.return_value = MagicMock()

                agent = SWEAgent(
                    context_store=mock_context.return_value,
                    budget_manager=mock_budget.return_value,
                    openai_client=mock_llm.return_value,
                    github_token="test-token",
                )

                assert agent.context_store is not None
                assert agent.budget_manager is not None
                assert agent.openai_client is not None
                assert agent.github_token == "test-token"


def test_swe_agent_without_github_token():
    """Test SWEAgent initialization without GitHub token."""
    with patch("src.agents.swe.get_llm_client") as mock_llm:
        with patch("src.agents.swe.ContextStore") as mock_context:
            with patch("src.agents.swe.TokenBudgetManager") as mock_budget:
                mock_llm.return_value = MagicMock()
                mock_context.return_value = MagicMock()
                mock_budget.return_value = MagicMock()

                agent = SWEAgent(
                    context_store=mock_context.return_value,
                    budget_manager=mock_budget.return_value,
                )

                assert agent.github_token == ""


# ========================
# Test GitHub Tools
# ========================


@pytest.mark.asyncio
async def test_swe_create_branch_tool():
    """Test create_branch_tool function."""
    mock_repo = MagicMock()
    mock_ref = MagicMock()
    mock_ref.object.sha = "abc123"
    mock_repo.get_git_ref.return_value = mock_ref

    branch_name = await create_branch_tool(mock_repo, "task-123")

    assert branch_name == "fix/task-123"
    mock_repo.get_git_ref.assert_called_once_with("heads/main")
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/fix/task-123", sha="abc123"
    )


@pytest.mark.asyncio
async def test_swe_modify_file_tool():
    """Test modify_file_tool function."""
    mock_repo = MagicMock()
    mock_file = MagicMock()
    mock_file.sha = "oldsha"
    mock_repo.get_contents.return_value = mock_file

    await modify_file_tool(
        repo=mock_repo,
        branch="fix/task-123",
        path="src/main.py",
        content="new content",
        message="Fix: task-123",
    )

    mock_repo.get_contents.assert_called_once_with("src/main.py", ref="fix/task-123")
    mock_repo.update_file.assert_called_once()


@pytest.mark.asyncio
async def test_swe_create_pr_tool():
    """Test create_pr_tool function."""
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/owner/repo/pull/1"
    mock_pr.number = 1
    mock_repo.create_pull.return_value = mock_pr

    pr_url, pr_number = await create_pr_tool(
        repo=mock_repo,
        branch="fix/task-123",
        title="Fix: Login crash",
        body="## Why\nRoot cause\n## What\nFix implemented",
    )

    assert pr_url == "https://github.com/owner/repo/pull/1"
    assert pr_number == 1
    mock_repo.create_pull.assert_called_once()


@pytest.mark.asyncio
async def test_swe_trigger_ci_tool():
    """Test trigger_ci_tool function."""
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_repo.get_pull.return_value = mock_pr

    await trigger_ci_tool(mock_repo, 1)

    mock_repo.get_pull.assert_called_once_with(1)


# ========================
# Test Full Workflow
# ========================


@pytest.mark.asyncio
async def test_swe_full_workflow_integration():
    """Test full SWE agent workflow."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.swe.get_github_repo") as mock_get_repo:
        with patch("src.agents.swe.get_llm_client") as mock_llm:
            # Setup mocks
            mock_repo = MagicMock()
            mock_get_repo.return_value = mock_repo

            # Mock PR creation
            mock_pr = MagicMock()
            mock_pr.html_url = "https://github.com/owner/repo/pull/1"
            mock_pr.number = 1
            mock_repo.create_pull.return_value = mock_pr

            # Mock file operations
            mock_file = MagicMock()
            mock_file.sha = "oldsha"
            mock_repo.get_contents.return_value = mock_file

            # Mock branch creation
            mock_ref = MagicMock()
            mock_ref.object.sha = "abc123"
            mock_repo.get_git_ref.return_value = mock_ref

            # Mock LLM
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content='{"title": "Test", "body": "Body", "files": [], "confidence": 0.8}'))]
            mock_llm.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

            # Create agent
            agent = SWEAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
                openai_client=mock_llm.return_value,
            )

            # Run
            result = await agent.run(
                task_id="task-123",
                feedback_text="App crashes",
                researcher_findings={"root_cause": "null"},
                sre_findings={"priority": "HIGH"},
            )

            assert result.pr_number == 1
            assert result.branch_name == "fix/task-123"


# ========================
# Test Budget Integration
# ========================


@pytest.mark.asyncio
async def test_swe_acquires_budget_slot():
    """Test that SWE agent acquires budget slot."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.swe.get_github_repo") as mock_get_repo:
        with patch("src.agents.swe.get_llm_client") as mock_llm:
            # Setup mock repo
            mock_repo = MagicMock()
            mock_get_repo.return_value = mock_repo

            # Mock PR creation
            mock_pr = MagicMock()
            mock_pr.html_url = "https://github.com/owner/repo/pull/1"
            mock_pr.number = 1
            mock_repo.create_pull.return_value = mock_pr

            # Mock file operations
            mock_file = MagicMock()
            mock_file.sha = "oldsha"
            mock_repo.get_contents.return_value = mock_file

            # Mock branch creation
            mock_ref = MagicMock()
            mock_ref.object.sha = "abc123"
            mock_repo.get_git_ref.return_value = mock_ref

            # Mock LLM
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content='{"title": "Test", "body": "Body", "files": [], "confidence": 0.8}'))]
            mock_llm.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

            agent = SWEAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
                openai_client=mock_llm.return_value,
            )

            await agent.run(
                task_id="task-123",
                feedback_text="App crashes",
                researcher_findings={},
                sre_findings={},
            )

            mock_budget.acquire_task_slot.assert_called_once_with("task-123")


@pytest.mark.asyncio
async def test_swe_handles_budget_exhausted():
    """Test that SWE agent handles budget exhaustion."""
    mock_budget = AsyncMock()
    mock_budget.acquire_task_slot.side_effect = RuntimeError("Budget exhausted")
    mock_context = AsyncMock()
    mock_llm = MagicMock()

    agent = SWEAgent(
        context_store=mock_context,
        budget_manager=mock_budget,
        openai_client=mock_llm,
    )

    with pytest.raises(RuntimeError, match="Budget exhausted"):
        await agent.run(
            task_id="task-123",
            feedback_text="App crashes",
            researcher_findings={},
            sre_findings={},
        )


@pytest.mark.asyncio
async def test_swe_writes_result_to_context():
    """Test that SWE agent writes result to context."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.swe.get_github_repo") as mock_get_repo:
        with patch("src.agents.swe.get_llm_client") as mock_llm:
            # Setup mock repo
            mock_repo = MagicMock()
            mock_get_repo.return_value = mock_repo

            # Mock PR creation
            mock_pr = MagicMock()
            mock_pr.html_url = "https://github.com/owner/repo/pull/1"
            mock_pr.number = 1
            mock_repo.create_pull.return_value = mock_pr

            # Mock file operations
            mock_file = MagicMock()
            mock_file.sha = "oldsha"
            mock_repo.get_contents.return_value = mock_file

            # Mock branch creation
            mock_ref = MagicMock()
            mock_ref.object.sha = "abc123"
            mock_repo.get_git_ref.return_value = mock_ref

            # Mock LLM
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content='{"title": "Test", "body": "Body", "files": [], "confidence": 0.8}'))]
            mock_llm.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

            agent = SWEAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
                openai_client=mock_llm.return_value,
            )

            await agent.run(
                task_id="task-123",
                feedback_text="App crashes",
                researcher_findings={"root_cause": "bug"},
                sre_findings={"priority": "HIGH"},
            )

            # Verify context write was called
            mock_context.write.assert_called()


@pytest.mark.asyncio
async def test_swe_reads_researcher_findings():
    """Test that SWE agent reads researcher findings from context."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.swe.get_github_repo") as mock_get_repo:
        with patch("src.agents.swe.get_llm_client") as mock_llm:
            # Setup mock repo
            mock_repo = MagicMock()
            mock_get_repo.return_value = mock_repo

            # Mock PR creation
            mock_pr = MagicMock()
            mock_pr.html_url = "https://github.com/owner/repo/pull/1"
            mock_pr.number = 1
            mock_repo.create_pull.return_value = mock_pr

            # Mock file operations
            mock_file = MagicMock()
            mock_file.sha = "oldsha"
            mock_repo.get_contents.return_value = mock_file

            # Mock branch creation
            mock_ref = MagicMock()
            mock_ref.object.sha = "abc123"
            mock_repo.get_git_ref.return_value = mock_ref

            # Mock LLM
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content='{"title": "Test", "body": "Body", "files": [], "confidence": 0.8}'))]
            mock_llm.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

            agent = SWEAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
                openai_client=mock_llm.return_value,
            )

            await agent.run(
                task_id="task-123",
                feedback_text="App crashes",
                researcher_findings={"root_cause": "null pointer"},
                sre_findings={"priority": "HIGH"},
            )

            # Verify researcher findings were written
            call_args = mock_context.write.call_args_list[0]
            assert call_args[0][1] == "swe"  # agent name
            assert "researcher_findings" in str(call_args)


@pytest.mark.asyncio
async def test_swe_reads_sre_findings():
    """Test that SWE agent reads SRE findings from context."""
    mock_budget = AsyncMock()
    mock_context = AsyncMock()

    with patch("src.agents.swe.get_github_repo") as mock_get_repo:
        with patch("src.agents.swe.get_llm_client") as mock_llm:
            # Setup mock repo
            mock_repo = MagicMock()
            mock_get_repo.return_value = mock_repo

            # Mock PR creation
            mock_pr = MagicMock()
            mock_pr.html_url = "https://github.com/owner/repo/pull/1"
            mock_pr.number = 1
            mock_repo.create_pull.return_value = mock_pr

            # Mock file operations
            mock_file = MagicMock()
            mock_file.sha = "oldsha"
            mock_repo.get_contents.return_value = mock_file

            # Mock branch creation
            mock_ref = MagicMock()
            mock_ref.object.sha = "abc123"
            mock_repo.get_git_ref.return_value = mock_ref

            # Mock LLM
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content='{"title": "Test", "body": "Body", "files": [], "confidence": 0.8}'))]
            mock_llm.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

            agent = SWEAgent(
                context_store=mock_context,
                budget_manager=mock_budget,
                openai_client=mock_llm.return_value,
            )

            await agent.run(
                task_id="task-123",
                feedback_text="App crashes",
                researcher_findings={},
                sre_findings={"priority": "CRITICAL", "error_rate": 0.5},
            )

            # Verify SRE findings were passed to synthesis
            mock_llm.return_value.chat.completions.create.assert_called()


# ========================
# Test LLM Connection
# ========================


def test_swe_azure_openai_connection():
    """Test Azure OpenAI client connection."""
    with patch("src.agents.swe.get_azure_openai_client") as mock_azure:
        with patch.dict("os.environ", {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com", "AZURE_OPENAI_API_KEY": "test-key"}):
            client = get_llm_client()
            assert client is not None


def test_swe_agent_without_azure_credentials():
    """Test SWE agent works without Azure credentials (fallback to Ollama)."""
    with patch("src.agents.swe.get_azure_openai_client") as mock_azure:
        mock_azure.return_value = None

        client = get_llm_client()
        assert client is not None
