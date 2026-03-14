"""Test suite for Event Dictionary."""
import pytest
from src.config.event_dictionary import EventDictionary, UnknownEventError


class TestEventDictionary:

    def setup_method(self):
        self.d = EventDictionary()

    def test_razorpay_payment_captured(self):
        e = self.d.resolve("razorpay", "payment.captured")
        assert e.topic == "finance.revenue.captured"
        assert e.sop   == "SOP_REVENUE_RECEIVED"
        assert "Bookkeeper" in e.employees

    def test_razorpay_subscription_cancelled(self):
        e = self.d.resolve("razorpay", "subscription.cancelled")
        assert e.sop   == "SOP_CHURN_DETECTED"
        assert "CFO" in e.employees
        assert "BI Analyst" in e.employees

    def test_zoho_invoice_created(self):
        e = self.d.resolve("zoho_books", "invoice.created")
        assert e.topic == "finance.ap.invoice_created"
        assert e.sop   == "SOP_VENDOR_INVOICE_RECEIVED"

    def test_telegram_pdf_bank_statement(self):
        e = self.d.resolve("telegram", "pdf.bank_statement")
        assert e.sop   == "SOP_BANK_STATEMENT_INGEST"

    def test_cron_weekly_briefing(self):
        e = self.d.resolve("cron", "ops.cron.weekly")
        assert e.sop   == "SOP_WEEKLY_BRIEFING"

    def test_esign_declined_maps_to_hitl(self):
        e = self.d.resolve("esign", "document.declined")
        assert e.sop   == "SOP_ESIGN_DECLINED"
        assert "EA" in e.employees

    def test_unknown_event_raises(self):
        with pytest.raises(UnknownEventError):
            self.d.resolve("razorpay", "completely.fake.event")

    def test_unknown_source_raises(self):
        with pytest.raises(UnknownEventError):
            self.d.resolve("stripe", "payment.captured")  # stripe not yet supported

    def test_no_duplicate_source_event_pairs(self):
        entries = self.d.all_entries()
        keys = [(e.source, e.event_name) for e in entries]
        assert len(keys) == len(set(keys)), "Duplicate (source, event_name) pairs found"

    def test_all_48_events_registered(self):
        count = self.d.count()
        assert count >= 48, f"Expected at least 48 events, got {count}"

    def test_all_razorpay_events(self):
        """Verify all 11 Razorpay events are registered."""
        razorpay_events = [e for e in self.d.all_entries() if e.source == "razorpay"]
        assert len(razorpay_events) == 11

    def test_all_zoho_events(self):
        """Verify all 7 Zoho Books events are registered."""
        zoho_events = [e for e in self.d.all_entries() if e.source == "zoho_books"]
        assert len(zoho_events) == 7

    def test_all_telegram_events(self):
        """Verify all 8 Telegram events are registered."""
        telegram_events = [e for e in self.d.all_entries() if e.source == "telegram"]
        assert len(telegram_events) == 8

    def test_all_cron_events(self):
        """Verify all 9 Cron events are registered."""
        cron_events = [e for e in self.d.all_entries() if e.source == "cron"]
        assert len(cron_events) == 9
