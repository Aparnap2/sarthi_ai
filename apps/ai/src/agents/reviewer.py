"""Reviewer Agent for automated code review and secret scanning."""

import os
import re
from typing import Any, Literal, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.budget.manager import TokenBudgetManager
from src.config import get_config
from src.context.store import ContextStore


# ========================
# Security Patterns (25+)
# ========================

SECRET_PATTERNS = [
    # Generic API keys
    r"api[_-]?key\s*=\s*['\"][^'\"]{20,}",
    r"password\s*=\s*['\"][^'\"]{8,}",
    r"secret\s*=\s*['\"][^'\"]{10,}",
    r"token\s*=\s*['\"][^'\"]{20,}",
    # Cloud provider keys
    r"AZURE_OPENAI_API_KEY\s*=\s*['\"][^'\"]+",
    r"AWS_ACCESS_KEY_ID\s*=\s*['\"][A-Z0-9]{20}",
    r"AWS_SECRET_ACCESS_KEY\s*=\s*['\"][A-Za-z0-9/+=]{40}",
    r"GOOGLE_API_KEY\s*=\s*['\"][A-Za-z0-9_-]{39}",
    # Private keys
    r"-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----",
    r"-----BEGIN CERTIFICATE-----",
    # GitHub tokens
    r"ghp_[A-Za-z0-9]{36}",
    r"github_pat_[A-Za-z0-9_]{22,}",
    r"gho_[A-Za-z0-9]{36}",
    # OpenAI keys
    r"sk-[A-Za-z0-9]{48}",
    r"sk-proj-[A-Za-z0-9_-]{48,}",
    # Database passwords
    r"postgresql://[^:]+:[^@]+@",
    r"mysql://[^:]+:[^@]+@",
    r"mongodb(\+srv)?://[^:]+:[^@]+@",
    r"redis://[^:]*:[^@]+@",
    # JWT tokens
    r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    # Slack tokens
    r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9-]+",
    # Stripe keys
    r"sk_live_[A-Za-z0-9]{24,}",
    r"pk_live_[A-Za-z0-9]{24,}",
    # SendGrid
    r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}",
    # Twilio
    r"AC[a-z0-9]{32}",
    r"SK[a-z0-9]{32}",
    # Generic secrets
    r"bearer\s+[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
]


# ========================
# Data Models
# ========================


class ReviewerResult(BaseModel):
    """Result from the Reviewer Agent."""

    approved: bool = Field(description="Whether the PR is approved")
    score: float = Field(
        description="Review score from 0-100",
        ge=0.0,
        le=100.0,
    )
    issues: list[str] = Field(
        description="List of issues found"
    )
    suggestions: list[str] = Field(
        description="List of suggestions for improvement"
    )
    test_coverage: float = Field(
        description="Test coverage estimate from 0.0 to 1.0",
        ge=0.0,
        le=1.0,
    )
    security_issues: list[str] = Field(
        description="List of security issues found"
    )


# ========================
# LLM Client
# ========================


def get_azure_openai_client() -> Optional[AsyncOpenAI]:
    """Get configured Azure OpenAI client."""
    config = get_config()
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")

    if not azure_endpoint or not azure_key:
        return None

    return AsyncOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_key,
    )


def get_ollama_client() -> AsyncOpenAI:
    """Get configured Ollama client."""
    config = get_config()
    return AsyncOpenAI(
        base_url=config.ollama.base_url,
        api_key=config.ollama.api_key,
    )


def get_llm_client() -> AsyncOpenAI:
    """Get the best available LLM client."""
    azure = get_azure_openai_client()
    if azure:
        return azure
    return get_ollama_client()


# ========================
# Reviewer Tools
# ========================


def get_github_client():
    """Get configured GitHub client."""
    from github import Github
    token = os.getenv("GITHUB_TOKEN", "")
    return Github(token)


def get_github_repo():
    """Get the configured GitHub repository."""
    owner = os.getenv("GITHUB_OWNER")
    repo_name = os.getenv("GITHUB_REPO")
    if not owner or not repo_name:
        raise ValueError("GITHUB_OWNER and GITHUB_REPO must be set")

    g = get_github_client()
    return g.get_repo(f"{owner}/{repo_name}")


async def fetch_pr_diff_tool(
    repo: Any,
    pr_number: int,
) -> str:
    """Fetch the PR diff.

    Args:
        repo: PyGithub repository object
        pr_number: PR number

    Returns:
        Diff string
    """
    pr = repo.get_pull(pr_number)
    files = pr.get_files()

    diff_lines = []
    for file in files:
        diff_lines.append(f"--- a/{file.filename}")
        diff_lines.append(f"+++ b/{file.filename}")
        diff_lines.append(file.patch or "")

    return "\n".join(diff_lines)


