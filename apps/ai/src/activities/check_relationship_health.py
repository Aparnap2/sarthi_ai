"""
Check Relationship Health Activity for Temporal.

Checks investor relationships that need warming up.
"""
from __future__ import annotations

import logging
from typing import Any
from temporalio import activity

from src.db.investor_relationships import check_relationship_health as db_check_health

log = logging.getLogger(__name__)


@activity.defn(name="check_relationship_health")
async def check_relationship_health(tenant_id: str) -> dict[str, Any]:
    """
    Check for investors needing warmup.

    Args:
        tenant_id: Tenant identifier

    Returns:
        dict with health metrics and cold investors list
    """
    if not tenant_id:
        return {"ok": False, "error": "tenant_id is required"}

    try:
        health = db_check_health(tenant_id)
        return {
            "ok": True,
            "total_investors": health.get("total_investors", 0),
            "warm_relationships": health.get("warm_relationships", 0),
            "cold_relationships": health.get("cold_relationships", 0),
            "high_priority_cold": health.get("high_priority_cold", 0),
            "cold_investors": health.get("cold_investors", []),
        }
    except Exception as e:
        log.error(f"Failed to check relationship health for {tenant_id}: {e}")
        return {"ok": False, "error": str(e)}