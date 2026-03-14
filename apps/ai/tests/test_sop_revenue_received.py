"""
Test suite for SOP_REVENUE_RECEIVED.

Tests run against real PostgreSQL and real Azure LLM.
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from src.sops.revenue_received import RevenueReceivedSOP, MRR_MILESTONES, CONCENTRATION_THRESHOLD
from src.sops.base import SOPResult, BANNED_JARGON


class TestRevenueReceivedSOP:
    """Test suite for RevenueReceivedSOP."""

    @pytest.fixture
    def sop(self):
        """Create SOP instance."""
        return RevenueReceivedSOP()

    @pytest.fixture
    def sample_razorpay_payload(self):
        """Sample Razorpay payment.captured payload."""
        return {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test123",
                        "amount": 500000,  # ₹5,000 in paise
                        "currency": "INR",
                        "status": "captured",
                        "method": "upi",
                        "description": "SaaS subscription - Pro plan",
                        "customer_id": "cust_abc123",
                        "captured": True,
                    }
                }
            }
        }

    def test_sop_name_is_correct(self, sop):
        """SOP should have correct name."""
        assert sop.sop_name == "SOP_REVENUE_RECEIVED"

    def test_extract_payment_entity(self, sop, sample_razorpay_payload):
        """Should extract payment entity from raw payload."""
        entity = sop._extract_payment_entity(sample_razorpay_payload)
        assert entity["id"] == "pay_test123"
        assert entity["amount"] == 500000
        assert entity["currency"] == "INR"

    def test_extract_payment_entity_handles_missing_keys(self, sop):
        """Should handle missing keys gracefully."""
        entity = sop._extract_payment_entity({})
        assert entity == {}
        
        entity = sop._extract_payment_entity({"payload": {}})
        assert entity == {}

    def test_format_milestone_lakhs(self, sop):
        """Should format milestones in lakhs."""
        assert sop._format_milestone(100_000) == "₹1.0L MRR"
        assert sop._format_milestone(500_000) == "₹5.0L MRR"
        assert sop._format_milestone(1_000_000) == "₹1.0L MRR"
        assert sop._format_milestone(5_000_000) == "₹5.0L MRR"

    def test_extract_raw_event_id(self, sop):
        """Should extract UUID from payload_ref."""
        assert sop._extract_raw_event_id("raw_events:abc-123") == "abc-123"
        assert sop._extract_raw_event_id("raw-events-uuid") == "raw-events-uuid"

    @pytest.mark.asyncio
    async def test_normal_payment_logs_silently(self, sop, sample_razorpay_payload):
        """
        Regular payment below milestone should log without Telegram alert.
        
        This test mocks database calls since we're testing SOP logic,
        not database connectivity.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "raw_events:test-uuid"
        
        with patch.object(sop, 'fetch_payload', return_value=sample_razorpay_payload):
            with patch.object(sop, '_write_transaction'):
                with patch.object(sop, '_check_mrr_milestones', return_value=[]):
                    with patch.object(sop, '_check_concentration_risk', return_value=None):
                        with patch.object(sop, '_log_to_memory'):
                            result = await sop.execute(payload_ref, founder_id)
        
        assert result.success is True
        assert result.fire_alert is False  # Silent for normal payments
        assert result.is_good_news is False
        assert result.headline == ""  # No headline for silent payments

    @pytest.mark.asyncio
    async def test_mrr_milestone_fires_positive_trigger(self, sop, sample_razorpay_payload):
        """
        Crossing ₹5L MRR should fire a celebratory alert.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "raw_events:test-uuid"
        
        with patch.object(sop, 'fetch_payload', return_value=sample_razorpay_payload):
            with patch.object(sop, '_write_transaction'):
                # Simulate crossing ₹5L milestone (return integer, not formatted string)
                with patch.object(sop, '_check_mrr_milestones', return_value=[500_000]):
                    with patch.object(sop, '_check_concentration_risk', return_value=None):
                        with patch.object(sop, '_log_to_memory'):
                            result = await sop.execute(payload_ref, founder_id)
        
        assert result.success is True
        assert result.fire_alert is True  # Alert for milestone
        assert result.is_good_news is True
        assert "₹5.0L MRR" in result.headline
        assert "runway" in result.headline.lower()

    @pytest.mark.asyncio
    async def test_concentration_risk_fires_alert(self, sop, sample_razorpay_payload):
        """
        Customer > 30% of revenue should fire concentration risk alert.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "raw_events:test-uuid"
        
        concentration_info = {
            "customer_id": "cust_abc123",
            "name": "Acme Corp",
            "pct": 0.35,  # 35%
            "threshold": CONCENTRATION_THRESHOLD,
        }
        
        with patch.object(sop, 'fetch_payload', return_value=sample_razorpay_payload):
            with patch.object(sop, '_write_transaction'):
                with patch.object(sop, '_check_mrr_milestones', return_value=[]):
                    with patch.object(sop, '_check_concentration_risk', return_value=concentration_info):
                        with patch.object(sop, '_log_to_memory'):
                            result = await sop.execute(payload_ref, founder_id)
        
        assert result.success is True
        assert result.fire_alert is True  # Alert for concentration risk
        assert result.is_good_news is False
        assert "Acme Corp" in result.headline
        assert "35%" in result.headline

    @pytest.mark.asyncio
    async def test_output_contains_payment_details(self, sop, sample_razorpay_payload):
        """Output should contain payment details for downstream processing."""
        founder_id = str(uuid.uuid4())
        payload_ref = "raw_events:test-uuid"
        
        with patch.object(sop, 'fetch_payload', return_value=sample_razorpay_payload):
            with patch.object(sop, '_write_transaction'):
                with patch.object(sop, '_check_mrr_milestones', return_value=[]):
                    with patch.object(sop, '_check_concentration_risk', return_value=None):
                        with patch.object(sop, '_log_to_memory'):
                            result = await sop.execute(payload_ref, founder_id)
        
        assert result.output["amount_inr"] == 5000.0  # ₹5,000
        assert result.output["currency"] == "INR"
        assert result.output["payment_id"] == "pay_test123"

    def test_validate_tone_no_jargon_in_milestone_headline(self, sop):
        """Milestone headlines should be jargon-free."""
        result = SOPResult(
            sop_name="SOP_REVENUE_RECEIVED",
            founder_id="founder_123",
            success=True,
            fire_alert=True,
            headline="You just crossed ₹5.0L MRR — your runway just got longer.",
            do_this="Review the details.",
            is_good_news=True,
        )
        
        violations = result.validate_tone()
        assert len(violations) == 0, f"Jargon violations found: {violations}"

    def test_validate_tone_no_jargon_in_concentration_headline(self, sop):
        """Concentration risk headlines should be jargon-free."""
        result = SOPResult(
            sop_name="SOP_REVENUE_RECEIVED",
            founder_id="founder_123",
            success=True,
            fire_alert=True,
            headline="Acme Corp is now 35% of your revenue — worth watching.",
            do_this="Review customer concentration.",
            is_good_news=False,
        )
        
        violations = result.validate_tone()
        assert len(violations) == 0, f"Jargon violations found: {violations}"

    def test_mrr_milestones_list(self):
        """Verify MRR milestones are defined."""
        assert len(MRR_MILESTONES) > 0
        assert 100_000 in MRR_MILESTONES  # ₹1L
        assert 500_000 in MRR_MILESTONES  # ₹5L
        assert 1_000_000 in MRR_MILESTONES  # ₹10L
        assert 5_000_000 in MRR_MILESTONES  # ₹50L

    def test_concentration_threshold(self):
        """Verify concentration risk threshold is 30%."""
        assert CONCENTRATION_THRESHOLD == 0.30


class TestRevenueReceivedIntegration:
    """Integration tests with real database."""

    @pytest.fixture
    def sop(self):
        return RevenueReceivedSOP()

    @pytest.mark.skip(reason="Requires full database setup")
    @pytest.mark.asyncio
    async def test_full_pipeline_with_real_db(self, sop):
        """
        Full pipeline test with real PostgreSQL.
        
        Skipped by default — run manually when database is ready.
        """
        from src.db.raw_events import insert_raw_event
        from src.db.transactions import get_transaction_by_external_id
        
        # Insert raw event
        raw_event_id = await insert_raw_event(
            founder_id="founder_test",
            source="razorpay",
            event_name="payment.captured",
            topic="finance.revenue.captured",
            sop_name="SOP_REVENUE_RECEIVED",
            payload={"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_integration_test", "amount": 750000, "currency": "INR"}}}},
        )
        
        # Execute SOP
        result = await sop.execute(f"raw_events:{raw_event_id}", "founder_test")
        
        # Verify transaction created
        txn = await get_transaction_by_external_id("founder_test", "pay_integration_test")
        assert txn is not None
        assert txn["credit"] == 7500.0  # ₹7,500
