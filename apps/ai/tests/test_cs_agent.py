"""Tests for CS Agent."""
import pytest
from unittest.mock import patch
from src.agents.cs_agent import CSAgent
from src.agents.base import BANNED_JARGON


class TestCSAgent:
    """Test suite for CSAgent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = CSAgent()

    def test_signup_initializes_state(self):
        """Test that signup triggers welcome message."""
        state = {"tenant_id": "test"}
        event = {
            "event_type": "USER_SIGNED_UP",
            "customer_name": "Arjun",
            "customer_id": "cus_001",
        }
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "Arjun" in result["headline"]

    def test_d1_message_queued(self):
        """Test that D1 tick triggers message."""
        state = {
            "tenant_id": "test",
            "days_since_last_login": 1,
            "onboarding_stage": "WELCOME",
        }
        event = {"event_type": "TIME_TICK_D1"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True

    def test_d7_no_login_risk_high(self):
        """Test that D7 with no login triggers high risk alert."""
        state = {
            "tenant_id": "test",
            "days_since_last_login": 10,
            "onboarding_stage": "WELCOME",
            "customer_name": "Arjun",
        }
        event = {"event_type": "TIME_TICK_D7"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert result["urgency"] == "high"

    def test_active_user_risk_low(self):
        """Test that active user does not trigger alert."""
        state = {
            "tenant_id": "test",
            "days_since_last_login": 0,
            "onboarding_stage": "DONE",
        }
        event = {"event_type": "USER_LOGGED_IN"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is False

    def test_support_ticket_faq_draft(self):
        """Test that single ticket generates draft reply."""
        with patch.object(self.agent, '_draft_reply', return_value="Here's how to reset your password..."):
            state = {"tenant_id": "test", "tickets_last_48h": 1}
            event = {
                "event_type": "SUPPORT_TICKET_CREATED",
                "body": "How do I reset password?",
            }
            result = self.agent.run(state, event)
            assert result["fire_telegram"] is False
            assert "ticket_draft" in result["output_json"]

    def test_support_ticket_escalation(self):
        """Test that multiple tickets trigger escalation."""
        state = {
            "tenant_id": "test",
            "tickets_last_48h": 3,
            "customer_name": "Arjun",
        }
        event = {"event_type": "SUPPORT_TICKET_CREATED"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "3 tickets" in result["headline"]

    def test_no_jargon_in_output(self):
        """Test that output contains no banned jargon."""
        state = {"tenant_id": "test", "days_since_last_login": 8}
        event = {"event_type": "TIME_TICK_D7"}
        result = self.agent.run(state, event)
        for term in BANNED_JARGON:
            assert term.lower() not in result.get("headline", "").lower()
