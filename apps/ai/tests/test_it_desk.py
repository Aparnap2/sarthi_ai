"""
Tests for IT Desk Agent — Sarthi v4.2 Phase 3.

Tests cover:
- Agent initialization
- All capabilities (SaaS, Access, Security)
- Pydantic validation (jargon detection, single action)
- LangGraph workflow completion
- Real Azure LLM integration

Run with: pytest apps/ai/tests/test_it_desk.py -v
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from src.schemas.desk_results import ITRiskAlert, HitlRisk
from src.agents.it_desk import ITDeskAgent, ITDeskState, get_it_desk_agent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with realistic responses."""
    client = MagicMock()
    
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(
            content='{"tool_name": "Slack", "monthly_cost": 5000, "days_unused": 45, "do_this": "Cancel unused subscription", "hitl_risk": "medium"}'
        ))]
    )
    
    return client


@pytest.fixture
def it_agent(mock_llm_client):
    """Create ITDeskAgent with mocked dependencies."""
    with patch('src.agents.it_desk.get_llm_client', return_value=mock_llm_client):
        with patch('src.agents.it_desk.get_chat_model', return_value='gpt-4'):
            agent = ITDeskAgent()
            mock_llm_client.reset_mock(return_value=False, side_effect=False)
            return agent


# =============================================================================
# Test Pydantic Schema Validation
# =============================================================================

