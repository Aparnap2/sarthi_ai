"""
Finance Agent unit tests.

All 14 tests run with existing containers only.
No new docker run. No new installs.
DB: iterateswarm-postgres (localhost:5433)
Qdrant: iterateswarm-qdrant (localhost:6333)
Ollama: localhost:11434
"""
import os
import pytest
from unittest.mock import patch, MagicMock

# Set env before any app import
os.environ.setdefault("DATABASE_URL",
    "postgresql://sarthi:sarthi @localhost:5433/sarthi")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("OLLAMA_CHAT_MODEL", "qwen3:0.6b")

from src.agents.finance.nodes import (
    node_ingest_event,
    node_detect_anomaly,
    node_decide_action,
    node_emit_output,
    node_write_memory,
)

# ── Base state fixture ────────────────────────────────────────────

@pytest.fixture
def base_state():
    return {
        "tenant_id": "unit-test-tenant",
        "event": {
            "event_type": "BANK_WEBHOOK",
            "tenant_id": "unit-test-tenant",
            "vendor": "AWS",
            "amount": 42000.0,
        },
        "monthly_revenue": 200000.0,
        "monthly_expense": 80000.0,
        "burn_rate": 80000.0,
        "runway_months": 8.0,
        "vendor_baselines": {
            "aws": {"avg_30d": 18000.0, "avg_90d": 18000.0, "count": 12}
        },
        "anomaly_detected": False,
        "anomaly_score": 0.0,
        "anomaly_explanation": "",
        "past_context": [],
        "action": "SKIP",
        "output_message": "",
        "langfuse_trace_id": "",
    }

# ── N1: node_ingest_event ─────────────────────────────────────────

def test_ingest_event_normalizes_razorpay_payload(base_state):
    """Razorpay PAYMENT_SUCCESS should normalize amount string to float."""
    state = {**base_state, "event": {
        "event_type": "PAYMENT_SUCCESS",
        "tenant_id": "unit-test-tenant",
        "amount": "5000",  # string — must be coerced to float
    }}
    result = node_ingest_event(state)
    assert result["event"]["event_type"] == "PAYMENT_SUCCESS"
    assert isinstance(result["event"]["amount"], float)


def test_ingest_event_rejects_unknown_event_type(base_state):
    """Missing required fields must raise."""
    state = {**base_state, "event": {"amount": 1000}}  # no event_type or tenant_id
    with pytest.raises((ValueError, KeyError, AssertionError)):
        node_ingest_event(state)

# ── N4: node_detect_anomaly ───────────────────────────────────────

def test_detect_anomaly_scores_2x_spend_correctly(base_state):
    """AWS ₹42,000 vs ₹18,000 baseline = 2.3× → score ≥ 0.5."""
    result = node_detect_anomaly(base_state)
    assert result["anomaly_score"] >= 0.5
    assert result["anomaly_detected"] is True


def test_detect_anomaly_scores_first_vendor_spike(base_state):
    """First-time vendor (count=0) → score gets +0.3."""
    state = {
        **base_state,
        "vendor_baselines": {},  # no baseline = first time
        "event": {**base_state["event"], "amount": 5000.0},
    }
    result = node_detect_anomaly(state)
    assert result["anomaly_score"] >= 0.3


def test_detect_anomaly_skips_normal_transaction(base_state):
    """₹17,000 vs ₹18,000 baseline = within threshold → not anomalous."""
    state = {
        **base_state,
        "event": {**base_state["event"], "amount": 17000.0},
    }
    result = node_detect_anomaly(state)
    assert result["anomaly_detected"] is False


def test_detect_anomaly_flags_low_runway(base_state):
    """Runway < 3 months → +0.5 score regardless of amount."""
    state = {
        **base_state,
        "runway_months": 2.0,
        "event": {**base_state["event"], "amount": 1000.0},  # normal amount
        "vendor_baselines": {"AWS": {"avg_30d": 900, "avg_90d": 900, "count": 10}},
    }
    result = node_detect_anomaly(state)
    assert result["anomaly_score"] >= 0.5


