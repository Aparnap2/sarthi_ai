"""
Tests for People Desk Agent — Sarthi v4.2 Phase 3.

Tests cover:
- Agent initialization
- Both capabilities (HR Coordinator, Internal Recruiter)
- Pydantic validation (jargon detection, single action)
- LangGraph workflow completion
- Real Azure LLM integration

Run with: pytest apps/ai/tests/test_people_desk.py -v
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from src.schemas.desk_results import PeopleOpsFinding, HitlRisk
from src.agents.people_desk import PeopleDeskAgent, PeopleDeskState, get_people_desk_agent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with realistic responses."""
    client = MagicMock()
    
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(
            content='{"employee_name": "John Doe", "event_type": "onboarding", "context": "New employee starting next Monday in Engineering team.", "do_this": "Send welcome email with first day instructions", "hitl_risk": "low"}'
        ))]
    )
    
    return client


@pytest.fixture
def people_agent(mock_llm_client):
    """Create PeopleDeskAgent with mocked dependencies."""
    with patch('src.agents.people_desk.get_llm_client', return_value=mock_llm_client):
        with patch('src.agents.people_desk.get_chat_model', return_value='gpt-4'):
            agent = PeopleDeskAgent()
            mock_llm_client.reset_mock(return_value=False, side_effect=False)
            return agent


# =============================================================================
# Test Pydantic Schema Validation
# =============================================================================

class TestPeopleOpsFindingValidation:
    """Test PeopleOpsFinding Pydantic validation."""

    def test_valid_finding_creation(self):
        """Test creating a valid PeopleOpsFinding."""
        finding = PeopleOpsFinding(
            employee_name="John Doe",
            event_type="onboarding",
            context="New employee starting next Monday in Engineering team.",
            do_this="Send welcome email with first day instructions",
            hitl_risk=HitlRisk.LOW
        )
        
        assert finding.employee_name == "John Doe"
        assert finding.event_type == "onboarding"
        assert finding.hitl_risk == HitlRisk.LOW

    def test_jargon_detection_pip(self):
        """Test that PIP jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PeopleOpsFinding(
                employee_name="Jane Smith",
                event_type="appraisal",
                context="Employee needs performance improvement",
                do_this="Start PIP process",
                hitl_risk=HitlRisk.HIGH
            )
        
        assert "jargon" in str(exc_info.value).lower()
        assert "PIP" in str(exc_info.value)

    def test_jargon_detection_attrition(self):
        """Test that attrition jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PeopleOpsFinding(
                employee_name="Team",
                event_type="offboarding",
                context="High attrition rate in department",
                do_this="Review retention strategies",
                hitl_risk=HitlRisk.MEDIUM
            )
        
        assert "jargon" in str(exc_info.value).lower()

    def test_jargon_detection_headcount(self):
        """Test that headcount jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PeopleOpsFinding(
                employee_name="HR Team",
                event_type="onboarding",
                context="New headcount approved",
                do_this="Begin recruitment",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "jargon" in str(exc_info.value).lower()

    def test_single_action_validation(self):
        """Test that do_this with multiple actions is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PeopleOpsFinding(
                employee_name="John Doe",
                event_type="onboarding",
                context="New employee starting",
                do_this="Send welcome email and schedule orientation",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "ONE action" in str(exc_info.value)

    def test_valid_single_action(self):
        """Test that single action passes validation."""
        finding = PeopleOpsFinding(
            employee_name="John Doe",
            event_type="onboarding",
            context="New employee starting next Monday",
            do_this="Send welcome email",
            hitl_risk=HitlRisk.LOW
        )
        
        assert finding.do_this == "Send welcome email"


# =============================================================================
# Test PeopleDeskAgent Initialization
# =============================================================================

class TestPeopleDeskAgentInitialization:
    """Test PeopleDeskAgent initialization."""

    def test_agent_initializes_without_params(self, mock_llm_client):
        """Test PeopleDeskAgent initializes without parameters."""
        with patch('src.agents.people_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.people_desk.get_chat_model', return_value='gpt-4'):
                agent = PeopleDeskAgent()
                
                assert agent.client is not None
                assert agent.model == 'gpt-4'

    def test_get_people_desk_agent_singleton(self, mock_llm_client):
        """Test get_people_desk_agent returns singleton."""
        with patch('src.agents.people_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.people_desk.get_chat_model', return_value='gpt-4'):
                import src.agents.people_desk as pd
                pd._people_desk_agent = None
                
                agent1 = get_people_desk_agent()
                agent2 = get_people_desk_agent()
                
                assert agent1 is agent2


# =============================================================================
# Test PeopleDeskAgent Capabilities
# =============================================================================

class TestPeopleDeskAgentCapabilities:
    """Test PeopleDeskAgent capabilities."""

    def test_analyze_hr_coordinator_onboarding(self, people_agent, mock_llm_client):
        """Test HR Coordinator handles onboarding events."""
        state = PeopleDeskState(
            founder_id="test-founder-id",
            hr_events=[{
                "type": "onboarding",
                "start_date": "2024-04-01",
                "role": "Senior Engineer",
                "department": "Engineering"
            }],
            task_type="hr_coordinator",
            employee_name="John Doe",
            result=None
        )
        
        result_state = people_agent.analyze_hr_coordinator(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], PeopleOpsFinding)
        mock_llm_client.chat.completions.create.assert_called_once()

    def test_analyze_hr_coordinator_leave_request(self, people_agent, mock_llm_client):
        """Test HR Coordinator handles leave requests."""
        state = PeopleDeskState(
            founder_id="test-founder-id",
            hr_events=[{
                "type": "leave_request",
                "leave_type": "Vacation",
                "from_date": "2024-04-15",
                "to_date": "2024-04-20",
                "reason": "Family vacation"
            }],
            task_type="hr_coordinator",
            employee_name="Jane Smith",
            result=None
        )
        
        result_state = people_agent.analyze_hr_coordinator(state)
        
        assert result_state["result"] is not None

    def test_analyze_hr_coordinator_appraisal(self, people_agent, mock_llm_client):
        """Test HR Coordinator handles appraisals."""
        state = PeopleDeskState(
            founder_id="test-founder-id",
            hr_events=[{
                "type": "appraisal",
                "review_type": "Annual",
                "due_date": "2024-03-31",
                "current_rating": "Exceeds Expectations"
            }],
            task_type="hr_coordinator",
            employee_name="Bob Johnson",
            result=None
        )
        
        result_state = people_agent.analyze_hr_coordinator(state)
        
        assert result_state["result"] is not None

    def test_analyze_internal_recruiter(self, people_agent, mock_llm_client):
        """Test Internal Recruiter handles hiring requests."""
        state = PeopleDeskState(
            founder_id="test-founder-id",
            hr_events=[{
                "type": "hiring_request",
                "role": "Product Manager",
                "department": "Product",
                "priority": "High",
                "hiring_manager": "Alice",
                "skills": ["Product Strategy", "Agile"],
                "experience": "Senior",
                "budget": 2500000
            }],
            task_type="internal_recruiter",
            result=None
        )
        
        result_state = people_agent.analyze_internal_recruiter(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], PeopleOpsFinding)


