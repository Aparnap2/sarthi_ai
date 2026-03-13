"""
Tests for Chief of Staff Agent — Sarthi v4.2 Phase 3.

Tests cover:
- Agent initialization
- Event routing to all 6 desks
- Internal-ops only enforcement (no external-facing agents)
- LangGraph workflow completion
- Real Azure LLM integration

Run with: pytest apps/ai/tests/test_chief_of_staff_routing.py -v
"""

import pytest
import os
from unittest.mock import MagicMock, patch

from src.agents.chief_of_staff_agent import (
    ChiefOfStaffAgent,
    ChiefOfStaffState,
    DESK_ROUTING_MAP,
    DESK_TASK_TYPES,
    get_chief_of_staff_agent,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    
    # Mock routing fallback
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="admin"))]
    )
    
    return client


@pytest.fixture
def chief_agent(mock_llm_client):
    """Create ChiefOfStaffAgent with mocked dependencies."""
    with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
        with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
            # Mock desk agents
            with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent') as mock_finance:
                with patch('src.agents.chief_of_staff_agent.get_people_desk_agent') as mock_people:
                    with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent') as mock_legal:
                        with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent') as mock_intel:
                            with patch('src.agents.chief_of_staff_agent.get_it_desk_agent') as mock_it:
                                with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent') as mock_admin:
                                    # Setup mock graphs
                                    mock_graph = MagicMock()
                                    mock_graph.invoke.return_value = {"result": {"test": "data"}}
                                    
                                    mock_finance.return_value.create_graph.return_value = mock_graph
                                    mock_people.return_value.create_graph.return_value = mock_graph
                                    mock_legal.return_value.create_graph.return_value = mock_graph
                                    mock_intel.return_value.create_graph.return_value = mock_graph
                                    mock_it.return_value.create_graph.return_value = mock_graph
                                    mock_admin.return_value.create_graph.return_value = mock_graph
                                    
                                    agent = ChiefOfStaffAgent()
                                    return agent


# =============================================================================
# Test Routing Map Configuration
# =============================================================================

class TestRoutingMapConfiguration:
    """Test DESK_ROUTING_MAP configuration."""

    def test_finance_desk_events(self):
        """Test Finance Desk event routing."""
        finance_events = [
            "bank_statement",
            "transaction_categorized",
            "invoice_overdue",
            "payment_received",
            "payroll_due",
            "reconciliation_needed",
            "ar_reminder",
            "ap_due",
            "payroll_prep",
        ]
        
        for event in finance_events:
            assert DESK_ROUTING_MAP.get(event) == "finance", f"Event {event} should route to finance"

    def test_people_desk_events(self):
        """Test People Desk event routing."""
        people_events = [
            "new_hire",
            "employee_onboarding",
            "leave_request",
            "appraisal_due",
            "offboarding",
            "hiring_request",
            "interview_scheduled",
        ]
        
        for event in people_events:
            assert DESK_ROUTING_MAP.get(event) == "people", f"Event {event} should route to people"

    def test_legal_desk_events(self):
        """Test Legal Desk event routing."""
        legal_events = [
            "contract_uploaded",
            "contract_expiry",
            "compliance_due",
            "regulatory_filing",
            "policy_update",
        ]
        
        for event in legal_events:
            assert DESK_ROUTING_MAP.get(event) == "legal", f"Event {event} should route to legal"

    def test_intelligence_desk_events(self):
        """Test Intelligence Desk event routing."""
        intel_events = [
            "revenue_anomaly",
            "churn_detected",
            "unit_economics_review",
            "ops_anomaly",
            "policy_change_detected",
        ]
        
        for event in intel_events:
            assert DESK_ROUTING_MAP.get(event) == "intelligence", f"Event {event} should route to intelligence"

    def test_it_desk_events(self):
        """Test IT Desk event routing."""
        it_events = [
            "saas_subscription",
            "tool_unused",
            "access_review_due",
            "security_audit",
            "cost_optimization",
        ]
        
        for event in it_events:
            assert DESK_ROUTING_MAP.get(event) == "it", f"Event {event} should route to it"

    def test_admin_desk_events(self):
        """Test Admin Desk event routing."""
        admin_events = [
            "meeting_transcript",
            "calendar_management",
            "sop_extraction",
            "documentation_update",
            "knowledge_capture",
        ]
        
        for event in admin_events:
            assert DESK_ROUTING_MAP.get(event) == "admin", f"Event {event} should route to admin"

    def test_no_external_facing_agents(self):
        """Test that no external-facing agents are in routing map."""
        external_keywords = [
            "revops", "revenue_ops", "gtm", "go_to_market",
            "market_intel", "market_intelligence", "sales",
            "marketing", "outbound", "inbound", "lead",
        ]
        
        for event in DESK_ROUTING_MAP.keys():
            for keyword in external_keywords:
                assert keyword not in event.lower(), f"External-facing event found: {event}"


