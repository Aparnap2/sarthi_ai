"""
Tests for Intelligence Desk Agent — Sarthi v4.2 Phase 3.

Tests cover:
- Agent initialization
- Both capabilities (BI Analyst, Policy Watcher)
- Pydantic validation (jargon detection, single action, headline length)
- LangGraph workflow completion
- Real Azure LLM integration

Run with: pytest apps/ai/tests/test_intelligence_desk.py -v
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from src.schemas.desk_results import IntelligenceFinding, HitlRisk
from src.agents.intelligence_desk import IntelligenceDeskAgent, IntelligenceDeskState, get_intelligence_desk_agent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with realistic responses."""
    client = MagicMock()
    
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(
            content='{"insight_type": "churn_signal", "headline": "Customer cancellations increased 5% this month", "evidence": "3 customers cancelled, up from 1 last month", "do_this": "Schedule calls with at-risk customers", "hitl_risk": "high"}'
        ))]
    )
    
    return client


@pytest.fixture
def intelligence_agent(mock_llm_client):
    """Create IntelligenceDeskAgent with mocked dependencies."""
    with patch('src.agents.intelligence_desk.get_llm_client', return_value=mock_llm_client):
        with patch('src.agents.intelligence_desk.get_chat_model', return_value='gpt-4'):
            agent = IntelligenceDeskAgent()
            mock_llm_client.reset_mock(return_value=False, side_effect=False)
            return agent


# =============================================================================
# Test Pydantic Schema Validation
# =============================================================================

