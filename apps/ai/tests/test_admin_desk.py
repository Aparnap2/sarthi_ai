"""
Tests for Admin Desk Agent — Sarthi v4.2 Phase 3.

Tests cover:
- Agent initialization
- Both capabilities (EA, Knowledge Manager)
- Pydantic validation (SOP structure, single action)
- LangGraph workflow completion
- Real Azure LLM integration

Run with: pytest apps/ai/tests/test_admin_desk.py -v
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from src.schemas.desk_results import KnowledgeManagerResult, HitlRisk
from src.agents.admin_desk import AdminDeskAgent, AdminDeskState, get_admin_desk_agent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with realistic responses."""
    client = MagicMock()
    
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(
            content='{"topic": "Weekly Team Meeting", "extracted_sop": "1. Schedule meeting\\n2. Send agenda\\n3. Take notes", "neo4j_nodes_added": 3, "do_this": "Save to Notion", "hitl_risk": "low"}'
        ))]
    )
    
    return client


@pytest.fixture
def admin_agent(mock_llm_client):
    """Create AdminDeskAgent with mocked dependencies."""
    with patch('src.agents.admin_desk.get_llm_client', return_value=mock_llm_client):
        with patch('src.agents.admin_desk.get_chat_model', return_value='gpt-4'):
            agent = AdminDeskAgent()
            mock_llm_client.reset_mock(return_value=False, side_effect=False)
            return agent


# =============================================================================
# Test Pydantic Schema Validation
# =============================================================================

class TestKnowledgeManagerResultValidation:
    """Test KnowledgeManagerResult Pydantic validation."""

    def test_valid_result_creation(self):
        """Test creating a valid KnowledgeManagerResult."""
        result = KnowledgeManagerResult(
            topic="Weekly Team Meeting",
            extracted_sop="1. Schedule meeting\n2. Send agenda\n3. Take notes",
            neo4j_nodes_added=3,
            do_this="Save to Notion",
            hitl_risk=HitlRisk.LOW
        )
        
        assert result.topic == "Weekly Team Meeting"
        assert result.neo4j_nodes_added == 3
        assert result.hitl_risk == HitlRisk.LOW

    def test_default_hitl_risk(self):
        """Test that hitl_risk defaults to LOW."""
        result = KnowledgeManagerResult(
            topic="Test Topic",
            extracted_sop="1. Step one\n2. Step two",
            neo4j_nodes_added=1,
            do_this="Save documentation"
        )
        
        assert result.hitl_risk == HitlRisk.LOW

    def test_sop_minimum_length(self):
        """Test that SOP must be at least 20 characters."""
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeManagerResult(
                topic="Test",
                extracted_sop="Short",
                neo4j_nodes_added=1,
                do_this="Save"
            )
        
        assert "20 characters" in str(exc_info.value)

    def test_sop_step_by_step_structure_numbered(self):
        """Test that SOP must have step-by-step structure (numbered)."""
        result = KnowledgeManagerResult(
            topic="Test",
            extracted_sop="1. First step\n2. Second step\n3. Third step",
            neo4j_nodes_added=1,
            do_this="Save"
        )
        
        assert result.extracted_sop is not None

    def test_sop_step_by_step_structure_bulleted(self):
        """Test that SOP must have step-by-step structure (bulleted)."""
        result = KnowledgeManagerResult(
            topic="Test",
            extracted_sop="- First step\n- Second step\n- Third step",
            neo4j_nodes_added=1,
            do_this="Save"
        )
        
        assert result.extracted_sop is not None

    def test_sop_step_by_step_structure_with_star(self):
        """Test that SOP must have step-by-step structure (star bullets)."""
        result = KnowledgeManagerResult(
            topic="Test",
            extracted_sop="* First step\n* Second step",
            neo4j_nodes_added=1,
            do_this="Save"
        )
        
        assert result.extracted_sop is not None

    def test_sop_missing_step_structure(self):
        """Test that SOP without step structure is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeManagerResult(
                topic="Test",
                extracted_sop="This is just a paragraph without steps",
                neo4j_nodes_added=1,
                do_this="Save"
            )
        
        assert "step-by-step" in str(exc_info.value).lower()

    def test_single_action_validation(self):
        """Test that do_this with multiple actions is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeManagerResult(
                topic="Test",
                extracted_sop="1. Step one\n2. Step two",
                neo4j_nodes_added=1,
                do_this="Save to Notion and share with team"
            )
        
        assert "ONE action" in str(exc_info.value)

    def test_valid_single_action(self):
        """Test that single action passes validation."""
        result = KnowledgeManagerResult(
            topic="Test",
            extracted_sop="1. Step one\n2. Step two",
            neo4j_nodes_added=1,
            do_this="Save to Notion"
        )
        
        assert result.do_this == "Save to Notion"

    def test_neo4j_nodes_non_negative(self):
        """Test that neo4j_nodes_added must be non-negative."""
        with pytest.raises(ValidationError):
            KnowledgeManagerResult(
                topic="Test",
                extracted_sop="1. Step one",
                neo4j_nodes_added=-1,
                do_this="Save"
            )


# =============================================================================
# Test AdminDeskAgent Initialization
# =============================================================================

