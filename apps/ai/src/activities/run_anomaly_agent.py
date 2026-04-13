"""
AnomalyAgent Activity for Temporal.

Wraps the Anomaly LangGraph agent as a Temporal activity.
LangGraph invoke is sync — wrapped with asyncio.get_event_loop().run_in_executor().
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from temporalio import activity

from src.agents.anomaly.graph import anomaly_graph
from src.agents.anomaly.state import AnomalyState

log = logging.getLogger(__name__)


def _safe_heartbeat(message: str) -> None:
    """Safely call activity.heartbeat, ignoring errors outside activity context."""
    try:
        activity.heartbeat(message)
    except RuntimeError:
        # Not in activity context (e.g., during testing)
        log.debug("Heartbeat (no context): %s", message)


@activity.defn(name="run_anomaly_agent")
async def run_anomaly_agent(tenant_id: str, anomalies: list[str]) -> dict[str, Any]:
    """
    Execute the AnomalyAgent LangGraph for anomaly detection and explanation.

    This activity:
    1. Initializes AnomalyState with tenant_id and anomalies list
    2. Invokes the anomaly_graph LangGraph
    3. Returns the output with explanations, actions, and Slack message

    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        anomalies: List of anomaly IDs or descriptions to analyze

    Returns:
        dict with keys:
            - ok: bool (True on success, False on error)
            - tenant_id: str
            - anomalies: list[str] (input anomalies)
            - explanations: dict (anomaly explanations)
            - actions: list[str] (recommended actions)
            - output_message: str (formatted Slack message)
            - slack_blocks: list[dict] (Slack block kit format)
            - langfuse_trace_id: str
            - error: str (only if ok=False)

    Note:
        Never raises — catches errors and returns {"ok": False, "error": "..."}
    """
    if not tenant_id or not tenant_id.strip():
        return {"ok": False, "error": "tenant_id is required and cannot be empty"}

    if not anomalies or not isinstance(anomalies, list):
        return {"ok": False, "error": "anomalies must be a non-empty list"}

    try:
        _safe_heartbeat(f"AnomalyAgent starting for tenant {tenant_id} with {len(anomalies)} anomalies")

        # Initialize state
        initial_state: AnomalyState = {
            "tenant_id": tenant_id,
            "anomalies": anomalies,
            "memory_context": "",
            "explanations": {},
            "actions": [],
            "slack_message": "",
            "slack_blocks": [],
            "error": "",
            "retry_count": 0,
            "langfuse_trace_id": "",
        }

        _safe_heartbeat(f"Invoking anomaly_graph for tenant {tenant_id}")

        # LangGraph invoke is sync — run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: anomaly_graph.invoke(initial_state),
        )

        _safe_heartbeat(f"AnomalyAgent completed for tenant {tenant_id}")

        # Return only the required output fields
        return {
            "ok": True,
            "tenant_id": result.get("tenant_id", tenant_id),
            "anomalies": result.get("anomalies", anomalies),
            "explanations": result.get("explanations", {}),
            "actions": result.get("actions", []),
            "output_message": result.get("slack_message", ""),
            "slack_blocks": result.get("slack_blocks", []),
            "langfuse_trace_id": result.get("langfuse_trace_id", ""),
        }

    except Exception as e:
        _safe_heartbeat(f"AnomalyAgent failed for tenant {tenant_id}: {e}")
        return {"ok": False, "error": str(e), "tenant_id": tenant_id}
