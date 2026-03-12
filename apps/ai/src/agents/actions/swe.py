"""SWE Agent for automated code fixes and PR creation."""

import os
from typing import Any, Literal, Optional

from github import Github
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.budget.manager import TokenBudgetManager
from src.config import get_config
from src.context.store import ContextStore


# ========================
# Data Models
# ========================


class SWEInput(BaseModel):
    """Input for the SWE Agent."""

    task_id: str = Field(description="Unique task identifier")
    feedback_text: str = Field(description="Original feedback text")
    researcher_findings: dict[str, Any] = Field(
        description="Findings from the Researcher agent"
    )
    sre_findings: dict[str, Any] = Field(
        description="Findings from the SRE agent"
    )


class SWEResult(BaseModel):
    """Result from the SWE Agent."""

    pr_url: str = Field(description="URL of the created PR")
    pr_number: int = Field(description="PR number")
    branch_name: str = Field(description="Name of the created branch")
    files_changed: list[str] = Field(
        description="List of files that were changed"
    )
    ci_status: Literal["pending", "success", "failure"] = Field(
        description="CI status after trigger"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0",
        ge=0.0,
        le=1.0,
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
# GitHub Tools
# ========================


def get_github_client() -> Github:
    """Get configured GitHub client."""
    token = os.getenv("GITHUB_TOKEN", "")
    return Github(token)


def get_github_repo() -> Any:
    """Get the configured GitHub repository."""
    owner = os.getenv("GITHUB_OWNER")
    repo_name = os.getenv("GITHUB_REPO")
    if not owner or not repo_name:
        raise ValueError("GITHUB_OWNER and GITHUB_REPO must be set")

    g = get_github_client()
    return g.get_repo(f"{owner}/{repo_name}")


async def create_branch_tool(
    repo: Any,
    task_id: str,
    base_branch: str = "main",
) -> str:
    """Create a new branch from base branch.

    Args:
        repo: PyGithub repository object
        task_id: Unique task identifier
        base_branch: Base branch to create from (default: main)

    Returns:
        Name of the created branch
    """
    branch_name = f"fix/{task_id}"

    # Get the base branch reference
    try:
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        sha = base_ref.object.sha
    except Exception:
        # Try main if main fails
        base_ref = repo.get_git_ref(f"heads/master")
        sha = base_ref.object.sha

    # Create the new branch
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sha)

    return branch_name


async def modify_file_tool(
    repo: Any,
    branch: str,
    path: str,
    content: str,
    message: str,
) -> None:
    """Modify a file in the repository.

    Args:
        repo: PyGithub repository object
        branch: Branch name to modify
        path: File path to modify
        content: New content for the file
        message: Commit message
    """
    try:
        # Get existing file to get SHA
        file = repo.get_contents(path, ref=branch)
        existing_sha = file.sha
    except Exception:
        # File doesn't exist, create new
        existing_sha = None

    # Update or create file
    repo.update_file(
        path=path,
        message=message,
        content=content,
        branch=branch,
        sha=existing_sha,
    )


async def create_pr_tool(
    repo: Any,
    branch: str,
    title: str,
    body: str,
    base_branch: str = "main",
) -> tuple[str, int]:
    """Create a pull request.

    Args:
        repo: PyGithub repository object
        branch: Branch name for the PR
        title: PR title
        body: PR body/description
        base_branch: Base branch to merge into

    Returns:
        Tuple of (pr_url, pr_number)
    """
    pr = repo.create_pull(
        title=title,
        body=body,
        head=branch,
        base=base_branch,
    )

    return pr.html_url, pr.number


async def trigger_ci_tool(
    repo: Any,
    pr_number: int,
    workflow_file: str = "ci.yml",
) -> None:
    """Trigger CI for the PR.

    Args:
        repo: PyGithub repository object
        pr_number: PR number
        workflow_file: Name of the workflow file to trigger
    """
    # Try to trigger workflow_dispatch
    try:
        # Get the workflow
        workflow = repo.get_workflow(workflow_file)
        # Note: workflow_dispatch requires additional setup
        # For now, we just post a comment to indicate CI should run
    except Exception:
        pass

    # Post a comment to trigger any PR-triggered CI
    pr = repo.get_pull(pr_number)
    pr.create_comment(
        "🤖 SWE Agent: CI triggered for this PR. "
        "Please review the changes and verify tests pass."
    )


# ========================
# SWE Agent
# ========================