class TestIntelligenceFindingValidation:
    """Test IntelligenceFinding Pydantic validation."""

    def test_valid_finding_creation(self):
        """Test creating a valid IntelligenceFinding."""
        finding = IntelligenceFinding(
            insight_type="churn_signal",
            headline="Customer cancellations increased 5% this month",
            evidence="3 customers cancelled, up from 1 last month",
            do_this="Schedule calls with at-risk customers",
            hitl_risk=HitlRisk.HIGH
        )
        
        assert finding.insight_type == "churn_signal"
        assert finding.headline == "Customer cancellations increased 5% this month"
        assert finding.hitl_risk == HitlRisk.HIGH

    def test_jargon_detection_cac(self):
        """Test that CAC jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IntelligenceFinding(
                insight_type="unit_economics",
                headline="Acquisition costs increased",
                evidence="Customer Acquisition Cost went up",
                do_this="Review marketing spend",
                hitl_risk=HitlRisk.MEDIUM
            )
        
        assert "jargon" in str(exc_info.value).lower()
        assert "Customer Acquisition Cost" in str(exc_info.value)

    def test_jargon_detection_ltv(self):
        """Test that LTV jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IntelligenceFinding(
                insight_type="unit_economics",
                headline="LTV to CAC ratio improved",
                evidence="Lifetime Value increased",
                do_this="Continue current strategy",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "jargon" in str(exc_info.value).lower()

    def test_jargon_detection_arr(self):
        """Test that ARR jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IntelligenceFinding(
                insight_type="unit_economics",
                headline="ARR crossed 1 crore milestone",
                evidence="Annual Recurring Revenue increased",
                do_this="Celebrate milestone",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "jargon" in str(exc_info.value).lower()

    def test_jargon_detection_burn_rate(self):
        """Test that burn rate jargon is rejected in evidence."""
        with pytest.raises(ValidationError) as exc_info:
            IntelligenceFinding(
                insight_type="unit_economics",
                headline="Cash spending increased",
                evidence="Monthly burn rate is higher than planned",
                do_this="Review expenses",
                hitl_risk=HitlRisk.HIGH
            )
        
        assert "jargon" in str(exc_info.value).lower()
        assert "burn rate" in str(exc_info.value).lower()

    def test_headline_max_words(self):
        """Test that headline is limited to 10 words."""
        with pytest.raises(ValidationError) as exc_info:
            IntelligenceFinding(
                insight_type="ops_anomaly",
                headline="This is a very long headline that exceeds the maximum word count limit of ten words",
                evidence="Some evidence",
                do_this="Take action",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "10 words" in str(exc_info.value)

    def test_single_action_validation(self):
        """Test that do_this with multiple actions is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IntelligenceFinding(
                insight_type="churn_signal",
                headline="Churn increased",
                evidence="More customers leaving",
                do_this="Call customers and review pricing",
                hitl_risk=HitlRisk.HIGH
            )
        
        assert "ONE action" in str(exc_info.value)

    def test_valid_single_action(self):
        """Test that single action passes validation."""
        finding = IntelligenceFinding(
            insight_type="churn_signal",
            headline="Cancellations increased",
            evidence="More customers leaving",
            do_this="Call at-risk customers",
            hitl_risk=HitlRisk.HIGH
        )
        
        assert finding.do_this == "Call at-risk customers"


# =============================================================================
# Test IntelligenceDeskAgent Initialization
# =============================================================================

class TestIntelligenceDeskAgentInitialization:
    """Test IntelligenceDeskAgent initialization."""

    def test_agent_initializes_without_params(self, mock_llm_client):
        """Test IntelligenceDeskAgent initializes without parameters."""
        with patch('src.agents.intelligence_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.intelligence_desk.get_chat_model', return_value='gpt-4'):
                agent = IntelligenceDeskAgent()
                
                assert agent.client is not None
                assert agent.model == 'gpt-4'

    def test_get_intelligence_desk_agent_singleton(self, mock_llm_client):
        """Test get_intelligence_desk_agent returns singleton."""
        with patch('src.agents.intelligence_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.intelligence_desk.get_chat_model', return_value='gpt-4'):
                import src.agents.intelligence_desk as idesk
                idesk._intelligence_desk_agent = None
                
                agent1 = get_intelligence_desk_agent()
                agent2 = get_intelligence_desk_agent()
                
                assert agent1 is agent2


# =============================================================================
# Test IntelligenceDeskAgent Capabilities
# =============================================================================

class TestIntelligenceDeskAgentCapabilities:
    """Test IntelligenceDeskAgent capabilities."""

    def test_analyze_bi_churn_signal(self, intelligence_agent, mock_llm_client):
        """Test BI Analyst detects churn signals."""
        state = IntelligenceDeskState(
            founder_id="test-founder-id",
            business_data={
                "revenue": {"current_month": 500000, "previous_month": 450000, "growth_rate": 0.11},
                "customers": {"active": 50, "new": 5, "churned": 3, "churn_rate": 0.06},
                "operations": {"support_tickets": 25, "avg_response_hours": 4, "downtime_minutes": 10},
                "anomalies": [{"description": "Churn rate increased from 2% to 6%"}]
            },
            policy_data={},
            task_type="bi_analyst",
            result=None
        )
        
        result_state = intelligence_agent.analyze_bi(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], IntelligenceFinding)
        mock_llm_client.chat.completions.create.assert_called_once()

    def test_analyze_bi_ops_anomaly(self, intelligence_agent, mock_llm_client):
        """Test BI Analyst detects operational anomalies."""
        state = IntelligenceDeskState(
            founder_id="test-founder-id",
            business_data={
                "revenue": {"current_month": 500000, "previous_month": 500000, "growth_rate": 0.0},
                "customers": {"active": 50, "new": 2, "churned": 2, "churn_rate": 0.04},
                "operations": {"support_tickets": 100, "avg_response_hours": 24, "downtime_minutes": 120},
                "anomalies": [{"description": "Support tickets increased 300%"}]
            },
            policy_data={},
            task_type="bi_analyst",
            result=None
        )
        
        result_state = intelligence_agent.analyze_bi(state)
        
        assert result_state["result"] is not None

    def test_analyze_policy(self, intelligence_agent, mock_llm_client):
        """Test Policy Watcher capability."""
        state = IntelligenceDeskState(
            founder_id="test-founder-id",
            business_data={},
            policy_data={
                "recent_changes": [{
                    "name": "Remote Work Policy",
                    "type": "Internal",
                    "effective_date": "2024-04-01",
                    "summary": "Updated remote work guidelines",
                    "impact": "All employees"
                }],
                "regulatory_updates": []
            },
            task_type="policy_watcher",
            result=None
        )
        
        result_state = intelligence_agent.analyze_policy(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], IntelligenceFinding)


