"""
Test suite for SOP_BANK_STATEMENT_INGEST.

Tests run with mocked database calls (TDD pattern).
Integration tests require real PostgreSQL.
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from src.sops.bank_statement_ingest import BankStatementIngestSOP, RUNWAY_ALERT_THRESHOLD_DAYS
from src.sops.base import SOPResult, BANNED_JARGON


class TestBankStatementIngestSOP:
    """Test suite for BankStatementIngestSOP."""

    @pytest.fixture
    def sop(self):
        """Create SOP instance."""
        return BankStatementIngestSOP()

    @pytest.fixture
    def sample_hdfc_csv_payload(self):
        """Sample HDFC bank statement CSV payload."""
        return {
            "event": "pdf.bank_statement",
            "file_path": "/tmp/hdfc_march_2026.csv",
            "file_type": "csv",
            "bank_name": "HDFC",
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
            "transactions": [
                {"date": "2026-03-01", "description": "UPI payment from Acme Corp", "debit": 0, "credit": 50000, "balance": 500000},
                {"date": "2026-03-05", "description": "AWS India Pvt Ltd", "debit": 15000, "credit": 0, "balance": 485000},
                {"date": "2026-03-10", "description": "Salary transfer", "debit": 0, "credit": 100000, "balance": 585000},
            ]
        }

    def test_sop_name_is_correct(self, sop):
        """SOP should have correct name."""
        assert sop.sop_name == "SOP_BANK_STATEMENT_INGEST"

    def test_extract_transactions_from_csv(self, sop, sample_hdfc_csv_payload):
        """Should extract transactions from CSV payload."""
        transactions = sop._extract_transactions(sample_hdfc_csv_payload)
        assert len(transactions) == 3
        assert transactions[0]["credit"] == 50000
        assert transactions[1]["debit"] == 15000

    def test_categorize_transaction_revenue(self, sop):
        """Should categorize incoming payments as Revenue."""
        txn = {"description": "UPI payment from Customer XYZ", "debit": 0, "credit": 25000}
        category, confidence = sop._categorize_transaction(txn)
        assert category == "Revenue"
        assert confidence > 0.9

    def test_categorize_transaction_infrastructure(self, sop):
        """Should categorize AWS/Azure/GCP as Infrastructure."""
        txn = {"description": "AWS India Pvt Ltd", "debit": 15000, "credit": 0}
        category, confidence = sop._categorize_transaction(txn)
        assert category == "Infrastructure"
        assert confidence > 0.9

    def test_categorize_transaction_payroll(self, sop):
        """Should categorize salary as Payroll."""
        txn = {"description": "Salary transfer", "debit": 0, "credit": 100000}
        category, confidence = sop._categorize_transaction(txn)
        assert category == "Payroll"  # Salary is categorized as Payroll
        assert confidence > 0.9

    def test_is_duplicate_detection(self, sop):
        """Should detect duplicate transactions."""
        txn = {"date": "2026-03-01", "amount": 50000, "description": "Test"}
        
        with patch('src.db.transactions.transaction_exists', return_value=True):
            assert sop._is_duplicate("founder_123", txn) is True
        
        with patch('src.db.transactions.transaction_exists', return_value=False):
            assert sop._is_duplicate("founder_123", txn) is False

    @pytest.mark.asyncio
    async def test_normal_statement_ingests_silently(self, sop, sample_hdfc_csv_payload):
        """
        Normal bank statement should ingest without firing alert.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "raw_events:test-uuid"
        
        with patch.object(sop, 'fetch_payload', return_value=sample_hdfc_csv_payload):
            with patch.object(sop, '_extract_transactions', return_value=sample_hdfc_csv_payload["transactions"]):
                with patch.object(sop, '_is_duplicate', return_value=False):
                    with patch.object(sop, '_categorize_transaction', return_value=("Revenue", 0.95)):
                        with patch.object(sop, '_write_transaction'):
                            with patch.object(sop, '_upsert_qdrant'):
                                with patch.object(sop, '_update_cfo_state', return_value=180):  # 180 days runway
                                    with patch.object(sop, '_log_to_memory'):
                                        result = await sop.execute(payload_ref, founder_id)
        
        assert result.success is True
        assert result.fire_alert is False  # Silent for normal statements
        assert result.output["transactions_ingested"] == 3
        assert result.output["runway_days"] == 180

    @pytest.mark.asyncio
    async def test_runway_below_90_days_fires_alert(self, sop, sample_hdfc_csv_payload):
        """
        If runway < 90 days, should fire alert.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "raw_events:test-uuid"
        
        with patch.object(sop, 'fetch_payload', return_value=sample_hdfc_csv_payload):
            with patch.object(sop, '_extract_transactions', return_value=sample_hdfc_csv_payload["transactions"]):
                with patch.object(sop, '_is_duplicate', return_value=False):
                    with patch.object(sop, '_categorize_transaction', return_value=("Revenue", 0.95)):
                        with patch.object(sop, '_write_transaction'):
                            with patch.object(sop, '_upsert_qdrant'):
                                with patch.object(sop, '_update_cfo_state', return_value=60):  # 60 days runway (< 90)
                                    with patch.object(sop, '_log_to_memory'):
                                        result = await sop.execute(payload_ref, founder_id)
        
        assert result.success is True
        assert result.fire_alert is True  # Alert for low runway
        assert "60 days" in result.headline or "2 months" in result.headline

    @pytest.mark.asyncio
    async def test_duplicate_transactions_skipped(self, sop, sample_hdfc_csv_payload):
        """
        Duplicate transactions should be skipped.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "raw_events:test-uuid"
        
        with patch.object(sop, 'fetch_payload', return_value=sample_hdfc_csv_payload):
            with patch.object(sop, '_extract_transactions', return_value=sample_hdfc_csv_payload["transactions"]):
                with patch.object(sop, '_is_duplicate', return_value=True):  # All duplicates
                    with patch.object(sop, '_write_transaction') as mock_write:
                        with patch.object(sop, '_upsert_qdrant'):
                            with patch.object(sop, '_update_cfo_state', return_value=180):
                                with patch.object(sop, '_log_to_memory'):
                                    result = await sop.execute(payload_ref, founder_id)
        
        assert mock_write.call_count == 0  # No writes for duplicates
        assert result.output["transactions_skipped"] == 3

    @pytest.mark.asyncio
    async def test_low_confidence_flagged_for_review(self, sop, sample_hdfc_csv_payload):
        """
        Transactions with confidence < 0.7 should be flagged.
        """
        founder_id = str(uuid.uuid4())
        payload_ref = "raw_events:test-uuid"
        
        def mock_categorize(txn):
            return ("Uncategorized", 0.5)  # Low confidence
        
        with patch.object(sop, 'fetch_payload', return_value=sample_hdfc_csv_payload):
            with patch.object(sop, '_extract_transactions', return_value=sample_hdfc_csv_payload["transactions"]):
                with patch.object(sop, '_is_duplicate', return_value=False):
                    with patch.object(sop, '_categorize_transaction', side_effect=mock_categorize):
                        with patch.object(sop, '_write_transaction'):
                            with patch.object(sop, '_upsert_qdrant'):
                                with patch.object(sop, '_update_cfo_state', return_value=180):
                                    with patch.object(sop, '_log_to_memory'):
                                        result = await sop.execute(payload_ref, founder_id)
        
        assert result.output["transactions_flagged"] == 3

    def test_validate_tone_no_jargon_in_alert_headline(self, sop):
        """Alert headlines should be jargon-free."""
        result = SOPResult(
            sop_name="SOP_BANK_STATEMENT_INGEST",
            founder_id="founder_123",
            success=True,
            fire_alert=True,
            headline="Runway dropped to 60 days — less than 2 months. Burn jumped.",
            do_this="Review the breakdown.",
            is_good_news=False,
        )
        
        violations = result.validate_tone()
        assert len(violations) == 0, f"Jargon violations found: {violations}"

    def test_runway_threshold_constant(self):
        """Verify runway alert threshold is 90 days."""
        assert RUNWAY_ALERT_THRESHOLD_DAYS == 90


class TestBankStatementIngestIntegration:
    """Integration tests with real database."""

    @pytest.fixture
    def sop(self):
        return BankStatementIngestSOP()

    @pytest.mark.skip(reason="Requires full database setup")
    @pytest.mark.asyncio
    async def test_full_pipeline_with_real_db(self, sop):
        """
        Full pipeline test with real PostgreSQL and Qdrant.
        
        Skipped by default — run manually when database is ready.
        """
        from src.db.raw_events import insert_raw_event
        from src.db.transactions import count_transactions
        
        # Insert raw event with HDFC CSV payload
        raw_event_id = await insert_raw_event(
            founder_id="founder_test",
            source="telegram",
            event_name="pdf.bank_statement",
            topic="ingestion.pdf.bank_statement",
            sop_name="SOP_BANK_STATEMENT_INGEST",
            payload={"file_path": "/tmp/test_hdfc.csv", "file_type": "csv", "bank_name": "HDFC"},
        )
        
        # Execute SOP
        result = await sop.execute(f"raw_events:{raw_event_id}", "founder_test")
        
        # Verify transactions created
        assert result.success is True
        assert result.output["transactions_ingested"] > 0
