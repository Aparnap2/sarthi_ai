"""
PulseAgent Activity for Temporal.

Wraps the Pulse LangGraph agent as a Temporal activity.
LangGraph invoke is sync — wrapped with asyncio.get_event_loop().run_in_executor().
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from temporalio import activity

from src.agents.pulse.graph import pulse_graph
from src.agents.pulse.state import PulseState

log = logging.getLogger(__name__)


def _safe_heartbeat(message: str) -> None:
    """Safely call activity.heartbeat, ignoring errors outside activity context."""
    try:
        activity.heartbeat(message)
    except RuntimeError:
        # Not in activity context (e.g., during testing)
        log.debug("Heartbeat (no context): %s", message)


@activity.defn(name="run_pulse_agent")
async def run_pulse_agent(tenant_id: str) -> dict[str, Any]:
    """
    Execute the PulseAgent LangGraph for daily metrics digest.

    This activity:
    1. Initializes PulseState with tenant_id
    2. Invokes the pulse_graph LangGraph
    3. Returns the output with metrics, narrative, and Slack message

    Args:
        tenant_id: Tenant identifier for multi-tenant isolation

    Returns:
        dict with keys:
            - ok: bool (True on success, False on error)
            - tenant_id: str
            - metrics: dict (computed metrics)
            - narrative: str (plain English summary)
            - output_message: str (formatted Slack message)
            - langfuse_trace_id: str
            - error: str (only if ok=False)

    Note:
        Never raises — catches errors and returns {"ok": False, "error": "..."}
    """
    if not tenant_id or not tenant_id.strip():
        return {"ok": False, "error": "tenant_id is required and cannot be empty"}

    try:
        _safe_heartbeat(f"PulseAgent starting for tenant {tenant_id}")

        # Initialize state
        initial_state: PulseState = {
            "tenant_id": tenant_id,
            "metrics": {},
            "memory_context": "",
            "narrative": "",
            "slack_message": "",
            "slack_blocks": [],
            "snapshot_id": "",
            "error": "",
            "retry_count": 0,
            "langfuse_trace_id": "",
        }

        _safe_heartbeat(f"Invoking pulse_graph for tenant {tenant_id}")

        # LangGraph invoke is sync — run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: pulse_graph.invoke(initial_state),
        )

        _safe_heartbeat(f"PulseAgent completed for tenant {tenant_id}")

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
        _safe_heartbeat(f"PulseAgent failed for tenant {tenant_id}: {e}")
        return {"ok": False, "error": str(e), "tenant_id": tenant_id}
