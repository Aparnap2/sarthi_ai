"""
Check Cold Candidates Activity for Temporal.

Finds candidates who haven't been contacted recently.
"""
from __future__ import annotations

import logging
from typing import Any
from temporalio import activity

from src.db.hiring import get_cold_candidates

log = logging.getLogger(__name__)


@activity.defn(name="check_cold_candidates")
async def check_cold_candidates(tenant_id: str, days_threshold: int = 7) -> dict[str, Any]:
    """
    Find candidates who haven't been contacted recently.

    Args:
        tenant_id: Tenant identifier
        days_threshold: Days without contact to consider cold (default 7)

    Returns:
        dict with list of cold candidates
    """
    if not tenant_id:
        return {"ok": False, "error": "tenant_id is required"}

    try:
        cold = get_cold_candidates(tenant_id, days_threshold)
        return {
            "ok": True,
            "cold_candidates": cold,
            "count": len(cold),
        }
    except Exception as e:
        log.error(f"Failed to check cold candidates for {tenant_id}: {e}")
        return {"ok": False, "error": str(e)}