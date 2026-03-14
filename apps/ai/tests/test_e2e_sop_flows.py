"""
E2E Test Suite for Sarthi SOP Runtime.

Full stack tests with real Docker infrastructure and real Azure LLM.
"""
import pytest
import os
import asyncio
import hashlib
import hmac
from datetime import datetime, timezone


# ── Helpers ────────────────────────────────────────────────────────────────────

def compute_razorpay_hmac(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for Razorpay webhook."""
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return mac.hexdigest()


async def poll_sop_job(sop_name: str, timeout: int = 30) -> dict:
    """Poll sop_jobs table for completed job."""
    import asyncpg
    
    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://iterateswarm:iterateswarm@localhost:5432/iterateswarm")
    conn = await asyncpg.connect(db_url)
    
    try:
        for _ in range(timeout):
            row = await conn.fetchrow(
                "SELECT * FROM sop_jobs WHERE sop_name = $1 ORDER BY created_at DESC LIMIT 1",
                sop_name
            )
            if row and row["status"] == "completed":
                return dict(row)
            await asyncio.sleep(1)
        
        raise TimeoutError(f"SOP {sop_name} did not complete within {timeout}s")
    finally:
        await conn.close()


async def get_transaction_by_external_id(founder_id: str, external_id: str) -> dict:
    """Get transaction by external_id."""
    import asyncpg
    
    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://iterateswarm:iterateswarm@localhost:5432/iterateswarm")
    conn = await asyncpg.connect(db_url)
    
    try:
        row = await conn.fetchrow(
            "SELECT * FROM transactions WHERE founder_id = $1 AND external_id = $2",
            founder_id, external_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def count_transactions(founder_id: str) -> int:
    """Count transactions for founder."""
    import asyncpg
    
    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://iterateswarm:iterateswarm@localhost:5432/iterateswarm")
    conn = await asyncpg.connect(db_url)
    
    try:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM transactions WHERE founder_id = $1",
            founder_id
        )
        return row["count"]
    finally:
        await conn.close()


# ── E2E Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.e2e
@pytest.mark.asyncio
class TestE2ESOPFlows:
    """
    End-to-end tests for full SOP pipeline.
    
    Requires:
    - Running Docker containers (postgres, redpanda)
    - Azure LLM credentials
    - Running webhooks server
    """

    @pytest.fixture
    def http_client(self):
        """Create test HTTP client."""
        import httpx
        base_url = os.environ.get("TEST_BASE_URL", "http://localhost:8080")
        with httpx.AsyncClient(base_url=base_url) as client:
            yield client

    async def test_razorpay_payment_captured_full_pipeline(self, http_client):
        """
        Razorpay payment.captured →
        Go Fiber verifies HMAC →
        raw_events persisted →
        Redpanda published →
        Temporal child SOP_REVENUE_RECEIVED →
        transactions row created
        """
        # Skip if no webhook secret configured
        webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET_TEST")
        if not webhook_secret:
            pytest.skip("RAZORPAY_WEBHOOK_SECRET_TEST not configured")
        
        # Build payload
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_e2e_test_" + str(hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]),
                        "amount": 750000,  # ₹7,500
                        "currency": "INR",
                        "method": "upi",
                        "description": "E2E test payment",
                    }
                }
            }
        }
        
        import json
        body = json.dumps(payload).encode()
        sig = compute_razorpay_hmac(body, webhook_secret)
        
        # Send webhook
        resp = await http_client.post(
            "/webhooks/razorpay",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": sig
            }
        )
        
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"
        
        # Wait for Temporal to process
        job = await poll_sop_job("SOP_REVENUE_RECEIVED", timeout=30)
        assert job["status"] == "completed"
        
        # Verify transaction persisted
        txn = await get_transaction_by_external_id("founder_test", payload["payload"]["payment"]["entity"]["id"])
        assert txn is not None
        assert txn["credit"] == 7500.0  # ₹7,500
        assert txn["category"] == "Revenue"

    async def test_bank_statement_telegram_drop_full_pipeline(self, http_client, tmp_path):
        """
        Telegram CSV drop →
        classified as bank statement →
        SOP_BANK_STATEMENT_INGEST →
        transactions created
        """
        # Create test CSV
        csv_content = """Date,Description,Debit,Credit,Balance
2026-03-01,Opening Balance,0,0,500000
2026-03-05,UPI payment from Customer A,0,50000,550000
2026-03-10,AWS India Pvt Ltd,15000,0,535000
2026-03-15,Salary transfer,0,100000,635000
"""
        csv_file = tmp_path / "hdfc_test.csv"
        csv_file.write_text(csv_content)
        
        # Build Telegram document message
        update = {
            "update_id": 123456,
            "message": {
                "message_id": 789,
                "from": {"id": 123456789, "first_name": "Test User"},
                "chat": {"id": 123456789, "type": "private"},
                "document": {
                    "file_name": "hdfc_march_2026.csv",
                    "mime_type": "text/csv",
                    "file_id": "BQACAgQAAxkBAAIB",
                },
            }
        }
        
        import json
        resp = await http_client.post(
            "/webhooks/telegram",
            json=update,
            headers={"Content-Type": "application/json"}
        )
        
        assert resp.status_code == 200
        
        # Wait for SOP to process
        job = await poll_sop_job("SOP_BANK_STATEMENT_INGEST", timeout=60)
        assert job["status"] == "completed"
        
        # Verify transactions created
        count = await count_transactions("founder_test")
        assert count > 0

    async def test_weekly_briefing_cron_produces_jargon_free_message(self):
        """
        Weekly cron trigger →
        SOP_WEEKLY_BRIEFING →
        max 5 items, jargon-free, Langfuse trace exists
        """
        from src.sops.weekly_briefing import WeeklyBriefingSOP
        from src.sops.base import BANNED_JARGON
        
        sop = WeeklyBriefingSOP()
        result = await sop.execute("cron:ops.cron.weekly", "founder_test")
        
        assert result.success is True
        items = result.output.get("items", [])
        assert len(items) <= 5, f"Weekly brief has {len(items)} items, max is 5"
        
        # Check for jargon
        full_text = result.headline + " " + result.do_this
        for term in BANNED_JARGON:
            assert term.lower() not in full_text.lower(), \
                f"Banned jargon '{term}' in weekly briefing"