class TestITRiskAlertValidation:
    """Test ITRiskAlert Pydantic validation."""

    def test_valid_alert_creation(self):
        """Test creating a valid ITRiskAlert."""
        alert = ITRiskAlert(
            tool_name="Slack",
            monthly_cost=5000,
            days_unused=45,
            do_this="Cancel unused subscription",
            hitl_risk=HitlRisk.MEDIUM
        )
        
        assert alert.tool_name == "Slack"
        assert alert.monthly_cost == 5000
        assert alert.days_unused == 45
        assert alert.hitl_risk == HitlRisk.MEDIUM

    def test_default_hitl_risk(self):
        """Test that hitl_risk defaults to MEDIUM."""
        alert = ITRiskAlert(
            tool_name="Zoom",
            monthly_cost=3000,
            days_unused=30,
            do_this="Review usage"
        )
        
        assert alert.hitl_risk == HitlRisk.MEDIUM

    def test_jargon_detection_provision(self):
        """Test that provision jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ITRiskAlert(
                tool_name="AWS",
                monthly_cost=10000,
                days_unused=30,
                do_this="Deprovision unused resources"
            )
        
        assert "jargon" in str(exc_info.value).lower()
        assert "provision" in str(exc_info.value).lower()

    def test_jargon_detection_saas(self):
        """Test that SaaS jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ITRiskAlert(
                tool_name="Generic",
                monthly_cost=5000,
                days_unused=30,
                do_this="Review SaaS subscriptions"
            )
        
        assert "jargon" in str(exc_info.value).lower()

    def test_single_action_validation(self):
        """Test that do_this with multiple actions is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ITRiskAlert(
                tool_name="Slack",
                monthly_cost=5000,
                days_unused=45,
                do_this="Cancel subscription and notify team"
            )
        
        assert "ONE action" in str(exc_info.value)

    def test_valid_single_action(self):
        """Test that single action passes validation."""
        alert = ITRiskAlert(
            tool_name="Slack",
            monthly_cost=5000,
            days_unused=45,
            do_this="Cancel subscription"
        )
        
        assert alert.do_this == "Cancel subscription"

    def test_monthly_cost_validation(self):
        """Test that monthly_cost must be non-negative."""
        with pytest.raises(ValidationError):
            ITRiskAlert(
                tool_name="Test",
                monthly_cost=-100,
                days_unused=30,
                do_this="Review"
            )

    def test_days_unused_validation(self):
        """Test that days_unused must be non-negative."""
        with pytest.raises(ValidationError):
            ITRiskAlert(
                tool_name="Test",
                monthly_cost=100,
                days_unused=-5,
                do_this="Review"
            )


# =============================================================================
# Test ITDeskAgent Initialization
# =============================================================================

class TestITDeskAgentInitialization:
    """Test ITDeskAgent initialization."""

    def test_agent_initializes_without_params(self, mock_llm_client):
        """Test ITDeskAgent initializes without parameters."""
        with patch('src.agents.it_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.it_desk.get_chat_model', return_value='gpt-4'):
                agent = ITDeskAgent()
                
                assert agent.client is not None
                assert agent.model == 'gpt-4'

    def test_get_it_desk_agent_singleton(self, mock_llm_client):
        """Test get_it_desk_agent returns singleton."""
        with patch('src.agents.it_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.it_desk.get_chat_model', return_value='gpt-4'):
                import src.agents.it_desk as itd
                itd._it_desk_agent = None
                
                agent1 = get_it_desk_agent()
                agent2 = get_it_desk_agent()
                
                assert agent1 is agent2


# =============================================================================
# Test ITDeskAgent Capabilities
# =============================================================================

class TestITDeskAgentCapabilities:
    """Test ITDeskAgent capabilities."""

    def test_analyze_saas_unused_tools(self, it_agent, mock_llm_client):
        """Test SaaS management identifies unused tools."""
        state = ITDeskState(
            founder_id="test-founder-id",
            tools_data={
                "tools": [
                    {"name": "Slack", "monthly_cost": 5000, "days_since_last_use": 45, "assigned_users": 2},
                    {"name": "Zoom", "monthly_cost": 3000, "days_since_last_use": 5, "assigned_users": 10},
                ]
            },
            task_type="saas_management",
            result=None
        )
        
        result_state = it_agent.analyze_saas(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], ITRiskAlert)
        mock_llm_client.chat.completions.create.assert_called_once()

    def test_analyze_access_orphaned_accounts(self, it_agent, mock_llm_client):
        """Test Access review identifies orphaned accounts."""
        state = ITDeskState(
            founder_id="test-founder-id",
            tools_data={
                "access_issues": [
                    {"type": "orphaned", "user_email": "ex@company.com", "tool": "GitHub", "last_access": "2024-01-01"},
                ]
            },
            task_type="access_review",
            result=None
        )
        
        result_state = it_agent.analyze_access(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], ITRiskAlert)

    def test_analyze_security_issues(self, it_agent, mock_llm_client):
        """Test Security review identifies issues."""
        state = ITDeskState(
            founder_id="test-founder-id",
            tools_data={
                "security_issues": [
                    {"tool": "AWS", "severity": "high", "description": "Public S3 bucket", "affected_users": 5},
                ],
                "tools_without_2fa": [{"name": "AWS"}, {"name": "GitHub"}]
            },
            task_type="security_review",
            result=None
        )
        
        result_state = it_agent.analyze_security(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], ITRiskAlert)


# =============================================================================
# Test LangGraph Workflow
# =============================================================================

class TestITDeskGraph:
    """Test ITDesk LangGraph workflow."""

    def test_create_graph_returns_compiled_graph(self, it_agent):
        """Test create_graph returns a compiled StateGraph."""
        graph = it_agent.create_graph()
        
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graph_routes_to_saas_management(self, it_agent, mock_llm_client):
        """Test graph routes to SaaS management."""
        graph = it_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "tools_data": {"tools": [{"name": "Slack", "monthly_cost": 5000}]},
            "task_type": "saas_management",
        })
        
        assert result is not None
        assert "result" in result

    def test_graph_routes_to_access_review(self, it_agent, mock_llm_client):
        """Test graph routes to Access review."""
        graph = it_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "tools_data": {"access_issues": []},
            "task_type": "access_review",
        })
        
        assert result is not None

    def test_graph_routes_to_security_review(self, it_agent, mock_llm_client):
        """Test graph routes to Security review."""
        graph = it_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "tools_data": {"security_issues": []},
            "task_type": "security_review",
        })
        
        assert result is not None

    def test_graph_default_routing(self, it_agent, mock_llm_client):
        """Test graph defaults to SaaS management for unknown types."""
        graph = it_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "tools_data": {},
            "task_type": "unknown_type",
        })
        
        assert result is not None


# =============================================================================
# Test Context Building Helpers
# =============================================================================

class TestITDeskContextBuilding:
    """Test ITDeskAgent context building helpers."""

    def test_build_saas_context_unused(self, it_agent):
        """Test SaaS context with unused tools."""
        tools_data = {
            "tools": [
                {"name": "Slack", "monthly_cost": 5000, "days_since_last_use": 45, "assigned_users": 2},
                {"name": "Zoom", "monthly_cost": 3000, "days_since_last_use": 5, "assigned_users": 10},
            ]
        }
        
        context = it_agent._build_saas_context(tools_data)
        
        assert "Total Tools: 2" in context
        assert "Unused (>30 days): 1" in context
        assert "Total Monthly Cost:" in context

    def test_build_access_context_orphaned(self, it_agent):
        """Test Access context with orphaned accounts."""
        tools_data = {
            "access_issues": [
                {"type": "orphaned", "user_email": "ex@company.com", "tool": "GitHub"},
                {"type": "excessive_permissions", "user_email": "user@company.com", "tool": "AWS"},
            ]
        }
        
        context = it_agent._build_access_context(tools_data)
        
        assert "Total Access Issues: 2" in context
        assert "Orphaned Accounts: 1" in context

    def test_build_security_context(self, it_agent):
        """Test Security context building."""
        tools_data = {
            "security_issues": [
                {"tool": "AWS", "severity": "high", "description": "Public bucket", "affected_users": 5},
            ],
            "tools_without_2fa": [{"name": "AWS"}, {"name": "GitHub"}]
        }
        
        context = it_agent._build_security_context(tools_data)
        
        assert "Total Security Issues: 1" in context
        assert "Tools Without 2FA: 2" in context


# =============================================================================
# Integration Tests (Real LLM)
# =============================================================================

@pytest.mark.skipif(not os.environ.get("AZURE_OPENAI_ENDPOINT"), reason="No Azure OpenAI configured")
class TestITDeskIntegration:
    """Integration tests with real Azure LLM."""

    def test_full_workflow_with_real_llm(self):
        """Test complete IT Desk workflow with real LLM."""
        agent = ITDeskAgent()
        graph = agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "tools_data": {
                "tools": [
                    {"name": "Slack", "monthly_cost": 5000, "days_since_last_use": 45},
                ]
            },
            "task_type": "saas_management",
        })
        
        assert result is not None
        assert "result" in result
        
        it_result = result["result"]
        assert isinstance(it_result, ITRiskAlert)
        assert " and " not in it_result.do_this.lower()
