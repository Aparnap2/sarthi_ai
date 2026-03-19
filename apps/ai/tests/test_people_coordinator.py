"""Tests for People Coordinator Agent."""
import pytest
from src.agents.people_coordinator import PeopleCoordinatorAgent
from src.agents.base import BANNED_JARGON


class TestPeopleCoordinator:
    """Test suite for PeopleCoordinatorAgent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = PeopleCoordinatorAgent()

    def test_eng_checklist_has_github(self):
        """Test that eng role gets github in checklist."""
        state = {"tenant_id": "test"}
        event = {
            "event_type": "EMPLOYEE_CREATED",
            "name": "Priya",
            "role_function": "eng",
        }
        result = self.agent.run(state, event)
        assert "github" in result["output_json"]["checklist"]

    def test_sales_checklist_no_github(self):
        """Test that sales role does not get github."""
        state = {"tenant_id": "test"}
        event = {
            "event_type": "EMPLOYEE_CREATED",
            "name": "Rahul",
            "role_function": "sales",
        }
        result = self.agent.run(state, event)
        assert "github" not in result["output_json"]["checklist"]

    def test_incomplete_item_nag_24h(self):
        """Test that incomplete items trigger nag."""
        state = {
            "tenant_id": "test",
            "employee_name": "Priya",
            "checklist": {"slack": True, "github": False, "notion": False},
        }
        event = {"event_type": "TIME_TICK_D1"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "github" in result["headline"]

    def test_complete_checklist_no_nag(self):
        """Test that complete checklist does not trigger nag."""
        state = {
            "tenant_id": "test",
            "checklist": {"slack": True, "notion": True, "github": True},
        }
        event = {"event_type": "TIME_TICK_D1"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is False

    def test_offboarding_generates_revoke_list(self):
        """Test that offboarding generates revocation list."""
        state = {"tenant_id": "test"}
        event = {
            "event_type": "EMPLOYEE_TERMINATED",
            "name": "Rahul",
            "role_function": "eng",
        }
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "github" in result["output_json"]["revoke_list"]

    def test_new_hire_fires_telegram(self):
        """Test that new hire triggers telegram message."""
        state = {"tenant_id": "test"}
        event = {
            "event_type": "EMPLOYEE_CREATED",
            "name": "Priya",
            "role_function": "eng",
        }
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "Priya" in result["headline"]

    def test_no_jargon_in_output(self):
        """Test that output contains no banned jargon."""
        state = {
            "tenant_id": "test",
            "checklist": {"slack": True, "github": False},
        }
        event = {"event_type": "TIME_TICK_D1"}
        result = self.agent.run(state, event)
        for term in BANNED_JARGON:
            assert term.lower() not in result.get("headline", "").lower()
