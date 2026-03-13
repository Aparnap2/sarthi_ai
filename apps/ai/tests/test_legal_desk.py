"""
Tests for Legal Desk Agent — Sarthi v4.2 Phase 3.

Tests cover:
- Agent initialization
- Both capabilities (Contracts, Compliance)
- Pydantic validation (legalese detection, single action)
- LangGraph workflow completion

Run with: pytest apps/ai/tests/test_legal_desk.py -v
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from src.schemas.desk_results import LegalOpsResult, HitlRisk
from src.agents.legal_desk import LegalDeskAgent, LegalDeskState, get_legal_desk_agent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with realistic responses."""
    client = MagicMock()
    
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(
            content='{"document_type": "Vendor Contract", "document_name": "AWS Service Agreement", "expiry_date": "2024-12-31", "action_required": "Renew contract before expiry", "hitl_risk": "medium"}'
        ))]
    )
    
    return client


@pytest.fixture
def legal_agent(mock_llm_client):
    """Create LegalDeskAgent with mocked dependencies."""
    with patch('src.agents.legal_desk.get_llm_client', return_value=mock_llm_client):
        with patch('src.agents.legal_desk.get_chat_model', return_value='gpt-4'):
            agent = LegalDeskAgent()
            mock_llm_client.reset_mock(return_value=False, side_effect=False)
            return agent


# =============================================================================
# Test Pydantic Schema Validation
# =============================================================================

class TestLegalOpsResultValidation:
    """Test LegalOpsResult Pydantic validation."""

    def test_valid_result_creation(self):
        """Test creating a valid LegalOpsResult."""
        result = LegalOpsResult(
            document_type="Vendor Contract",
            document_name="AWS Service Agreement",
            expiry_date="2024-12-31",
            action_required="Renew contract before expiry",
            hitl_risk=HitlRisk.MEDIUM
        )
        
        assert result.document_type == "Vendor Contract"
        assert result.document_name == "AWS Service Agreement"
        assert result.expiry_date == "2024-12-31"

    def test_legalese_detection_heretofore(self):
        """Test that heretofore legalese is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LegalOpsResult(
                document_type="Contract",
                document_name="Test Contract",
                action_required="Review heretofore mentioned clauses",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "Legalese" in str(exc_info.value)
        assert "heretofore" in str(exc_info.value)

    def test_legalese_detection_notwithstanding(self):
        """Test that notwithstanding legalese is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LegalOpsResult(
                document_type="Contract",
                document_name="Test Contract",
                action_required="Proceed notwithstanding delays",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "Legalese" in str(exc_info.value)

    def test_legalese_detection_indemnification(self):
        """Test that indemnification legalese is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LegalOpsResult(
                document_type="Contract",
                document_name="Test Contract",
                action_required="Review indemnification terms",
                hitl_risk=HitlRisk.MEDIUM
            )
        
        assert "Legalese" in str(exc_info.value)

    def test_single_action_validation(self):
        """Test that action_required with multiple actions is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LegalOpsResult(
                document_type="Contract",
                document_name="Test Contract",
                action_required="Review contract and send for signature",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "ONE action" in str(exc_info.value)

    def test_valid_single_action(self):
        """Test that single action passes validation."""
        result = LegalOpsResult(
            document_type="Vendor Contract",
            document_name="AWS Agreement",
            action_required="Renew contract",
            hitl_risk=HitlRisk.MEDIUM
        )
        
        assert result.action_required == "Renew contract"


# =============================================================================
# Test LegalDeskAgent Initialization
# =============================================================================

class TestLegalDeskAgentInitialization:
    """Test LegalDeskAgent initialization."""

    def test_agent_initializes_without_params(self, mock_llm_client):
        """Test LegalDeskAgent initializes without parameters."""
        with patch('src.agents.legal_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.legal_desk.get_chat_model', return_value='gpt-4'):
                agent = LegalDeskAgent()
                
                assert agent.client is not None
                assert agent.model == 'gpt-4'

    def test_get_legal_desk_agent_singleton(self, mock_llm_client):
        """Test get_legal_desk_agent returns singleton."""
        with patch('src.agents.legal_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.legal_desk.get_chat_model', return_value='gpt-4'):
                import src.agents.legal_desk as ld
                ld._legal_desk_agent = None
                
                agent1 = get_legal_desk_agent()
                agent2 = get_legal_desk_agent()
                
                assert agent1 is agent2


# =============================================================================
# Test LegalDeskAgent Capabilities
# =============================================================================

class TestLegalDeskAgentCapabilities:
    """Test LegalDeskAgent capabilities."""

    def test_analyze_contracts(self, legal_agent, mock_llm_client):
        """Test Contracts Coordinator capability."""
        state = LegalDeskState(
            founder_id="test-founder-id",
            legal_documents=[{
                "type": "contract",
                "name": "AWS Service Agreement",
                "days_until_expiry": 30,
                "value": 500000,
                "counterparty": "Amazon Web Services"
            }],
            task_type="contracts",
            result=None
        )
        
        result_state = legal_agent.analyze_contracts(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], LegalOpsResult)
        mock_llm_client.chat.completions.create.assert_called_once()

    def test_analyze_compliance(self, legal_agent, mock_llm_client):
        """Test Compliance Tracker capability."""
        state = LegalDeskState(
            founder_id="test-founder-id",
            legal_documents=[{
                "type": "compliance",
                "name": "GST Monthly Filing",
                "status": "pending",
                "days_until_due": 10
            }],
            task_type="compliance",
            result=None
        )
        
        result_state = legal_agent.analyze_compliance(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], LegalOpsResult)


