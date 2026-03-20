"""Test suite for Event Dictionary (v1.0 — 2 agents)."""
import pytest
from src.config.event_dictionary import EventDictionary, UnknownEventError


class TestEventDictionary:
    """Test EventDictionary for Sarthi v1.0."""

    def setup_method(self):
        """Set up test fixtures."""
        self.d = EventDictionary()

    def test_razorpay_payment_success_maps_to_finance(self):
        """Razorpay PAYMENT_SUCCESS should route to FinanceAgent."""
        entry = self.d.resolve(source="razorpay", event_type="PAYMENT_SUCCESS")
        assert entry.agent_name == "FinanceAgent"
        assert "Bookkeeper" in entry.employees
        assert "CFO" in entry.employees

    def test_razorpay_subscription_cancelled_maps_to_finance(self):
        """Razorpay SUBSCRIPTION_CANCELLED should route to FinanceAgent."""
        entry = self.d.resolve(source="razorpay", event_type="SUBSCRIPTION_CANCELLED")
        assert entry.agent_name == "FinanceAgent"
        assert "CFO" in entry.employees
        assert "BI Analyst" in entry.employees

    def test_telegram_nl_query_maps_to_bi(self):
        """Telegram NL_QUERY should route to BIAgent."""
        entry = self.d.resolve(source="telegram", event_type="NL_QUERY")
        assert entry.agent_name == "BIAgent"
        assert "BI Analyst" in entry.employees

    def test_cron_weekly_briefing_maps_to_chief_of_staff(self):
        """Cron WEEKLY_BRIEFING should route to ChiefOfStaffAgent."""
        entry = self.d.resolve(source="cron", event_type="WEEKLY_BRIEFING")
        assert entry.agent_name == "ChiefOfStaffAgent"
        assert "Chief of Staff" in entry.employees

    def test_cron_weekly_insights_maps_to_bi(self):
        """Cron WEEKLY_INSIGHTS should route to BIAgent."""
        entry = self.d.resolve(source="cron", event_type="WEEKLY_INSIGHTS")
        assert entry.agent_name == "BIAgent"

    def test_internal_finance_anomaly_maps_to_bi(self):
        """Internal FINANCE_ANOMALY should trigger BIAgent."""
        entry = self.d.resolve(source="internal", event_type="FINANCE_ANOMALY")
        assert entry.agent_name == "BIAgent"

    def test_unknown_event_raises(self):
        """Unknown events should raise UnknownEventError."""
        with pytest.raises(UnknownEventError):
            self.d.resolve(source="stripe", event_type="payment.captured")

    def test_unknown_source_raises(self):
        """Unknown sources should raise UnknownEventError."""
        with pytest.raises(UnknownEventError):
            self.d.resolve(source="unknown_source", event_type="UNKNOWN_EVENT")

    def test_no_duplicate_source_event_pairs(self):
        """No duplicate (source, event_type) pairs should exist."""
        entries = self.d.all_entries()
        keys = [(e.source, e.event_type) for e in entries]
        assert len(keys) == len(set(keys)), "Duplicate (source, event_type) pairs found"

    def test_all_razorpay_events(self):
        """All Razorpay events should be registered (5 events)."""
        razorpay_events = self.d.by_source("razorpay")
        assert len(razorpay_events) == 5, f"Expected 5 Razorpay events, got {len(razorpay_events)}"

    def test_all_telegram_events(self):
        """All Telegram events should be registered (3 events)."""
        telegram_events = self.d.by_source("telegram")
        assert len(telegram_events) == 3, f"Expected 3 Telegram events, got {len(telegram_events)}"

    def test_all_cron_events(self):
        """All Cron events should be registered (3 events)."""
        cron_events = self.d.by_source("cron")
        assert len(cron_events) == 3, f"Expected 3 Cron events, got {len(cron_events)}"

    def test_finance_agent_events(self):
        """FinanceAgent should handle 10 events."""
        finance_events = self.d.by_agent("FinanceAgent")
        assert len(finance_events) == 10, f"Expected 10 FinanceAgent events, got {len(finance_events)}"

    def test_bi_agent_events(self):
        """BIAgent should handle 4 events."""
        bi_events = self.d.by_agent("BIAgent")
        assert len(bi_events) == 4, f"Expected 4 BIAgent events, got {len(bi_events)}"

    def test_chief_of_staff_events(self):
        """ChiefOfStaffAgent should handle 2 events."""
        cos_events = self.d.by_agent("ChiefOfStaffAgent")
        assert len(cos_events) == 2, f"Expected 2 ChiefOfStaffAgent events, got {len(cos_events)}"

    def test_total_event_count(self):
        """Total events should be 16 for v1.0."""
        total = self.d.count()
        assert total == 16, f"Expected 16 events for v1.0, got {total}"
