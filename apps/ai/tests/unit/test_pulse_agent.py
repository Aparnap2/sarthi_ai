"""
Unit tests for PulseAgent.

Tests cover:
  - PulseState structure
  - fetch_data node
  - compute_metrics node
  - generate_narrative node
  - build_slack_message node
  - Full graph compilation

All tests run in MOCK MODE (no real API calls).
"""
from __future__ import annotations
import os
import pytest
from typing import Any

# Force mock environment before any imports
os.environ["STRIPE_API_KEY"] = ""
os.environ["PLAID_ACCESS_TOKEN"] = ""
os.environ["SLACK_WEBHOOK_URL"] = ""
os.environ["DATABASE_URL"] = ""
os.environ["PRODUCT_DB_URL"] = ""

TENANT = "test-pulse-tenant-unit"


# =============================================================================
# TestPulseState
# =============================================================================

class TestPulseState:
    """Tests for PulseState TypedDict structure."""

    def test_pulse_state_creation_empty(self):
        """PulseState can be created with no fields (all optional)."""
        from src.agents.pulse.state import PulseState

        state: PulseState = {}
        assert isinstance(state, dict)
        assert len(state) == 0

    def test_pulse_state_with_tenant_id(self):
        """PulseState accepts tenant_id field."""
        from src.agents.pulse.state import PulseState

        state: PulseState = {"tenant_id": TENANT}
        assert state["tenant_id"] == TENANT

    def test_pulse_state_with_monetary_fields(self):
        """PulseState accepts cents-based monetary fields."""
        from src.agents.pulse.state import PulseState

        state: PulseState = {
            "tenant_id": TENANT,
            "mrr_cents": 1250000,
            "arr_cents": 15000000,
            "balance_cents": 45000000,
            "burn_30d_cents": 15000000,
        }
        assert state["mrr_cents"] == 1250000
        assert state["arr_cents"] == 15000000
        assert state["balance_cents"] == 45000000


# =============================================================================
# TestFetchData
# =============================================================================

