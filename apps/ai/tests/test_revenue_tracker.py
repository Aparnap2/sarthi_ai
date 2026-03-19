"""Tests for Revenue Tracker Agent."""
import pytest
from unittest.mock import patch
from src.agents.revenue_tracker import RevenueTrackerAgent
from src.agents.base import BANNED_JARGON


class TestRevenueTracker:
    """Test suite for RevenueTrackerAgent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = RevenueTrackerAgent()

    def test_stale_deal_7d_fires(self):
        """Test that stale deals (>7 days) trigger alert."""
        state = {
            "tenant_id": "test",
            "pipeline_deals": [
                {
                    "name": "Acme",
                    "amount": 50000,
                    "stage": "NEGOTIATION",
                    "last_contact_at": "2026-03-01T00:00:00Z",
                }
            ],
        }
        event = {"event_type": "TIME_TICK_WEEKLY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "Acme" in result["headline"]

    def test_active_deal_silent(self):
        """Test that active deals do not trigger alert."""
        state = {
            "tenant_id": "test",
            "pipeline_deals": [
                {
                    "name": "Acme",
                    "stage": "NEGOTIATION",
                    "last_contact_at": "2026-03-17T00:00:00Z",
                }
            ],
        }
        event = {"event_type": "TIME_TICK_WEEKLY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is False

    def test_mrr_milestone_crosses_1L(self):
        """Test that crossing ₹1L MRR triggers celebration."""
        state = {"tenant_id": "test", "last_30d_mrr": 98000}
        event = {
            "event_type": "PAYMENT_SUCCESS",
            "amount": 3500,
            "customer_name": "Acme",
        }
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert result["is_good_news"] is True

    def test_routine_payment_silent(self):
        """Test that routine payments do not trigger alert."""
        state = {"tenant_id": "test", "last_30d_mrr": 50000}
        event = {"event_type": "PAYMENT_SUCCESS", "amount": 1500}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is False

    def test_concentration_risk_fires(self):
        """Test that high concentration (>30%) triggers warning."""
        state = {"tenant_id": "test", "top_customer_pct": 0.38}
        event = {
            "event_type": "PAYMENT_SUCCESS",
            "amount": 5000,
            "customer_name": "Acme",
        }
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "38%" in result["headline"]

    def test_no_jargon_in_output(self):
        """Test that output contains no banned jargon."""
        state = {
            "tenant_id": "test",
            "pipeline_deals": [
                {
                    "name": "Acme",
                    "stage": "NEGOTIATION",
                    "last_contact_at": "2026-03-01T00:00:00Z",
                }
            ],
        }
        event = {"event_type": "TIME_TICK_WEEKLY"}
        result = self.agent.run(state, event)
        for term in BANNED_JARGON:
            assert term.lower() not in result.get("headline", "").lower()
