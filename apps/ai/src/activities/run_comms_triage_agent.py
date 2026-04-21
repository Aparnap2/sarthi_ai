"""
Run CommsTriage Activity for Temporal.

Runs comms triage for specified Slack channels.
"""
from __future__ import annotations

import logging
from typing import Any
from temporalio import activity

from src.agents.comms.graph import run_comms_triage

log = logging.getLogger(__name__)


@activity.defn(name="run_comms_triage_agent")
async def run_comms_triage_agent(tenant_id: str, channels: list[str]) -> dict[str, Any]:
    """
    Run comms triage for specified Slack channels.

    Args:
        tenant_id: Tenant identifier
        channels: List of Slack channel names

    Returns:
        dict with digest, slack_blocks, and message counts
    """
    if not tenant_id:
        return {"ok": False, "error": "tenant_id is required"}

    if not channels:
        return {"ok": False, "error": "channels is required"}

    try:
        result = await run_comms_triage(tenant_id, channels)
        return result
    except Exception as e:
        log.error(f"CommsTriage failed for {tenant_id}: {e}")
        return {"ok": False, "error": str(e)}