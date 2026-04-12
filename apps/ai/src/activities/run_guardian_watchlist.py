"""Guardian watchlist activity — runs all 16 patterns."""
from __future__ import annotations

from temporalio import activity


@activity.defn(name="run_guardian_watchlist")
async def run_guardian_watchlist(tenant_id: str, pulse_result: dict) -> dict:
    """Run Guardian watchlist detection against pulse metrics.

    Checks 16 blindspot patterns (churn, burn rate, runway, MRR anomalies)
    and returns any triggered alerts.

    Args:
        tenant_id: The tenant identifier.
        pulse_result: Output from run_pulse_agent containing metrics.

    Returns:
        dict with tenant_id, triggered blindspot IDs, and match count.
    """
    from src.guardian.detector import GuardianDetector

    signals = {
        "monthly_churn_pct": pulse_result.get("churn_pct", 0),
        "burn_rate_cents": pulse_result.get("burn_rate_cents", 0),
        "runway_days": pulse_result.get("runway_months", 999) * 30,
        "mrr_cents": pulse_result.get("mrr_cents", 0),
    }

    detector = GuardianDetector()
    matches = detector.run(signals)

    return {
        "tenant_id": tenant_id,
        "blindspots_triggered": [m.id for m in matches],
        "match_count": len(matches),
    }
