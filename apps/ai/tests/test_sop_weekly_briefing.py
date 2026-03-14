"""
Test suite for SOP_WEEKLY_BRIEFING.

Tests run with mocked database calls (TDD pattern).
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from src.sops.weekly_briefing import WeeklyBriefingSOP, MAX_BRIEFING_ITEMS
from src.sops.base import SOPResult, BANNED_JARGON


class TestWeeklyBriefingSOP:
    """Test suite for WeeklyBriefingSOP."""

    @pytest.fixture
    def sop(self):
        """Create SOP instance."""
        return WeeklyBriefingSOP()

    def test_sop_name_is_correct(self, sop):
        """SOP should have correct name."""
        assert sop.sop_name == "SOP_WEEKLY_BRIEFING"

    def test_max_briefing_items_constant(self):
        """Verify max briefing items is 5."""
        assert MAX_BRIEFING_ITEMS == 5

    @pytest.mark.asyncio
    async def test_briefing_contains_max_5_items(self, sop):
        """Weekly briefing should have max 5 items."""
        founder_id = str(uuid.uuid4())
        payload_ref = "cron:ops.cron.weekly"
        
        # Mock 10 items from desks (should be trimmed to 5)
        mock_items = [{"headline": f"Item {i}", "urgency": i} for i in range(10)]
        
        with patch.object(sop, '_collect_from_all_desks', return_value=mock_items):
            with patch.object(sop, '_score_and_rank', return_value=mock_items[:5]):
                with patch.object(sop, '_find_positive', return_value=None):
                    with patch.object(sop, '_apply_tone_filter', side_effect=lambda x: x):
                        result = await sop.execute(payload_ref, founder_id)
        
        assert len(result.output["items"]) <= 5

    @pytest.mark.asyncio
    async def test_briefing_always_includes_positive_if_exists(self, sop):
        """
        If positive news exists, at least one item should be positive.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "cron:ops.cron.weekly"
        
        # Mock items with no positive news
        mock_items = [
            {"headline": "GST due Friday", "is_good_news": False, "urgency": 10},
            {"headline": "3 invoices overdue", "is_good_news": False, "urgency": 8},
        ]
        mock_positive = {"headline": "Hit ₹5L MRR 🎉", "is_good_news": True, "urgency": 5}
        
        with patch.object(sop, '_collect_from_all_desks', return_value=mock_items):
            with patch.object(sop, '_score_and_rank', return_value=mock_items):
                with patch.object(sop, '_find_positive', return_value=mock_positive):
                    with patch.object(sop, '_apply_tone_filter', side_effect=lambda x: x):
                        result = await sop.execute(payload_ref, founder_id)
        
        # Should include positive item
        assert any(item.get("is_good_news") for item in result.output["items"])

    @pytest.mark.asyncio
    async def test_briefing_output_is_jargon_free(self, sop):
        """All briefing items should be jargon-free."""
        founder_id = str(uuid.uuid4())
        payload_ref = "cron:ops.cron.weekly"
        
        mock_items = [
            {"headline": "GST due Friday", "urgency": 10, "hitl_risk": "high"},
        ]
        
        with patch.object(sop, '_collect_from_all_desks', return_value=mock_items):
            with patch.object(sop, '_score_and_rank', return_value=mock_items):
                with patch.object(sop, '_find_positive', return_value=None):
                    with patch.object(sop, '_apply_tone_filter', side_effect=lambda x: x):
                        result = await sop.execute(payload_ref, founder_id)
        
        # Validate tone
        violations = result.validate_tone()
        assert len(violations) == 0, f"Jargon violations: {violations}"

    @pytest.mark.asyncio
    async def test_score_and_rank_sorts_by_urgency(self, sop):
        """Should sort items by urgency (highest first)."""
        items = [
            {"headline": "Low priority", "urgency": 1},
            {"headline": "High priority", "urgency": 10},
            {"headline": "Medium priority", "urgency": 5},
        ]
        
        ranked = sop._score_and_rank(items)
        
        assert ranked[0]["urgency"] == 10  # Highest first
        assert ranked[1]["urgency"] == 5
        assert ranked[2]["urgency"] == 1

    @pytest.mark.asyncio
    async def test_apply_tone_filter_removes_jargon(self, sop):
        """Tone filter should remove jargon from items."""
        item = {
            "headline": "Leverage synergies to optimize runway",
            "urgency": 5,
        }
        
        filtered = sop._apply_tone_filter(item)
        
        # Should not contain banned terms
        for term in BANNED_JARGON:
            assert term.lower() not in filtered.get("headline", "").lower()

    def test_tone_filter_clean_input(self, sop):
        """Tone filter should pass clean input unchanged."""
        item = {
            "headline": "Your revenue increased this month",
            "urgency": 5,
        }
        
        filtered = sop._apply_tone_filter(item)
        
        assert filtered["headline"] == item["headline"]

    @pytest.mark.asyncio
    async def test_full_briefing_execution(self, sop):
        """
        Full weekly briefing execution with all desks.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "cron:ops.cron.weekly"
        
        mock_items = [
            {"headline": "GST due Friday", "urgency": 10, "hitl_risk": "high", "is_good_news": False},
            {"headline": "Hit ₹5L MRR 🎉", "urgency": 5, "hitl_risk": "low", "is_good_news": True},
        ]
        
        with patch.object(sop, '_collect_from_all_desks', return_value=mock_items):
            with patch.object(sop, '_score_and_rank', return_value=mock_items):
                with patch.object(sop, '_find_positive', return_value=mock_items[1]):
                    with patch.object(sop, '_apply_tone_filter', side_effect=lambda x: x):
                        result = await sop.execute(payload_ref, founder_id)
        
        assert result.success is True
        assert len(result.output["items"]) <= MAX_BRIEFING_ITEMS
        assert result.output["item_count"] <= 5

    @pytest.mark.asyncio
    async def test_compose_actions_returns_first_action(self, sop):
        """Should return first (most urgent) action."""
        items = [
            {"headline": "Urgent", "do_this": "Do this first", "urgency": 10},
            {"headline": "Less urgent", "do_this": "Do this later", "urgency": 5},
        ]
        
        action = sop._compose_actions(items)
        assert action == "Do this first"

    @pytest.mark.asyncio
    async def test_compose_actions_empty_if_no_actions(self, sop):
        """Should return empty string if no actions."""
        items = [
            {"headline": "Info only", "urgency": 5},
        ]
        
        action = sop._compose_actions(items)
        assert action == ""


class TestWeeklyBriefingIntegration:
    """Integration tests with real database."""

    @pytest.fixture
    def sop(self):
        return WeeklyBriefingSOP()

    @pytest.mark.skip(reason="Requires full database setup")
    @pytest.mark.asyncio
    async def test_full_briefing_with_real_db(self, sop):
        """
        Full weekly briefing with real PostgreSQL.
        
        Skipped by default — run manually when database is ready.
        """
        from src.db.raw_events import insert_raw_event
        
        # Insert cron trigger event
        raw_event_id = await insert_raw_event(
            founder_id="founder_test",
            source="cron",
            event_name="ops.cron.weekly",
            topic="ops.cron.weekly",
            sop_name="SOP_WEEKLY_BRIEFING",
            payload={"cron_schedule": "weekly"},
        )
        
        # Execute SOP
        result = await sop.execute(f"raw_events:{raw_event_id}", "founder_test")
        
        # Verify briefing created
        assert result.success is True
        assert len(result.output["items"]) > 0
