"""
Run HiringAgent Activity for Temporal.

Scores and processes candidate applications.
"""
from __future__ import annotations

import logging
from typing import Any
from temporalio import activity

from src.agents.hiring.graph import run_hiring_agent

log = logging.getLogger(__name__)


@activity.defn(name="run_hiring_agent")
async def run_hiring_agent_activity(tenant_id: str, candidate_data: dict, role_id: int = None) -> dict[str, Any]:
    """
    Run hiring agent to score a candidate.

    Args:
        tenant_id: Tenant identifier
        candidate_data: Dict with candidate info (name, email, resume_text, etc.)
        role_id: Optional role ID

    Returns:
        dict with scores and recommendation
    """
    if not tenant_id:
        return {"ok": False, "error": "tenant_id is required"}

    if not candidate_data.get("name") or not candidate_data.get("email"):
        return {"ok": False, "error": "name and email are required"}

    try:
        result = await run_hiring_agent(tenant_id, candidate_data, role_id)
        return result
    except Exception as e:
        log.error(f"HiringAgent failed for {tenant_id}: {e}")
        return {"ok": False, "error": str(e)}