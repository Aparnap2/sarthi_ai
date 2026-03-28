"""
QAAgent Activity for Temporal.

Wraps the QA LangGraph agent as a Temporal activity.
LangGraph invoke is sync — wrapped with asyncio.get_event_loop().run_in_executor().
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from temporalio import activity

from src.agents.qa.graph import qa_graph
from src.agents.qa.state import QAState

log = logging.getLogger(__name__)


def _safe_heartbeat(message: str) -> None:
    """Safely call activity.heartbeat, ignoring errors outside activity context."""
    try:
        activity.heartbeat(message)
    except RuntimeError:
        # Not in activity context (e.g., during testing)
        log.debug("Heartbeat (no context): %s", message)


@activity.defn(name="run_qa_agent")
async def run_qa_agent(tenant_id: str, question: str) -> dict[str, Any]:
    """
    Execute the QAAgent LangGraph for answering questions.

    This activity:
    1. Initializes QAState with tenant_id and question
    2. Invokes the qa_graph LangGraph
    3. Returns the output with answer and Slack message

    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        question: The question to answer

    Returns:
        dict with keys:
            - ok: bool (True on success, False on error)
            - tenant_id: str
            - question: str (original question)
            - answer: str (generated answer)
            - matched_category: str (question category)
            - output_message: str (formatted Slack message)
            - slack_blocks: list[dict] (Slack block kit format)
            - langfuse_trace_id: str
            - error: str (only if ok=False)

    Note:
        Never raises — catches errors and returns {"ok": False, "error": "..."}
    """
    if not tenant_id or not tenant_id.strip():
        return {"ok": False, "error": "tenant_id is required and cannot be empty"}

    if not question or not question.strip():
        return {"ok": False, "error": "question is required and cannot be empty"}

    try:
        _safe_heartbeat(f"QAAgent starting for tenant {tenant_id}: {question[:50]}...")

        # Initialize state
        initial_state: QAState = {
            "tenant_id": tenant_id,
            "question": question,
            "matched_category": "",
            "data_context": "",
            "memory_context": "",
            "answer": "",
            "slack_message": "",
            "slack_blocks": [],
            "error": "",
            "retry_count": 0,
            "langfuse_trace_id": "",
        }

        _safe_heartbeat(f"Invoking qa_graph for tenant {tenant_id}")

        # LangGraph invoke is sync — run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: qa_graph.invoke(initial_state),
        )

        _safe_heartbeat(f"QAAgent completed for tenant {tenant_id}")

        # Return only the required output fields
        return {
            "ok": True,
            "tenant_id": result.get("tenant_id", tenant_id),
            "question": result.get("question", question),
            "answer": result.get("answer", ""),
            "matched_category": result.get("matched_category", ""),
            "output_message": result.get("slack_message", ""),
            "slack_blocks": result.get("slack_blocks", []),
            "langfuse_trace_id": result.get("langfuse_trace_id", ""),
        }

    except Exception as e:
        _safe_heartbeat(f"QAAgent failed for tenant {tenant_id}: {e}")
        return {"ok": False, "error": str(e), "tenant_id": tenant_id}