class TestAdminDeskAgentInitialization:
    """Test AdminDeskAgent initialization."""

    def test_agent_initializes_without_params(self, mock_llm_client):
        """Test AdminDeskAgent initializes without parameters."""
        with patch('src.agents.admin_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.admin_desk.get_chat_model', return_value='gpt-4'):
                agent = AdminDeskAgent()
                
                assert agent.client is not None
                assert agent.model == 'gpt-4'

    def test_get_admin_desk_agent_singleton(self, mock_llm_client):
        """Test get_admin_desk_agent returns singleton."""
        with patch('src.agents.admin_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.admin_desk.get_chat_model', return_value='gpt-4'):
                import src.agents.admin_desk as ad
                ad._admin_desk_agent = None
                
                agent1 = get_admin_desk_agent()
                agent2 = get_admin_desk_agent()
                
                assert agent1 is agent2


# =============================================================================
# Test AdminDeskAgent Capabilities
# =============================================================================

class TestAdminDeskAgentCapabilities:
    """Test AdminDeskAgent capabilities."""

    def test_analyze_ea_meetings(self, admin_agent, mock_llm_client):
        """Test EA capability handles meeting data."""
        state = AdminDeskState(
            founder_id="test-founder-id",
            meeting_data={
                "meetings": [
                    {"title": "Weekly Standup", "date": "2024-04-01", "attendees": ["Alice", "Bob"], "duration_minutes": 30, "status": "scheduled"},
                ],
                "action_items": [
                    {"description": "Review PR", "due_date": "2024-04-02", "status": "pending"},
                ]
            },
            knowledge_data={},
            task_type="ea",
            result=None
        )
        
        result_state = admin_agent.analyze_ea(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], dict)
        assert result_state["result"]["result_type"] == "ea_task"
        mock_llm_client.chat.completions.create.assert_called_once()

    def test_analyze_knowledge_manager(self, admin_agent, mock_llm_client):
        """Test Knowledge Manager capability extracts SOPs."""
        state = AdminDeskState(
            founder_id="test-founder-id",
            meeting_data={},
            knowledge_data={
                "documents": [
                    {"title": "Onboarding Guide", "type": "SOP", "preview": "This guide covers..."}
                ],
                "knowledge_graph_stats": {"total_nodes": 100, "total_relationships": 250}
            },
            task_type="knowledge_manager",
            result=None
        )
        
        result_state = admin_agent.analyze_knowledge_manager(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], KnowledgeManagerResult)


# =============================================================================
# Test LangGraph Workflow
# =============================================================================

class TestAdminDeskGraph:
    """Test AdminDesk LangGraph workflow."""

    def test_create_graph_returns_compiled_graph(self, admin_agent):
        """Test create_graph returns a compiled StateGraph."""
        graph = admin_agent.create_graph()
        
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_routes_to_ea(self, admin_agent, mock_llm_client):
        """Test graph routes to EA capability."""
        graph = admin_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "meeting_data": {"meetings": []},
            "knowledge_data": {},
            "task_type": "ea",
        })
        
        assert result is not None
        assert "result" in result

    def test_graph_routes_to_knowledge_manager(self, admin_agent, mock_llm_client):
        """Test graph routes to Knowledge Manager."""
        graph = admin_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "meeting_data": {},
            "knowledge_data": {"documents": []},
            "task_type": "knowledge_manager",
        })
        
        assert result is not None

    def test_graph_default_routing(self, admin_agent, mock_llm_client):
        """Test graph defaults to EA for unknown types."""
        graph = admin_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "meeting_data": {},
            "knowledge_data": {},
            "task_type": "unknown_type",
        })
        
        assert result is not None


# =============================================================================
# Test Context Building Helpers
# =============================================================================

class TestAdminDeskContextBuilding:
    """Test AdminDeskAgent context building helpers."""

    def test_build_ea_context_meetings(self, admin_agent):
        """Test EA context with meetings."""
        meeting_data = {
            "meetings": [
                {"title": "Weekly Standup", "date": "2024-04-01", "attendees": ["Alice", "Bob"], "duration_minutes": 30, "status": "scheduled"},
            ],
            "action_items": [
                {"description": "Review PR", "due_date": "2024-04-02", "status": "pending"},
            ]
        }
        
        context = admin_agent._build_ea_context(meeting_data)
        
        assert "Total Meetings: 1" in context
        assert "Upcoming: 1" in context
        assert "Pending Action Items: 1" in context

    def test_build_knowledge_context(self, admin_agent):
        """Test Knowledge Manager context building."""
        knowledge_data = {
            "documents": [
                {"title": "Onboarding Guide", "type": "SOP", "preview": "This guide covers the onboarding process..."}
            ],
            "knowledge_graph_stats": {"total_nodes": 100, "total_relationships": 250}
        }
        
        context = admin_agent._build_knowledge_context(knowledge_data)
        
        assert "Documents to Process: 1" in context
        assert "Knowledge Graph Stats:" in context
        assert "Total Nodes: 100" in context


# =============================================================================
# Integration Tests (Real LLM)
# =============================================================================

@pytest.mark.skipif(not os.environ.get("AZURE_OPENAI_ENDPOINT"), reason="No Azure OpenAI configured")
class TestAdminDeskIntegration:
    """Integration tests with real Azure LLM."""

    def test_full_workflow_with_real_llm(self):
        """Test complete Admin Desk workflow with real LLM."""
        agent = AdminDeskAgent()
        graph = agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "meeting_data": {
                "meetings": [{"title": "Weekly Standup", "date": "2024-04-01", "status": "scheduled"}],
            },
            "knowledge_data": {},
            "task_type": "ea",
        })
        
        assert result is not None
        assert "result" in result
        
        admin_result = result["result"]
        assert admin_result is not None
