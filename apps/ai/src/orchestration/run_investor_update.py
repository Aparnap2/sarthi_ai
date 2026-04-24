"""
Investor Update Orchestration.

Reuses existing run_investor_agent and check_relationship_health logic.
Preserves criteria-based evaluation.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from src.activities.run_investor_agent import run_investor_agent
from src.activities.check_relationship_health import check_relationship_health
from src.activities.send_slack_message import send_slack_message
from src.events.bus import emit

log = logging.getLogger(__name__)


async def run_investor_update(tenant_id: str) -> dict[str, Any]:
    """
    Run investor update job.

    This orchestrates:
    1. Check investor relationship health (warmup alerts)
    2. Run InvestorAgent to generate investor update
    3. Send Slack notification

    Args:
        tenant_id: Tenant identifier

    Returns:
        dict with execution results
    """
    run_id = str(uuid4())
    log.info(f"Running investor update for {tenant_id}, run_id={run_id}")

    result = {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "relationship_health": {},
        "investor_result": {},
        "ok": True,
    }

    # Step 1: Check relationship health
    try:
        relationship_health = await check_relationship_health(tenant_id)
        result["relationship_health"] = relationship_health

        if relationship_health.get("ok") and relationship_health.get("high_priority_cold", 0) > 0:
            cold_count = relationship_health["high_priority_cold"]
            log.warning(f"{cold_count} high-priority investors need warmup")

    except Exception as e:
        log.warning(f"Relationship health check failed: {e}")

    # Step 2: Run InvestorAgent
    try:
        investor_result = await run_investor_agent(tenant_id)
        result["investor_result"] = investor_result

        if not investor_result.get("ok"):
            error_msg = investor_result.get("error", "Unknown error")
            log.error(f"InvestorAgent failed: {error_msg}")

            await send_slack_message(
                f"❌ Investor Update failed for {tenant_id}: {error_msg}",
            )

            result["ok"] = False
            result["error"] = error_msg
            return result

        log.info(f"InvestorAgent completed: {investor_result.get('narrative', '')[:100]}")

    except Exception as e:
        log.error(f"InvestorAgent activity failed: {e}")

        await send_slack_message(
            f"❌ Investor Update failed for {tenant_id}: {str(e)}",
        )

        result["ok"] = False
        result["error"] = str(e)
        return result

    # Step 3: Send Slack notification
    try:
        narrative = investor_result.get("narrative", "No narrative generated")
        slack_blocks = investor_result.get("slack_blocks", [])

        await send_slack_message(
            narrative,
            blocks=slack_blocks if slack_blocks else None,
        )

    except Exception as e:
        log.warning(f"Slack notification failed: {e}")

    # Emit completion event
    await emit("investor.completed", tenant_id, {
        "run_id": run_id,
        "agent": "investor",
    })

    return result