# =============================================================================
# Test ChiefOfStaffAgent Initialization
# =============================================================================

class TestChiefOfStaffAgentInitialization:
    """Test ChiefOfStaffAgent initialization."""

    def test_agent_initializes_with_all_desks(self, mock_llm_client):
        """Test ChiefOfStaffAgent initializes with all 6 desk agents."""
        with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
                with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent'):
                    with patch('src.agents.chief_of_staff_agent.get_people_desk_agent'):
                        with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent'):
                            with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent'):
                                with patch('src.agents.chief_of_staff_agent.get_it_desk_agent'):
                                    with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent'):
                                        agent = ChiefOfStaffAgent()
                                        
                                        assert agent.finance is not None
                                        assert agent.people is not None
                                        assert agent.legal is not None
                                        assert agent.intelligence is not None
                                        assert agent.it is not None
                                        assert agent.admin is not None

    def test_get_chief_of_staff_agent_singleton(self, mock_llm_client):
        """Test get_chief_of_staff_agent returns singleton."""
        with patch('src.agents.chief_of_staff_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.chief_of_staff_agent.get_chat_model', return_value='gpt-4'):
                with patch('src.agents.chief_of_staff_agent.get_finance_desk_agent'):
                    with patch('src.agents.chief_of_staff_agent.get_people_desk_agent'):
                        with patch('src.agents.chief_of_staff_agent.get_legal_desk_agent'):
                            with patch('src.agents.chief_of_staff_agent.get_intelligence_desk_agent'):
                                with patch('src.agents.chief_of_staff_agent.get_it_desk_agent'):
                                    with patch('src.agents.chief_of_staff_agent.get_admin_desk_agent'):
                                        import src.agents.chief_of_staff_agent as cos
                                        cos._chief_of_staff_agent = None
                                        
                                        agent1 = get_chief_of_staff_agent()
                                        agent2 = get_chief_of_staff_agent()
                                        
                                        assert agent1 is agent2


# =============================================================================
# Test Event Routing
# =============================================================================