# =============================================================================
# Test LangGraph Workflow
# =============================================================================

class TestLegalDeskGraph:
    """Test LegalDesk LangGraph workflow."""

    def test_create_graph_returns_compiled_graph(self, legal_agent):
        """Test create_graph returns a compiled StateGraph."""
        graph = legal_agent.create_graph()
        
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_routes_to_contracts(self, legal_agent, mock_llm_client):
        """Test graph routes to Contracts capability."""
        graph = legal_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "legal_documents": [{"type": "contract", "name": "Test Contract"}],
            "task_type": "contracts",
        })
        
        assert result is not None
        assert "result" in result

    def test_graph_routes_to_compliance(self, legal_agent, mock_llm_client):
        """Test graph routes to Compliance capability."""
        graph = legal_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "legal_documents": [{"type": "compliance", "name": "GST Filing"}],
            "task_type": "compliance",
        })
        
        assert result is not None

    def test_graph_default_routing(self, legal_agent, mock_llm_client):
        """Test graph defaults to Contracts for unknown types."""
        graph = legal_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "legal_documents": [],
            "task_type": "unknown_type",
        })
        
        assert result is not None


# =============================================================================
# Test Context Building Helpers
# =============================================================================

class TestLegalDeskContextBuilding:
    """Test LegalDeskAgent context building helpers."""

    def test_build_contracts_context_expiring(self, legal_agent):
        """Test Contracts context with expiring contracts."""
        legal_documents = [{
            "type": "contract",
            "name": "AWS Agreement",
            "days_until_expiry": 15,
            "value": 500000,
            "counterparty": "AWS"
        }]
        
        context = legal_agent._build_contracts_context(legal_documents)
        
        assert "Total Contracts: 1" in context
        assert "Expiring in 30 days: 1" in context
        assert "AWS Agreement" in context

    def test_build_compliance_context_overdue(self, legal_agent):
        """Test Compliance context with overdue items."""
        legal_documents = [{
            "type": "compliance",
            "name": "GST Filing",
            "status": "overdue",
            "days_overdue": 5,
            "penalty": 10000
        }]
        
        context = legal_agent._build_compliance_context(legal_documents)
        
        assert "Overdue: 1" in context
        assert "GST Filing" in context


# =============================================================================
# Integration Tests (Real LLM)
# =============================================================================

@pytest.mark.skipif(not os.environ.get("AZURE_OPENAI_ENDPOINT"), reason="No Azure OpenAI configured")
class TestLegalDeskIntegration:
    """Integration tests with real Azure LLM."""

    def test_full_workflow_with_real_llm(self):
        """Test complete Legal Desk workflow with real LLM."""
        agent = LegalDeskAgent()
        graph = agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "legal_documents": [{
                "type": "contract",
                "name": "Vendor Agreement",
                "days_until_expiry": 30,
                "value": 500000
            }],
            "task_type": "contracts",
        })
        
        assert result is not None
        assert "result" in result
        
        legal_result = result["result"]
        assert isinstance(legal_result, LegalOpsResult)
        assert " and " not in legal_result.action_required.lower()
