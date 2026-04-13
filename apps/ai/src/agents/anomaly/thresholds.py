"""
Anomaly detection thresholds — rule-based, NO LLM.
Configurable per-tenant via overrides.
"""

ANOMALY_THRESHOLDS = {
    # Runway thresholds (days)
    "runway_drop": {
        "critical": 90,    # < 90 days → critical
        "warning": 180,    # < 180 days → warning
    },
    # MRR change thresholds (%)
    "mrr_drop": {
        "critical": -15.0,  # < -15% → critical
        "warning": -5.0,    # < -5% → warning
    },
    # Burn rate thresholds (ratio vs previous)
    "burn_spike": {
        "critical": 1.5,   # > 1.5x previous → critical
        "warning": 1.2,    # > 1.2x previous → warning
    },
    # Churn thresholds (count per month)
    "high_churn": {
        "critical": 3,     # >= 3 churned → critical
        "warning": 1,      # >= 1 churned → warning
    },
}


def detect_anomaly(state: dict) -> dict:
    """
    Rule-based anomaly detection. Returns:
    {
        "anomaly_detected": bool,
        "anomaly_type": str | None,
        "anomaly_severity": str | None,
        "threshold_used": float | None,
        "should_alert": bool,
    }
    """
    runway = state.get("runway_days", 999)
    mrr_change = state.get("mrr_change_pct", 0.0)
    burn = state.get("burn_rate_cents", 0)
    prev_burn = state.get("prev_burn_cents", burn)
    churned = state.get("churned_customers", 0)

    # Check runway
    if runway < ANOMALY_THRESHOLDS["runway_drop"]["critical"]:
        return {
            "anomaly_detected": True,
            "anomaly_type": "runway_drop",
            "anomaly_severity": "critical",
            "threshold_used": ANOMALY_THRESHOLDS["runway_drop"]["critical"],
            "should_alert": True,
        }
    elif runway < ANOMALY_THRESHOLDS["runway_drop"]["warning"]:
        return {
            "anomaly_detected": True,
            "anomaly_type": "runway_drop",
            "anomaly_severity": "warning",
            "threshold_used": ANOMALY_THRESHOLDS["runway_drop"]["warning"],
            "should_alert": True,
        }

    # Check MRR drop
    if mrr_change < ANOMALY_THRESHOLDS["mrr_drop"]["critical"]:
        return {
            "anomaly_detected": True,
            "anomaly_type": "mrr_drop",
            "anomaly_severity": "critical",
            "threshold_used": ANOMALY_THRESHOLDS["mrr_drop"]["critical"],
            "should_alert": True,
        }
    elif mrr_change < ANOMALY_THRESHOLDS["mrr_drop"]["warning"]:
        return {
            "anomaly_detected": True,
            "anomaly_type": "mrr_drop",
            "anomaly_severity": "warning",
            "threshold_used": ANOMALY_THRESHOLDS["mrr_drop"]["warning"],
            "should_alert": True,
        }

    # Check burn spike
    if prev_burn > 0:
        burn_ratio = burn / prev_burn
        if burn_ratio > ANOMALY_THRESHOLDS["burn_spike"]["critical"]:
            return {
                "anomaly_detected": True,
                "anomaly_type": "burn_spike",
                "anomaly_severity": "critical",
                "threshold_used": ANOMALY_THRESHOLDS["burn_spike"]["critical"],
                "should_alert": True,
            }
        elif burn_ratio > ANOMALY_THRESHOLDS["burn_spike"]["warning"]:
            return {
                "anomaly_detected": True,
                "anomaly_type": "burn_spike",
                "anomaly_severity": "warning",
                "threshold_used": ANOMALY_THRESHOLDS["burn_spike"]["warning"],
                "should_alert": True,
            }

    # Check high churn
    if churned >= ANOMALY_THRESHOLDS["high_churn"]["critical"]:
        return {
            "anomaly_detected": True,
            "anomaly_type": "high_churn",
            "anomaly_severity": "critical",
            "threshold_used": ANOMALY_THRESHOLDS["high_churn"]["critical"],
            "should_alert": True,
        }
    elif churned >= ANOMALY_THRESHOLDS["high_churn"]["warning"]:
        return {
            "anomaly_detected": True,
            "anomaly_type": "high_churn",
            "anomaly_severity": "warning",
            "threshold_used": ANOMALY_THRESHOLDS["high_churn"]["warning"],
            "should_alert": True,
        }

    # No anomaly detected
    return {
        "anomaly_detected": False,
        "anomaly_type": None,
        "anomaly_severity": None,
        "threshold_used": None,
        "should_alert": False,
    }