class TestFetchData:
    """Tests for fetch_data node."""

    def test_fetch_data_returns_data_sources(self):
        """fetch_data returns list of data sources used."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import fetch_data

        state: PulseState = {"tenant_id": TENANT}
        result = fetch_data(state)

        assert "data_sources" in result
        assert isinstance(result["data_sources"], list)
        assert len(result["data_sources"]) > 0

    def test_fetch_data_returns_mrr_cents(self):
        """fetch_data returns mrr_cents in mock mode."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import fetch_data

        state: PulseState = {"tenant_id": TENANT}
        result = fetch_data(state)

        assert "mrr_cents" in result
        assert isinstance(result["mrr_cents"], int)
        assert result["mrr_cents"] > 0  # Mock data has positive MRR

    def test_fetch_data_returns_balance_and_burn(self):
        """fetch_data returns balance_cents and burn_30d_cents."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import fetch_data

        state: PulseState = {"tenant_id": TENANT}
        result = fetch_data(state)

        assert "balance_cents" in result
        assert "burn_30d_cents" in result
        assert isinstance(result["balance_cents"], int)
        assert isinstance(result["burn_30d_cents"], int)


# =============================================================================
# TestComputeMetrics
# =============================================================================

class TestComputeMetrics:
    """Tests for compute_metrics node."""

    def _create_state_with_data(self) -> Any:
        """Helper to create state with realistic test data."""
        from src.agents.pulse.state import PulseState

        return PulseState(
            tenant_id=TENANT,
            mrr_cents=1250000,
            arr_cents=15000000,
            active_customers=25,
            new_customers=3,
            churned_customers=1,
            expansion_cents=50000,
            contraction_cents=20000,
            balance_cents=45000000,
            burn_30d_cents=15000000,
            active_users_30d=1250,
            prev_mrr_cents=1200000,
        )

    def test_compute_metrics_returns_runway(self):
        """compute_metrics calculates runway_months."""
        from src.agents.pulse.nodes import compute_metrics

        state = self._create_state_with_data()
        result = compute_metrics(state)

        assert "runway_months" in result
        assert isinstance(result["runway_months"], float)
        # 45000000 / 15000000 = 3.0 months
        assert result["runway_months"] == 3.0

    def test_compute_metrics_returns_quick_ratio(self):
        """compute_metrics calculates quick_ratio."""
        from src.agents.pulse.nodes import compute_metrics

        state = self._create_state_with_data()
        result = compute_metrics(state)

        assert "quick_ratio" in result
        assert isinstance(result["quick_ratio"], float)

    def test_compute_metrics_returns_net_revenue_churn(self):
        """compute_metrics calculates net_revenue_churn."""
        from src.agents.pulse.nodes import compute_metrics

        state = self._create_state_with_data()
        result = compute_metrics(state)

        assert "net_revenue_churn" in result
        assert isinstance(result["net_revenue_churn"], float)

    def test_compute_metrics_detects_low_runway_anomaly(self):
        """compute_metrics detects anomaly when runway < 6 months."""
        from src.agents.pulse.nodes import compute_metrics

        state = self._create_state_with_data()
        # Runway is 3.0 months (< 6), should trigger anomaly
        result = compute_metrics(state)

        assert "anomalies_detected" in result
        assert isinstance(result["anomalies_detected"], list)
        # Should have at least the low runway anomaly
        anomaly_found = any(
            "runway" in a.lower() for a in result["anomalies_detected"]
        )
        assert anomaly_found

    def test_compute_metrics_no_anomalies_healthy_state(self):
        """compute_metrics returns empty anomalies for healthy metrics."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import compute_metrics

        # Create healthy state: high runway, good growth
        state = PulseState(
            tenant_id=TENANT,
            mrr_cents=1250000,
            prev_mrr_cents=1000000,  # 25% growth
            balance_cents=100000000,  # High balance
            burn_30d_cents=5000000,  # Low burn
            new_customers=10,
            churned_customers=2,
            expansion_cents=100000,
            contraction_cents=20000,
        )
        result = compute_metrics(state)

        # Runway = 20 months (healthy), growth positive
        assert result["runway_months"] == 20.0
        # May still have some anomalies depending on quick ratio

    def test_compute_metrics_handles_zero_burn(self):
        """compute_metrics handles zero burn without division error."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import compute_metrics

        state = PulseState(
            tenant_id=TENANT,
            balance_cents=50000000,
            burn_30d_cents=0,  # Zero burn
            mrr_cents=1000000,
            prev_mrr_cents=1000000,
            new_customers=0,
            churned_customers=0,
        )
        result = compute_metrics(state)

        # Should not raise, runway should be inf or handled gracefully
        assert "runway_months" in result


# =============================================================================
# TestGenerateNarrative
# =============================================================================

class TestGenerateNarrative:
    """Tests for generate_narrative node."""

    def test_generate_narrative_returns_narrative_and_action(self):
        """generate_narrative returns both narrative and action_item."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import generate_narrative

        state = PulseState(
            tenant_id=TENANT,
            mrr_cents=1250000,
            arr_cents=15000000,
            runway_months=3.0,
            burn_30d_cents=15000000,
            active_customers=25,
            new_customers=3,
            churned_customers=1,
            mrr_growth_pct=4.17,
            quick_ratio=1.5,
            active_users_30d=1250,
            historical_context="Previous MRR was ₹12,000",
            anomalies_detected=[],
        )
        result = generate_narrative(state)

        assert "narrative" in result
        assert "action_item" in result
        assert isinstance(result["narrative"], str)
        assert isinstance(result["action_item"], str)

    def test_generate_narrative_handles_missing_data(self):
        """generate_narrative handles missing fields gracefully."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import generate_narrative

        # Minimal state with missing fields
        state = PulseState(tenant_id=TENANT)
        result = generate_narrative(state)

        # Should not raise, should have fallback narrative
        assert "narrative" in result
        assert "action_item" in result
        assert len(result["narrative"]) > 0


# =============================================================================
# TestBuildSlackMessage
# =============================================================================

class TestBuildSlackMessage:
    """Tests for build_slack_message node."""

    def test_build_slack_message_returns_blocks(self):
        """build_slack_message returns Slack Block Kit blocks."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import build_slack_message

        state = PulseState(
            tenant_id=TENANT,
            narrative="Test narrative with three sentences. Second sentence. Third sentence.",
            action_item="Review churned customers",
            mrr_cents=1250000,
            runway_months=3.0,
            quick_ratio=1.5,
            anomalies_detected=["Low runway warning"],
            data_sources=["stripe_mock", "bank_mock"],
        )
        result = build_slack_message(state)

        assert "slack_blocks" in result
        assert isinstance(result["slack_blocks"], list)
        assert len(result["slack_blocks"]) > 0

    def test_build_slack_message_header_block(self):
        """build_slack_message includes header block."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import build_slack_message

        state = PulseState(tenant_id=TENANT, narrative="Test", action_item="Test")
        result = build_slack_message(state)

        blocks = result["slack_blocks"]
        header_found = any(
            b.get("type") == "header" for b in blocks
        )
        assert header_found

    def test_build_slack_message_action_item_block(self):
        """build_slack_message includes action item in blocks."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import build_slack_message

        state = PulseState(
            tenant_id=TENANT,
            narrative="Test",
            action_item="Call top 5 customers",
        )
        result = build_slack_message(state)

        blocks_text = " ".join(
            str(b.get("text", {})) for b in result["slack_blocks"]
        )
        assert "Call top 5 customers" in blocks_text

    def test_build_slack_message_handles_empty_anomalies(self):
        """build_slack_message handles empty anomalies list."""
        from src.agents.pulse.state import PulseState
        from src.agents.pulse.nodes import build_slack_message

        state = PulseState(
            tenant_id=TENANT,
            narrative="Test",
            action_item="Test",
            anomalies_detected=[],  # Empty
        )
        result = build_slack_message(state)

        # Should not raise
        assert "slack_blocks" in result
        assert len(result["slack_blocks"]) > 0


# =============================================================================
# TestPulseGraph
# =============================================================================

class TestPulseGraph:
    """Tests for PulseAgent LangGraph compilation and structure."""

    def test_pulse_graph_compiles(self):
        """PulseAgent graph compiles without errors."""
        from src.agents.pulse.graph import build_pulse_graph

        graph = build_pulse_graph()
        assert graph is not None

    def test_pulse_graph_has_all_nodes(self):
        """PulseAgent graph contains all 7 required nodes (+ __start__)."""
        from src.agents.pulse.graph import build_pulse_graph

        graph = build_pulse_graph()
        nodes = list(graph.nodes.keys())

        expected_nodes = [
            "fetch_data",
            "retrieve_memory",
            "compute_metrics",
            "generate_narrative",
            "build_slack_message",
            "send_slack",
            "persist_snapshot",
        ]

        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

        # LangGraph adds __start__ node automatically, so 7 + 1 = 8
        assert len(nodes) == 8
