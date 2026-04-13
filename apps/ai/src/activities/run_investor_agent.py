"""
InvestorAgent Activity for Temporal.

Wraps the Investor LangGraph agent as a Temporal activity.
LangGraph invoke is sync — wrapped with asyncio.get_event_loop().run_in_executor().
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from temporalio import activity

from src.agents.investor.graph import investor_graph
from src.agents.investor.state import InvestorState

log = logging.getLogger(__name__)


def _safe_heartbeat(message: str) -> None:
    """Safely call activity.heartbeat, ignoring errors outside activity context."""
    try:
        activity.heartbeat(message)
    except RuntimeError:
        # Not in activity context (e.g., during testing)
        log.debug("Heartbeat (no context): %s", message)


@activity.defn(name="run_investor_agent")
async def run_investor_agent(tenant_id: str) -> dict[str, Any]:
    """
    Execute the InvestorAgent LangGraph for weekly investor updates.

    This activity:
    1. Initializes InvestorState with tenant_id
    2. Invokes the investor_graph LangGraph
    3. Returns the output with metrics, narrative, and Slack message

    Args:
        tenant_id: Tenant identifier for multi-tenant isolation

    Returns:
        dict with keys:
            - ok: bool (True on success, False on error)
            - tenant_id: str
            - metrics: dict (key business metrics)
            - narrative: str (investor-friendly summary)
            - output_message: str (formatted Slack message)
            - slack_blocks: list[dict] (Slack block kit format)
            - langfuse_trace_id: str
            - error: str (only if ok=False)

    Note:
        Never raises — catches errors and returns {"ok": False, "error": "..."}
    """
    if not tenant_id or not tenant_id.strip():
        return {"ok": False, "error": "tenant_id is required and cannot be empty"}

    try:
        _safe_heartbeat(f"InvestorAgent starting for tenant {tenant_id}")

        # Initialize state
        initial_state: InvestorState = {
            "tenant_id": tenant_id,
            "metrics": {},
            "memory_context": "",
            "draft": "",
            "narrative": "",
            "slack_message": "",
            "slack_blocks": [],
            "error": "",
            "retry_count": 0,
            "langfuse_trace_id": "",
        }

        _safe_heartbeat(f"Invoking investor_graph for tenant {tenant_id}")

        # LangGraph invoke is sync — run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: investor_graph.invoke(initial_state),
        )

        _safe_heartbeat(f"InvestorAgent completed for tenant {tenant_id}")

        # Return only the required output fields
        return {
            "ok": True,
            "tenant_id": result.get("tenant_id", tenant_id),
            "metrics": result.get("metrics", {}),
            "narrative": result.get("narrative", ""),
            "output_message": result.get("slack_message", ""),
            "slack_blocks": result.get("slack_blocks", []),
            "langfuse_trace_id": result.get("langfuse_trace_id", ""),
        }

    except Exception as e:
        _safe_heartbeat(f"InvestorAgent failed for tenant {tenant_id}: {e}")
        return {"ok": False, "error": str(e), "tenant_id": tenant_id}