# =============================================================================
# Test LangGraph Workflow
# =============================================================================

class TestIntelligenceDeskGraph:
    """Test IntelligenceDesk LangGraph workflow."""

    def test_create_graph_returns_compiled_graph(self, intelligence_agent):
        """Test create_graph returns a compiled StateGraph."""
        graph = intelligence_agent.create_graph()
        
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_routes_to_bi_analyst(self, intelligence_agent, mock_llm_client):
        """Test graph routes to BI Analyst."""
        graph = intelligence_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "business_data": {"revenue": {"current_month": 500000}},
            "policy_data": {},
            "task_type": "bi_analyst",
        })
        
        assert result is not None
        assert "result" in result

    def test_graph_routes_to_policy_watcher(self, intelligence_agent, mock_llm_client):
        """Test graph routes to Policy Watcher."""
        graph = intelligence_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "business_data": {},
            "policy_data": {"recent_changes": []},
            "task_type": "policy_watcher",
        })
        
        assert result is not None

    def test_graph_default_routing(self, intelligence_agent, mock_llm_client):
        """Test graph defaults to BI Analyst for unknown types."""
        graph = intelligence_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "business_data": {},
            "policy_data": {},
            "task_type": "unknown_type",
        })
        
        assert result is not None


# =============================================================================
# Test Context Building Helpers
# =============================================================================

class TestIntelligenceDeskContextBuilding:
    """Test IntelligenceDeskAgent context building helpers."""

    def test_build_bi_context(self, intelligence_agent):
        """Test BI context building."""
        business_data = {
            "revenue": {"current_month": 500000, "previous_month": 450000, "growth_rate": 0.11},
            "customers": {"active": 50, "new": 5, "churned": 3, "churn_rate": 0.06},
            "operations": {"support_tickets": 25, "avg_response_hours": 4},
            "anomalies": [{"description": "Churn increased"}]
        }
        
        context = intelligence_agent._build_bi_context(business_data)
        
        assert "Revenue Metrics:" in context
        assert "Customer Metrics:" in context
        assert "Churn Rate:" in context

    def test_build_policy_context(self, intelligence_agent):
        """Test Policy context building."""
        policy_data = {
            "recent_changes": [{
                "name": "Remote Work Policy",
                "type": "Internal",
                "effective_date": "2024-04-01",
                "summary": "Updated guidelines",
                "impact": "All employees"
            }],
            "regulatory_updates": [{"title": "New Tax Rule", "deadline": "2024-04-30"}]
        }
        
        context = intelligence_agent._build_policy_context(policy_data)
        
        assert "Recent Policy Changes:" in context
        assert "Remote Work Policy" in context


# =============================================================================
# Integration Tests (Real LLM)
# =============================================================================

@pytest.mark.skipif(not os.environ.get("AZURE_OPENAI_ENDPOINT"), reason="No Azure OpenAI configured")
class TestIntelligenceDeskIntegration:
    """Integration tests with real Azure LLM."""

    def test_full_workflow_with_real_llm(self):
        """Test complete Intelligence Desk workflow with real LLM."""
        agent = IntelligenceDeskAgent()
        graph = agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "business_data": {
                "revenue": {"current_month": 500000, "previous_month": 450000, "growth_rate": 0.11},
                "customers": {"active": 50, "new": 5, "churned": 3, "churn_rate": 0.06},
            },
            "policy_data": {},
            "task_type": "bi_analyst",
        })
        
        assert result is not None
        assert "result" in result
        
        intel_result = result["result"]
        assert isinstance(intel_result, IntelligenceFinding)
        assert len(intel_result.headline.split()) <= 10
        assert " and " not in intel_result.do_this.lower()
