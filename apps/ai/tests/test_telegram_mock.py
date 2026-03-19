"""
Tests Telegram integration against tg-mock mock server.
No real bot token. No real messages sent.

Run: uv run pytest tests/test_telegram_mock.py -v -s
Requires: sarthi-tg-mock container running on :8081
"""
import os
import json
import pytest
import requests

MOCKOON_BASE = os.getenv("TELEGRAM_API_BASE", "http://localhost:8081")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "987654321:ZYX-cba")
TEST_CHAT_ID = os.getenv("TELEGRAM_TEST_CHAT_ID", "111222333")
API_BASE = f"{MOCKOON_BASE}/bot{BOT_TOKEN}"


class TestTelegramMock:
    """Test Telegram API calls against tg-mock."""

    def test_tg_mock_is_running(self):
        """tg-mock should respond to getMe."""
        resp = requests.get(f"{API_BASE}/getMe", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        # Note: tg-mock faker generates user-like responses for getMe
        # The important thing is that the API responds correctly
        assert "result" in data
        assert "id" in data["result"]

    def test_send_plain_message(self):
        """sendMessage returns ok=true with message_id."""
        resp = requests.post(f"{API_BASE}/sendMessage", json={
            "chat_id": TEST_CHAT_ID,
            "text": "Sarthi test: AWS bill 2.3× usual.",
            "parse_mode": "Markdown",
        }, timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "message_id" in data["result"]
        assert data["result"]["text"] == "Sarthi test: AWS bill 2.3× usual."
        print(f"\n  ✅ message_id: {data['result']['message_id']}")

    def test_send_message_with_inline_keyboard(self):
        """Finance Monitor alert with action buttons."""
        resp = requests.post(f"{API_BASE}/sendMessage", json={
            "chat_id": TEST_CHAT_ID,
            "text": "AWS bill ₹42,000 — 2.3× usual. First spike.",
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "Investigate", "callback_data": "investigate:ao-001"},
                    {"text": "Expected", "callback_data": "mark_ok:ao-001"},
                ]]
            }
        }, timeout=5)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_send_weekly_briefing_format(self):
        """Chief of Staff briefing — multi-line, ≤5 items."""
        briefing = (
            "📋 *Monday Brief*\n\n"
            "🔴 AWS bill 2.3× usual — investigate today\\.\n"
            "🟡 Deal with Acme idle 9 days — send nudge\\.\n"
            "🟢 MRR crossed ₹1L — Priya pushed you over\\."
        )
        resp = requests.post(f"{API_BASE}/sendMessage", json={
            "chat_id": TEST_CHAT_ID,
            "text": briefing,
            "parse_mode": "MarkdownV2",
        }, timeout=5)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_answer_callback_query(self):
        """Founder taps [Investigate] — answerCallbackQuery must succeed."""
        resp = requests.post(f"{API_BASE}/answerCallbackQuery", json={
            "callback_query_id": "cq-test-12345",
            "text": "Got it. Investigating now.",
            "show_alert": False,
        }, timeout=5)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.skip(reason="tg-mock scenario matching requires manual scenario registration per test run")
    def test_rate_limit_simulation(self):
        """Simulate 429 by using chat_id=999 (configured in tg-mock.yaml)."""
        resp = requests.post(f"{API_BASE}/sendMessage", json={
            "chat_id": 999,
            "text": "test",
        }, timeout=5)
        assert resp.status_code == 429
        data = resp.json()
        assert data["ok"] is False
        assert data["error_code"] == 429
        assert "Too Many Requests" in data["description"]

    @pytest.mark.skip(reason="tg-mock scenario matching requires manual scenario registration per test run")
    def test_chat_not_found_error(self):
        """Simulate 400 chat not found by using chat_id=888."""
        resp = requests.post(f"{API_BASE}/sendMessage", json={
            "chat_id": 888,
            "text": "test",
        }, timeout=5)
        assert resp.status_code == 400
        data = resp.json()
        assert data["ok"] is False
        assert data["error_code"] == 400
        assert "chat not found" in data["description"]

    @pytest.mark.skip(reason="tg-mock faker generates different IDs per call despite seed")
    def test_deterministic_faker(self):
        """With faker_seed=12345, responses should be reproducible."""
        # Call getMe twice — should return same bot info
        resp1 = requests.get(f"{API_BASE}/getMe", timeout=5)
        resp2 = requests.get(f"{API_BASE}/getMe", timeout=5)
        
        assert resp1.json()["result"]["id"] == resp2.json()["result"]["id"]
        assert resp1.json()["result"]["username"] == resp2.json()["result"]["username"]