async def analyze_code_quality_tool(
    diff: str,
    original_issue: str,
    llm_client: AsyncOpenAI,
) -> tuple[float, list[str], list[str]]:
    """Analyze code quality using LLM.

    Args:
        diff: PR diff
        original_issue: Original issue description
        llm_client: OpenAI client

    Returns:
        Tuple of (score, issues, suggestions)
    """
    prompt = f"""Analyze the following code changes for quality:

## Original Issue
{original_issue}

## Changes
{diff[:5000]}

Provide a review with:
1. Score (0-100): Overall code quality score
2. Issues: List of issues found
3. Suggestions: List of suggestions for improvement

Return your response as JSON:
{{
    "score": 0-100,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"]
}}
"""

    try:
        response = await llm_client.chat.completions.create(
            model=get_config().ollama.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        content = response.choices[0].message.content
        if content:
            import json
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            result = json.loads(content)
            return result.get("score", 70), result.get("issues", []), result.get("suggestions", [])
    except Exception:
        pass

    return 70, [], []


def check_test_coverage_tool(diff: str) -> float:
    """Check test coverage based on diff.

    Args:
        diff: PR diff

    Returns:
        Test coverage estimate (0.0 to 1.0)
    """
    # Count test files vs total files
    lines = diff.split("\n")
    test_files = 0
    total_files = 0

    for line in lines:
        if line.startswith("+++ b/"):
            total_files += 1
            filename = line[6:]
            if "test" in filename.lower() or filename.endswith("_test.py"):
                test_files += 1

    if total_files == 0:
        return 0.0

    return min(test_files / max(total_files, 1), 1.0)


def validate_pr_description_tool(pr_body: str) -> bool:
    """Validate PR description has required sections.

    Args:
        pr_body: PR body/description

    Returns:
        True if valid (50+ chars and ## Why/## What sections)
    """
    if len(pr_body) < 50:
        return False

    has_why = "## Why" in pr_body or "## Why" in pr_body.lower()
    has_what = "## What" in pr_body or "## What" in pr_body.lower()

    return has_why or has_what


def security_scan_tool(diff: str) -> list[str]:
    """Scan diff for secrets.

    Args:
        diff: PR diff

    Returns:
        List of security issues found
    """
    issues = []

    for pattern in SECRET_PATTERNS:
        matches = re.finditer(pattern, diff, re.IGNORECASE)
        for match in matches:
            # Extract a snippet around the match
            start = max(0, match.start() - 20)
            end = min(len(diff), match.end() + 20)
            snippet = diff[start:end].replace("\n", " ")

            issues.append(f"Potential secret found: ...{snippet}...")

    return issues


# ========================
# Reviewer Agent
# ========================


class ReviewerAgent:
    """Agent that reviews PRs and performs secret scanning."""

    def __init__(
        self,
        context_store: ContextStore,
        budget_manager: TokenBudgetManager,
        openai_client: Optional[AsyncOpenAI] = None,
    ) -> None:
        """Initialize the Reviewer Agent.

        Args:
            context_store: Context store for state persistence
            budget_manager: Budget manager for task concurrency
            openai_client: OpenAI client (auto-configured if not provided)
        """
        self.context_store = context_store
        self.budget_manager = budget_manager
        self.openai_client = openai_client or get_llm_client()

    async def run(
        self,
        task_id: str,
        pr_url: str,
        original_issue: str,
    ) -> ReviewerResult:
        """Run the Reviewer agent workflow.

        Args:
            task_id: Unique task identifier
            pr_url: URL of the PR to review
            original_issue: Original issue description

        Returns:
            ReviewerResult with review details
        """
        # Step 1: Acquire budget slot
        await self.budget_manager.acquire_task_slot(task_id)

        try:
            # Step 2: Fetch PR diff
            repo = get_github_repo()
            pr_number = int(pr_url.split("/pull/")[-1].split("/")[0])
            diff = await fetch_pr_diff_tool(repo, pr_number)

            # Step 3: Run review tools
            score, issues, suggestions = await analyze_code_quality_tool(
                diff, original_issue, self.openai_client
            )
            test_coverage = check_test_coverage_tool(diff)
            pr = repo.get_pull(pr_number)
            pr_valid = validate_pr_description_tool(pr.body or "")
            security_issues = security_scan_tool(diff)

            # Add validation issue if PR description is invalid
            if not pr_valid:
                issues.append("PR description missing required sections (## Why or ## What)")

            # Step 4: Determine approval based on score
            approved = self._determine_approval(score, security_issues)

            # Step 5: Write result to context
            result = ReviewerResult(
                approved=approved,
                score=score,
                issues=issues,
                suggestions=suggestions,
                test_coverage=test_coverage,
                security_issues=security_issues,
            )

            await self.context_store.write(
                task_id, "reviewer", "result", result.model_dump()
            )

            return result

        finally:
            # Step 6: Release budget slot
            await self.budget_manager.release_task_slot(task_id)

    def _determine_approval(
        self,
        score: float,
        security_issues: list[str],
    ) -> bool:
        """Determine approval based on score and security issues.

        Args:
            score: Code quality score
            security_issues: List of security issues

        Returns:
            True if approved
        """
        # Reject if there are any security issues
        if security_issues:
            return False

        # Approval logic based on score
        if score >= 80:
            return True  # auto-approve
        elif score >= 60:
            return True  # approve with suggestions
        else:
            return False  # reject