# =============================================================================
# Test LangGraph Workflow
# =============================================================================

class TestPeopleDeskGraph:
    """Test PeopleDesk LangGraph workflow."""

    def test_create_graph_returns_compiled_graph(self, people_agent):
        """Test create_graph returns a compiled StateGraph."""
        graph = people_agent.create_graph()
        
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_routes_to_hr_coordinator(self, people_agent, mock_llm_client):
        """Test graph routes to HR Coordinator."""
        graph = people_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "hr_events": [{"type": "onboarding", "start_date": "2024-04-01"}],
            "task_type": "hr_coordinator",
            "employee_name": "John Doe",
        })
        
        assert result is not None
        assert "result" in result

    def test_graph_routes_to_internal_recruiter(self, people_agent, mock_llm_client):
        """Test graph routes to Internal Recruiter."""
        graph = people_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "hr_events": [{"type": "hiring_request", "role": "Engineer"}],
            "task_type": "internal_recruiter",
        })
        
        assert result is not None

    def test_graph_default_routing(self, people_agent, mock_llm_client):
        """Test graph defaults to HR Coordinator for unknown types."""
        graph = people_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "hr_events": [],
            "task_type": "unknown_type",
        })
        
        assert result is not None


# =============================================================================
# Test Context Building Helpers
# =============================================================================

class TestPeopleDeskContextBuilding:
    """Test PeopleDeskAgent context building helpers."""

    def test_build_hr_coordinator_context_onboarding(self, people_agent):
        """Test HR Coordinator context for onboarding."""
        hr_events = [{
            "type": "onboarding",
            "start_date": "2024-04-01",
            "role": "Senior Engineer",
            "department": "Engineering"
        }]
        
        context = people_agent._build_hr_coordinator_context(hr_events, "John Doe")
        
        assert "Employee: John Doe" in context
        assert "Start Date: 2024-04-01" in context

    def test_build_hr_coordinator_context_leave(self, people_agent):
        """Test HR Coordinator context for leave request."""
        hr_events = [{
            "type": "leave_request",
            "leave_type": "Vacation",
            "from_date": "2024-04-15",
            "to_date": "2024-04-20"
        }]
        
        context = people_agent._build_hr_coordinator_context(hr_events, "Jane Smith")
        
        assert "Leave Type: Vacation" in context

    def test_build_recruiter_context(self, people_agent):
        """Test Internal Recruiter context building."""
        hr_events = [{
            "type": "hiring_request",
            "role": "Product Manager",
            "department": "Product",
            "priority": "High",
            "hiring_manager": "Alice",
            "skills": ["Strategy", "Agile"],
            "experience": "Senior",
            "budget": 2500000
        }]
        
        context = people_agent._build_recruiter_context(hr_events)
        
        assert "Role: Product Manager" in context
        assert "₹2,500,000" in context


# =============================================================================
# Integration Tests (Real LLM)
# =============================================================================

@pytest.mark.skipif(not os.environ.get("AZURE_OPENAI_ENDPOINT"), reason="No Azure OpenAI configured")
class TestPeopleDeskIntegration:
    """Integration tests with real Azure LLM."""

    def test_full_workflow_with_real_llm(self):
        """Test complete People Desk workflow with real LLM."""
        agent = PeopleDeskAgent()
        graph = agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "hr_events": [{
                "type": "onboarding",
                "start_date": "2024-04-01",
                "role": "Senior Engineer",
                "department": "Engineering"
            }],
            "task_type": "hr_coordinator",
            "employee_name": "John Doe",
        })
        
        assert result is not None
        assert "result" in result
        
        people_result = result["result"]
        assert isinstance(people_result, PeopleOpsFinding)
        assert " and " not in people_result.do_this.lower()
