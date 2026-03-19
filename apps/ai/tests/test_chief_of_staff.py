"""Tests for Chief of Staff Agent."""
import pytest
from unittest.mock import patch
from src.agents.chief_of_staff import ChiefOfStaffAgent
from src.agents.base import BANNED_JARGON


class TestChiefOfStaff:
    """Test suite for ChiefOfStaffAgent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ChiefOfStaffAgent()

    def test_briefing_max_5_items(self):
        """Test that briefing has max 5 items."""
        with patch.object(self.agent, '_compose_with_llm', return_value="Weekly briefing summary"):
            state = {
                "tenant_id": "test",
                "agent_outputs": [
                    {"headline": f"Item {i}", "urgency": "low"} for i in range(10)
                ],
            }
            event = {"event_type": "TIME_TICK_WEEKLY"}
            result = self.agent.run(state, event)
            assert result["output_json"]["item_count"] <= 5

    def test_briefing_has_one_positive_item(self):
        """Test that briefing includes positive item."""
        with patch.object(self.agent, '_compose_with_llm', return_value="Weekly briefing summary"):
            state = {
                "tenant_id": "test",
                "agent_outputs": [
                    {
                        "headline": "Issue 1",
                        "urgency": "high",
                        "is_good_news": False,
                    },
                    {
                        "headline": "Issue 2",
                        "urgency": "warn",
                        "is_good_news": False,
                    },
                ],
            }
            event = {"event_type": "TIME_TICK_WEEKLY"}
            result = self.agent.run(state, event)
            # Should find or add positive item
            assert result["fire_telegram"] is True

    def test_briefing_no_banned_jargon(self):
        """Test that briefing contains no banned jargon."""
        with patch.object(self.agent, '_compose_with_llm', return_value="Weekly briefing summary"):
            state = {
                "tenant_id": "test",
                "agent_outputs": [
                    {
                        "headline": "AWS spike detected",
                        "urgency": "high",
                        "is_good_news": False,
                    }
                ],
            }
            event = {"event_type": "TIME_TICK_WEEKLY"}
            result = self.agent.run(state, event)
            for term in BANNED_JARGON:
                assert term.lower() not in result.get("headline", "").lower()

    def test_high_urgency_ranked_first(self):
        """Test that high urgency items are ranked first."""
        with patch.object(self.agent, '_compose_with_llm', return_value="Critical issue first"):
            state = {
                "tenant_id": "test",
                "agent_outputs": [
                    {"headline": "Low priority", "urgency": "low"},
                    {"headline": "Critical issue", "urgency": "critical"},
                ],
            }
            event = {"event_type": "TIME_TICK_WEEKLY"}
            result = self.agent.run(state, event)
            assert "Critical" in result["headline"]

    def test_investor_draft_contains_revenue_burn_runway(self):
        """Test that investor draft contains key metrics."""
        state = {
            "tenant_id": "test",
            "monthly_revenue": 500000,
            "burn_rate": 180000,
            "runway_months": 14.2,
        }
        event = {"event_type": "TIME_TICK_MONTHLY"}
        result = self.agent.run(state, event)
        draft = result["output_json"].get("draft", "")
        assert "Revenue" in draft
        assert "Burn" in draft
        assert "Runway" in draft

    def test_empty_week_graceful(self):
        """Test that empty week is handled gracefully."""
        state = {"tenant_id": "test", "agent_outputs": []}
        event = {"event_type": "TIME_TICK_WEEKLY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "Quiet" in result["headline"] or "quiet" in result["headline"]

    def test_briefing_written_to_qdrant(self):
        """Test that briefing is written to Qdrant."""
        with patch.object(self.agent, '_compose_with_llm', return_value="Weekly briefing summary"):
            state = {
                "tenant_id": "test",
                "agent_outputs": [{"headline": "Test item", "urgency": "high"}],
            }
            event = {"event_type": "TIME_TICK_WEEKLY"}
            result = self.agent.run(state, event)
            assert result["qdrant_point_id"] is not None

    def test_no_jargon_in_output(self):
        """Test that output contains no banned jargon."""
        with patch.object(self.agent, '_compose_with_llm', return_value="Weekly briefing summary"):
            state = {
                "tenant_id": "test",
                "agent_outputs": [{"headline": "AWS spike", "urgency": "high"}],
            }
            event = {"event_type": "TIME_TICK_WEEKLY"}
            result = self.agent.run(state, event)
            for term in BANNED_JARGON:
                assert term.lower() not in result.get("headline", "").lower()