class TestChiefOfStaffEventRouting:
    """Test ChiefOfStaffAgent event routing."""

    def test_route_bank_statement_to_finance(self, chief_agent):
        """Test bank_statement routes to Finance Desk."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="bank_statement",
            event_payload={"balance": 500000},
            routed_to=None,
            result=None
        )
        
        result_state = chief_agent.route_event(state)
        
        assert result_state["routed_to"] == "finance"

    def test_route_new_hire_to_people(self, chief_agent):
        """Test new_hire routes to People Desk."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="new_hire",
            event_payload={"employee_name": "John Doe"},
            routed_to=None,
            result=None
        )
        
        result_state = chief_agent.route_event(state)
        
        assert result_state["routed_to"] == "people"

    def test_route_contract_uploaded_to_legal(self, chief_agent):
        """Test contract_uploaded routes to Legal Desk."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="contract_uploaded",
            event_payload={"contract_name": "Vendor Agreement"},
            routed_to=None,
            result=None
        )
        
        result_state = chief_agent.route_event(state)
        
        assert result_state["routed_to"] == "legal"

    def test_route_revenue_anomaly_to_intelligence(self, chief_agent):
        """Test revenue_anomaly routes to Intelligence Desk."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="revenue_anomaly",
            event_payload={"anomaly_type": "spike"},
            routed_to=None,
            result=None
        )
        
        result_state = chief_agent.route_event(state)
        
        assert result_state["routed_to"] == "intelligence"

    def test_route_saas_subscription_to_it(self, chief_agent):
        """Test saas_subscription routes to IT Desk."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="saas_subscription",
            event_payload={"tool_name": "Slack"},
            routed_to=None,
            result=None
        )
        
        result_state = chief_agent.route_event(state)
        
        assert result_state["routed_to"] == "it"

    def test_route_meeting_transcript_to_admin(self, chief_agent):
        """Test meeting_transcript routes to Admin Desk."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="meeting_transcript",
            event_payload={"transcript": "Meeting content..."},
            routed_to=None,
            result=None
        )
        
        result_state = chief_agent.route_event(state)
        
        assert result_state["routed_to"] == "admin"

    def test_route_unknown_event_fallback_to_llm(self, chief_agent, mock_llm_client):
        """Test unknown events use LLM fallback routing."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="unknown_event_type",
            event_payload={},
            routed_to=None,
            result=None
        )
        
        result_state = chief_agent.route_event(state)
        
        # Should use LLM fallback (mocked to return "admin")
        assert result_state["routed_to"] == "admin"
        mock_llm_client.chat.completions.create.assert_called_once()


# =============================================================================
# Test Desk Processing
# =============================================================================

class TestChiefOfStaffDeskProcessing:
    """Test ChiefOfStaffAgent desk processing."""

    def test_process_finance(self, chief_agent):
        """Test Finance Desk processing."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="bank_statement",
            event_payload={
                "bank_data": {"balance": 500000},
                "accounting_data": {"revenue": 600000}
            },
            routed_to="finance",
            result=None
        )
        
        result_state = chief_agent.process_finance(state)
        
        assert result_state["result"] is not None

    def test_process_people(self, chief_agent):
        """Test People Desk processing."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="new_hire",
            event_payload={
                "hr_events": [{"type": "onboarding"}],
                "employee_name": "John Doe"
            },
            routed_to="people",
            result=None
        )
        
        result_state = chief_agent.process_people(state)
        
        assert result_state["result"] is not None

    def test_process_legal(self, chief_agent):
        """Test Legal Desk processing."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="contract_uploaded",
            event_payload={
                "legal_documents": [{"type": "contract", "name": "Agreement"}]
            },
            routed_to="legal",
            result=None
        )
        
        result_state = chief_agent.process_legal(state)
        
        assert result_state["result"] is not None

    def test_process_intelligence(self, chief_agent):
        """Test Intelligence Desk processing."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="revenue_anomaly",
            event_payload={
                "business_data": {"revenue": {"current_month": 500000}},
                "policy_data": {}
            },
            routed_to="intelligence",
            result=None
        )
        
        result_state = chief_agent.process_intelligence(state)
        
        assert result_state["result"] is not None

    def test_process_it(self, chief_agent):
        """Test IT Desk processing."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="saas_subscription",
            event_payload={
                "tools_data": {"tools": [{"name": "Slack"}]}
            },
            routed_to="it",
            result=None
        )
        
        result_state = chief_agent.process_it(state)
        
        assert result_state["result"] is not None

    def test_process_admin(self, chief_agent):
        """Test Admin Desk processing."""
        state = ChiefOfStaffState(
            founder_id="test-founder-id",
            event_type="meeting_transcript",
            event_payload={
                "meeting_data": {"meetings": []},
                "knowledge_data": {}
            },
            routed_to="admin",
            result=None
        )
        
        result_state = chief_agent.process_admin(state)
        
        assert result_state["result"] is not None


# =============================================================================
# Test LangGraph Workflow
# =============================================================================