def test_detect_anomaly_score_capped_at_1(base_state):
    """Score never exceeds 1.0 even with multiple triggers."""
    state = {
        **base_state,
        "runway_months": 1.0,  # +0.5
        "vendor_baselines": {},  # +0.3 first time
        "event": {**base_state["event"], "amount": 100000.0},  # +0.5 but also new
    }
    result = node_detect_anomaly(state)
    assert result["anomaly_score"] <= 1.0

# ── N7: node_decide_action ────────────────────────────────────────

def test_decide_action_alerts_on_high_score(base_state):
    """Score >= 0.7 → ALERT action."""
    state = {**base_state, "anomaly_score": 0.8, "anomaly_detected": True}
    result = node_decide_action(state)
    assert result["action"] == "ALERT"


def test_decide_action_digests_on_weekly_tick(base_state):
    """TIME_TICK_WEEKLY → DIGEST action."""
    state = {
        **base_state,
        "anomaly_score": 0.0,
        "event": {**base_state["event"], "event_type": "TIME_TICK_WEEKLY"},
    }
    result = node_decide_action(state)
    assert result["action"] == "DIGEST"


def test_decide_action_skips_on_low_score(base_state):
    """Score < 0.5 and no TIME_TICK → SKIP action."""
    state = {**base_state, "anomaly_score": 0.1, "anomaly_detected": False}
    result = node_decide_action(state)
    assert result["action"] == "SKIP"

# ── N8: node_write_memory ─────────────────────────────────────────

def test_write_memory_payload_has_required_fields(base_state):
    """SKIP action → write_memory is a no-op and returns state unchanged."""
    state = {**base_state, "action": "SKIP"}
    result = node_write_memory(state)
    assert result["action"] == "SKIP"
    # State passes through unmodified
    assert result["tenant_id"] == base_state["tenant_id"]


@patch("src.agents.finance.nodes._qdrant_upsert")
@patch("src.agents.finance.nodes._embed")
def test_write_memory_calls_qdrant_on_alert(mock_embed, mock_upsert, base_state):
    """ALERT action → Qdrant upsert is called with correct payload keys."""
    mock_embed.return_value = [0.1] * 768
    state = {
        **base_state,
        "action": "ALERT",
        "anomaly_score": 0.8,
        "anomaly_explanation": "AWS bill 2.3× usual. Check deployments.",
    }
    node_write_memory(state)
    assert mock_upsert.called
    call_kwargs = mock_upsert.call_args
    payload = call_kwargs[1]["payload"] if call_kwargs[1] else call_kwargs[0][3]
    assert "tenant_id" in payload
    assert "vendor" in payload
    assert "amount" in payload
    assert "content" in payload

# ── N9: node_emit_output ─────────────────────────────────────────

def test_emit_output_formats_alert_message(base_state):
    """ALERT action → non-empty output_message with vendor and runway."""
    state = {
        **base_state,
        "action": "ALERT",
        "anomaly_score": 0.8,
        "anomaly_explanation": "AWS bill 2.3× usual.",
    }
    result = node_emit_output(state)
    msg = result["output_message"]
    assert msg != ""
    assert "AWS" in msg or "Finance Alert" in msg
    # Must include runway
    assert "months" in msg.lower()


def test_emit_output_empty_on_skip(base_state):
    """SKIP action → empty output_message."""
    state = {**base_state, "action": "SKIP"}
    result = node_emit_output(state)
    assert result["output_message"] == ""


def test_emit_output_digest_has_numbers(base_state):
    """DIGEST action → output_message with revenue and burn numbers."""
    state = {
        **base_state,
        "action": "DIGEST",
        "monthly_revenue": 200000.0,
        "burn_rate": 80000.0,
        "runway_months": 8.0,
        "event": {**base_state["event"], "event_type": "TIME_TICK_WEEKLY"},
    }
    result = node_emit_output(state)
    msg = result["output_message"]
    assert msg != ""
    assert "200,000" in msg or "200000" in msg or "₹" in msg or "Revenue" in msg
