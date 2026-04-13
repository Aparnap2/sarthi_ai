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
        pulse_result: Output from run_pulse_agent containing metrics and
            guardian_signals computed by compute_metrics.

    Returns:
        dict with tenant_id, triggered blindspot IDs, match count, and
            detailed match info for each triggered pattern.
    """
    from src.guardian.detector import GuardianDetector

    # Use the full guardian_signals dict computed by compute_metrics node.
    # Fall back to building signals from pulse_result if guardian_signals
    # is not present (backward compatibility).
    signals = pulse_result.get("guardian_signals")
    if signals is None:
        # Legacy fallback: build minimal signal dict from raw pulse_result
        signals = {
            "monthly_churn_pct": pulse_result.get("churn_pct", 0),
            "burn_rate": pulse_result.get("burn_30d_cents", 0),
            "prev_burn_rate": pulse_result.get("prev_burn_cents", 0),
            "runway_days": pulse_result.get("runway_months", 999) * 30,
            "total_mrr": pulse_result.get("mrr_cents", 0),
            "mrr": pulse_result.get("mrr_cents", 0),
        }

    detector = GuardianDetector()
    matches = detector.run(signals)

    match_details = []
    for m in matches:
        match_details.append({
            "id": m.id,
            "name": m.name,
            "domain": m.domain,
            "severity": m.severity,
            "one_action": m.one_action,
        })

    return {
        "tenant_id": tenant_id,
        "blindspots_triggered": [m.id for m in matches],
        "match_count": len(matches),
        "matches": match_details,
    }