class TestChiefOfStaffGraph:
    """Test ChiefOfStaff LangGraph workflow."""

    def test_create_graph_returns_compiled_graph(self, chief_agent):
        """Test create_graph returns a compiled StateGraph."""
        graph = chief_agent.create_graph()
        
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_routes_and_processes_finance(self, chief_agent):
        """Test graph routes and processes Finance events."""
        graph = chief_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "event_type": "bank_statement",
            "event_payload": {"bank_data": {"balance": 500000}},
        })
        
        assert result is not None
        assert "routed_to" in result
        assert result["routed_to"] == "finance"

    def test_graph_routes_and_processes_people(self, chief_agent):
        """Test graph routes and processes People events."""
        graph = chief_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "event_type": "new_hire",
            "event_payload": {"hr_events": []},
        })
        
        assert result is not None
        assert result["routed_to"] == "people"

    def test_graph_routes_and_processes_legal(self, chief_agent):
        """Test graph routes and processes Legal events."""
        graph = chief_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "event_type": "contract_uploaded",
            "event_payload": {"legal_documents": []},
        })
        
        assert result is not None
        assert result["routed_to"] == "legal"

    def test_graph_routes_and_processes_intelligence(self, chief_agent):
        """Test graph routes and processes Intelligence events."""
        graph = chief_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "event_type": "revenue_anomaly",
            "event_payload": {"business_data": {}},
        })
        
        assert result is not None
        assert result["routed_to"] == "intelligence"

    def test_graph_routes_and_processes_it(self, chief_agent):
        """Test graph routes and processes IT events."""
        graph = chief_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "event_type": "saas_subscription",
            "event_payload": {"tools_data": {}},
        })
        
        assert result is not None
        assert result["routed_to"] == "it"

    def test_graph_routes_and_processes_admin(self, chief_agent):
        """Test graph routes and processes Admin events."""
        graph = chief_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "event_type": "meeting_transcript",
            "event_payload": {"meeting_data": {}},
        })
        
        assert result is not None
        assert result["routed_to"] == "admin"


# =============================================================================
# Test Desk Task Type Mapping
# =============================================================================

class TestDeskTaskTypeMapping:
    """Test DESK_TASK_TYPES mapping."""

    def test_finance_task_types(self):
        """Test Finance Desk task type mapping."""
        assert "finance" in DESK_TASK_TYPES
        assert DESK_TASK_TYPES["finance"]["bank_statement"] == "cfo"
        assert DESK_TASK_TYPES["finance"]["payroll_due"] == "payroll"

    def test_people_task_types(self):
        """Test People Desk task type mapping."""
        assert "people" in DESK_TASK_TYPES
        assert DESK_TASK_TYPES["people"]["new_hire"] == "hr_coordinator"
        assert DESK_TASK_TYPES["people"]["hiring_request"] == "internal_recruiter"

    def test_legal_task_types(self):
        """Test Legal Desk task type mapping."""
        assert "legal" in DESK_TASK_TYPES
        assert DESK_TASK_TYPES["legal"]["contract_uploaded"] == "contracts"
        assert DESK_TASK_TYPES["legal"]["compliance_due"] == "compliance"

    def test_intelligence_task_types(self):
        """Test Intelligence Desk task type mapping."""
        assert "intelligence" in DESK_TASK_TYPES
        assert DESK_TASK_TYPES["intelligence"]["revenue_anomaly"] == "bi_analyst"
        assert DESK_TASK_TYPES["intelligence"]["policy_change_detected"] == "policy_watcher"

    def test_it_task_types(self):
        """Test IT Desk task type mapping."""
        assert "it" in DESK_TASK_TYPES
        assert DESK_TASK_TYPES["it"]["saas_subscription"] == "saas_management"
        assert DESK_TASK_TYPES["it"]["security_audit"] == "security_review"

    def test_admin_task_types(self):
        """Test Admin Desk task type mapping."""
        assert "admin" in DESK_TASK_TYPES
        assert DESK_TASK_TYPES["admin"]["meeting_transcript"] == "ea"
        assert DESK_TASK_TYPES["admin"]["sop_extraction"] == "knowledge_manager"


# =============================================================================
# Integration Tests (Real LLM)
# =============================================================================

@pytest.mark.skipif(not os.environ.get("AZURE_OPENAI_ENDPOINT"), reason="No Azure OpenAI configured")
class TestChiefOfStaffIntegration:
    """Integration tests with real Azure LLM."""

    def test_full_workflow_with_real_llm(self):
        """Test complete Chief of Staff workflow with real LLM."""
        agent = ChiefOfStaffAgent()
        graph = agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "event_type": "bank_statement",
            "event_payload": {
                "bank_data": {"balance": 500000},
                "accounting_data": {"revenue": 600000}
            },
        })
        
        assert result is not None
        assert "routed_to" in result
        assert result["routed_to"] == "finance"