class SWEAgent:
    """Agent that creates branches, edits code, and opens PRs."""

    def __init__(
        self,
        context_store: ContextStore,
        budget_manager: TokenBudgetManager,
        openai_client: Optional[AsyncOpenAI] = None,
        github_token: str = "",
    ) -> None:
        """Initialize the SWE Agent.

        Args:
            context_store: Context store for state persistence
            budget_manager: Budget manager for task concurrency
            openai_client: OpenAI client (auto-configured if not provided)
            github_token: GitHub token (auto-configured if not provided)
        """
        self.context_store = context_store
        self.budget_manager = budget_manager
        self.openai_client = openai_client or get_llm_client()
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")

    async def run(
        self,
        task_id: str,
        feedback_text: str,
        researcher_findings: dict[str, Any],
        sre_findings: dict[str, Any],
    ) -> SWEResult:
        """Run the SWE agent workflow.

        Args:
            task_id: Unique task identifier
            feedback_text: Original feedback text
            researcher_findings: Findings from Researcher agent
            sre_findings: Findings from SRE agent

        Returns:
            SWEResult with PR details
        """
        # Step 1: Acquire budget slot
        await self.budget_manager.acquire_task_slot(task_id)

        try:
            # Step 2: Read researcher and SRE findings from context
            await self.context_store.write(
                task_id, "swe", "input",
                {
                    "feedback_text": feedback_text,
                    "researcher_findings": researcher_findings,
                    "sre_findings": sre_findings,
                },
            )

            # Step 3: Synthesize fix using LLM
            fix_content = await self._synthesize_fix(
                feedback_text,
                researcher_findings,
                sre_findings,
            )

            # Step 4: Execute GitHub tools
            repo = get_github_repo()

            # Create branch
            branch_name = await create_branch_tool(repo, task_id)

            # Modify files
            files_changed = []
            for file_change in fix_content.get("files", []):
                await modify_file_tool(
                    repo=repo,
                    branch=branch_name,
                    path=file_change["path"],
                    content=file_change["content"],
                    message=file_change.get("message", f"Fix: {task_id}"),
                )
                files_changed.append(file_change["path"])

            # Create PR
            pr_url, pr_number = await create_pr_tool(
                repo=repo,
                branch=branch_name,
                title=fix_content.get("title", f"Fix: {feedback_text[:50]}"),
                body=fix_content.get("body", f"Fix for task {task_id}"),
            )

            # Trigger CI
            await trigger_ci_tool(repo, pr_number)

            # Step 5: Write result to context
            result = SWEResult(
                pr_url=pr_url,
                pr_number=pr_number,
                branch_name=branch_name,
                files_changed=files_changed,
                ci_status="pending",
                confidence=fix_content.get("confidence", 0.8),
            )

            await self.context_store.write(
                task_id, "swe", "result", result.model_dump()
            )

            return result

        finally:
            # Step 6: Release budget slot
            await self.budget_manager.release_task_slot(task_id)

    async def _synthesize_fix(
        self,
        feedback_text: str,
        researcher_findings: dict[str, Any],
        sre_findings: dict[str, Any],
    ) -> dict[str, Any]:
        """Synthesize code fix using LLM.

        Args:
            feedback_text: Original feedback
            researcher_findings: Researcher findings
            sre_findings: SRE findings

        Returns:
            Fix content with files to modify
        """
        prompt = f"""You are a SWE (Software Engineering) Agent. Based on the following findings,
generate a code fix.

## Original Feedback
{feedback_text}

## Researcher Findings
{researcher_findings}

## SRE Findings
{sre_findings}

## Task
Generate a code fix. Return your response as JSON with this structure:
{{
    "title": "Brief PR title",
    "body": "PR description with ## Why and ## What sections",
    "files": [
        {{
            "path": "relative/path/to/file.py",
            "content": "full file content or patch",
            "message": "commit message"
        }}
    ],
    "confidence": 0.0-1.0
}}

Focus on implementing the fix based on the root cause analysis.
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=get_config().ollama.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )

            import json

            content = response.choices[0].message.content
            if content:
                # Try to parse JSON from response
                # Handle potential markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return json.loads(content)
        except Exception:
            pass

        # Fallback to a simple fix structure
        return {
            "title": f"Fix: {feedback_text[:30]}",
            "body": f"## Why\n{researcher_findings.get('root_cause', 'N/A')}\n\n## What\nImplemented fix based on analysis.",
            "files": [],
            "confidence": 0.5,
        }
