"""
Unit tests for InvestorAgent.

Tests cover:
  - InvestorState structure
  - fetch_metrics node
  - retrieve_memory node
  - generate_draft node
  - build_slack_message node

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
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434/v1"

TENANT = "test-investor-tenant-unit"


# =============================================================================
# TestInvestorState
# =============================================================================

class TestInvestorState:
    """Tests for InvestorState TypedDict structure."""

    def test_investor_state_creation_empty(self):
        """InvestorState can be created with no fields (all optional)."""
        from src.agents.investor.state import InvestorState

        state: InvestorState = {}
        assert isinstance(state, dict)
        assert len(state) == 0

    def test_investor_state_with_tenant_id(self):
        """InvestorState accepts tenant_id field."""
        from src.agents.investor.state import InvestorState

        state: InvestorState = {"tenant_id": TENANT}
        assert state["tenant_id"] == TENANT

    def test_investor_state_with_period_fields(self):
        """InvestorState accepts period_start and period_end fields."""
        from src.agents.investor.state import InvestorState

        state: InvestorState = {
            "tenant_id": TENANT,
            "period_start": "2026-03-18",
            "period_end": "2026-03-25",
        }
        assert state["period_start"] == "2026-03-18"
        assert state["period_end"] == "2026-03-25"


# =============================================================================
# TestFetchMetrics
# =============================================================================

class TestFetchMetrics:
    """Tests for fetch_metrics node."""

    def test_fetch_metrics_returns_data_sources(self):
        """fetch_metrics returns list of data sources used."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import fetch_metrics

        state: InvestorState = {"tenant_id": TENANT}
        result = fetch_metrics(state)

        assert "data_sources" in result
        assert isinstance(result["data_sources"], list)
        assert len(result["data_sources"]) > 0

    def test_fetch_metrics_returns_mrr_cents(self):
        """fetch_metrics returns mrr_cents in mock mode."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import fetch_metrics

        state: InvestorState = {"tenant_id": TENANT}
        result = fetch_metrics(state)

        assert "mrr_cents" in result
        assert isinstance(result["mrr_cents"], int)
        assert result["mrr_cents"] > 0  # Mock data has positive MRR

    def test_fetch_metrics_returns_burn_and_runway(self):
        """fetch_metrics returns burn_cents and runway_months."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import fetch_metrics

        state: InvestorState = {"tenant_id": TENANT}
        result = fetch_metrics(state)

        assert "burn_cents" in result
        assert "runway_months" in result
        assert isinstance(result["burn_cents"], int)
        assert isinstance(result["runway_months"], (int, float))


# =============================================================================
# TestRetrieveMemory
# =============================================================================

class TestRetrieveMemory:
    """Tests for retrieve_memory node."""

    def test_retrieve_memory_returns_wins_list(self):
        """retrieve_memory returns top_wins as list."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import retrieve_memory

        state: InvestorState = {"tenant_id": TENANT}
        result = retrieve_memory(state)

        assert "top_wins" in result
        assert isinstance(result["top_wins"], list)

    def test_retrieve_memory_returns_blockers_list(self):
        """retrieve_memory returns top_blockers as list."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import retrieve_memory

        state: InvestorState = {"tenant_id": TENANT}
        result = retrieve_memory(state)

        assert "top_blockers" in result
        assert isinstance(result["top_blockers"], list)

    def test_retrieve_memory_returns_historical_context(self):
        """retrieve_memory returns historical_context string."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import retrieve_memory

        state: InvestorState = {"tenant_id": TENANT}
        result = retrieve_memory(state)

        assert "historical_context" in result
        assert isinstance(result["historical_context"], str)


# =============================================================================
# TestGenerateDraft
# =============================================================================

class TestGenerateDraft:
    """Tests for generate_draft node."""

    def _create_state_with_data(self) -> Any:
        """Helper to create state with realistic test data."""
        from src.agents.investor.state import InvestorState

        return InvestorState(
            tenant_id=TENANT,
            period_start="2026-03-18",
            period_end="2026-03-25",
            mrr_cents=1250000,
            mrr_growth_pct=4.17,
            burn_cents=15000000,
            runway_months=3.0,
            new_customers=3,
            churned_customers=1,
            active_customers=25,
            top_wins=["Closed enterprise deal with Acme Corp", "Launched new analytics feature"],
            top_blockers=["Hiring delay for senior engineer", "Payment gateway integration issues"],
            historical_context="Previous update: MRR was ₹12,000",
        )

    def test_generate_draft_returns_draft_markdown(self):
        """generate_draft returns draft_markdown string."""
        from src.agents.investor.nodes import generate_draft

        state = self._create_state_with_data()
        result = generate_draft(state)

        assert "draft_markdown" in result
        assert isinstance(result["draft_markdown"], str)
        assert len(result["draft_markdown"]) > 0

    def test_generate_draft_returns_slack_preview(self):
        """generate_draft returns slack_preview string."""
        from src.agents.investor.nodes import generate_draft

        state = self._create_state_with_data()
        result = generate_draft(state)

        assert "slack_preview" in result
        # slack_preview may be empty if DSPy truncates, but field should exist
        assert isinstance(result["slack_preview"], str)

    def test_generate_draft_handles_missing_data(self):
        """generate_draft handles missing fields gracefully."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import generate_draft

        # Minimal state with missing fields
        state = InvestorState(tenant_id=TENANT)
        result = generate_draft(state)

        # Should not raise, should have fallback draft
        assert "draft_markdown" in result
        assert "slack_preview" in result
        assert len(result["draft_markdown"]) > 0


# =============================================================================
# TestBuildSlackMessage
# =============================================================================

class TestBuildSlackMessage:
    """Tests for build_slack_message node."""

    def test_build_slack_message_returns_blocks(self):
        """build_slack_message returns Slack Block Kit blocks."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import build_slack_message

        state = InvestorState(
            tenant_id=TENANT,
            slack_preview="Test preview for investor update...",
            draft_markdown="# Investor Update\n\nTest content",
            mrr_cents=1250000,
            burn_cents=15000000,
            runway_months=3.0,
            period_end="2026-03-25",
            data_sources=["stripe_mock", "bank_mock"],
        )
        result = build_slack_message(state)

        assert "slack_blocks" in result
        assert isinstance(result["slack_blocks"], list)
        assert len(result["slack_blocks"]) > 0

    def test_build_slack_message_header_block(self):
        """build_slack_message includes header block."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import build_slack_message

        state = InvestorState(
            tenant_id=TENANT,
            slack_preview="Test",
            draft_markdown="Test",
        )
        result = build_slack_message(state)

        blocks = result["slack_blocks"]
        header_found = any(
            b.get("type") == "header" for b in blocks
        )
        assert header_found

    def test_build_slack_message_includes_metrics(self):
        """build_slack_message includes metrics in blocks."""
        from src.agents.investor.state import InvestorState
        from src.agents.investor.nodes import build_slack_message

        state = InvestorState(
            tenant_id=TENANT,
            slack_preview="Test",
            draft_markdown="Test",
            mrr_cents=1250000,
            burn_cents=15000000,
            runway_months=3.0,
        )
        result = build_slack_message(state)

        blocks_text = " ".join(
            str(b.get("text", {})) for b in result["slack_blocks"]
        )
        # Should contain MRR or Burn or Runway info
        assert "MRR" in blocks_text or "Burn" in blocks_text or "Runway" in blocks_text
