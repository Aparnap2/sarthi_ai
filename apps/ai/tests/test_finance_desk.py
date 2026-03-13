"""
Tests for Finance Desk Agent — Sarthi v4.2 Phase 3.

Tests cover:
- Agent initialization
- All 4 capabilities (CFO, Bookkeeper, AR/AP, Payroll)
- Pydantic validation (jargon detection, single action, headline length)
- LangGraph workflow completion
- Real Azure LLM integration

Run with: pytest apps/ai/tests/test_finance_desk.py -v
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from src.schemas.desk_results import FinanceTaskResult, HitlRisk
from src.agents.finance_desk import FinanceDeskAgent, FinanceDeskState, get_finance_desk_agent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with realistic responses."""
    client = MagicMock()
    
    # Mock chat completions for CFO analysis
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(
            content='{"headline": "Revenue up 20% this month", "what_is_true": "Revenue increased from ₹5,00,000 to ₹6,00,000. Expenses remained stable at ₹3,00,000.", "do_this": "Review pricing for top 5 customers", "urgency": "this_week", "rupee_impact": 100000, "hitl_risk": "low", "is_good_news": true}'
        ))]
    )
    
    return client


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    qdrant = MagicMock()
    mock_collection = MagicMock()
    type(mock_collection).name = property(lambda self: "sarthi_founder_memory")
    qdrant.get_collections.return_value = MagicMock(collections=[mock_collection])
    return qdrant


@pytest.fixture
def finance_agent(mock_llm_client, mock_qdrant_client):
    """Create FinanceDeskAgent with mocked dependencies."""
    with patch('src.agents.finance_desk.get_llm_client', return_value=mock_llm_client):
        with patch('src.agents.finance_desk.get_chat_model', return_value='gpt-4'):
            agent = FinanceDeskAgent()
            mock_llm_client.reset_mock(return_value=False, side_effect=False)
            return agent


# =============================================================================
# Test Pydantic Schema Validation
# =============================================================================

class TestFinanceTaskResultValidation:
    """Test FinanceTaskResult Pydantic validation."""

    def test_valid_result_creation(self):
        """Test creating a valid FinanceTaskResult."""
        result = FinanceTaskResult(
            task_type="ar_reminder",
            headline="Customer payment due in 3 days",
            what_is_true="Invoice #123 for ₹50,000 is due on March 15",
            do_this="Send payment reminder email to customer",
            urgency="today",
            rupee_impact=50000,
            hitl_risk=HitlRisk.LOW,
            is_good_news=False
        )
        
        assert result.task_type == "ar_reminder"
        assert result.headline == "Customer payment due in 3 days"
        assert result.rupee_impact == 50000
        assert result.hitl_risk == HitlRisk.LOW

    def test_jargon_detection_ebitda(self):
        """Test that EBITDA jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FinanceTaskResult(
                task_type="reconciliation",
                headline="EBITDA improved this quarter",
                what_is_true="EBITDA increased by 15%",
                do_this="Review financial statements",
                urgency="this_week",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "Jargon" in str(exc_info.value)
        assert "EBITDA" in str(exc_info.value)

    def test_jargon_detection_dso(self):
        """Test that DSO jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FinanceTaskResult(
                task_type="ar_reminder",
                headline="DSO needs improvement",
                what_is_true="Days Sales Outstanding is too high",
                do_this="Review collection process",
                urgency="this_week",
                hitl_risk=HitlRisk.MEDIUM
            )
        
        assert "Jargon" in str(exc_info.value)

    def test_jargon_detection_working_capital(self):
        """Test that working capital jargon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FinanceTaskResult(
                task_type="reconciliation",
                headline="Working capital optimization needed",
                what_is_true="Working capital is tied up in inventory",
                do_this="Review inventory levels",
                urgency="this_month",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "Jargon" in str(exc_info.value)
        assert "working capital" in str(exc_info.value).lower()

    def test_headline_max_words(self):
        """Test that headline is limited to 10 words."""
        with pytest.raises(ValidationError) as exc_info:
            FinanceTaskResult(
                task_type="ar_reminder",
                headline="This is a very long headline that exceeds the maximum word count limit of ten words",
                what_is_true="Invoice is due",
                do_this="Send reminder",
                urgency="today",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "10 words" in str(exc_info.value)

    def test_single_action_validation_with_and(self):
        """Test that do_this with 'and' is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FinanceTaskResult(
                task_type="ar_reminder",
                headline="Payment due soon",
                what_is_true="Invoice is due in 3 days",
                do_this="Send email reminder and call the customer",
                urgency="today",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "ONE action" in str(exc_info.value)
        assert "and" in str(exc_info.value)

    def test_single_action_validation_with_semicolon(self):
        """Test that do_this with semicolon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FinanceTaskResult(
                task_type="ap_due",
                headline="Vendor payment due",
                what_is_true="Payment due to vendor",
                do_this="Process payment; notify vendor",
                urgency="today",
                hitl_risk=HitlRisk.LOW
            )
        
        assert "ONE action" in str(exc_info.value)

    def test_single_action_valid(self):
        """Test that single action passes validation."""
        result = FinanceTaskResult(
            task_type="ar_reminder",
            headline="Payment due soon",
            what_is_true="Invoice is due in 3 days",
            do_this="Send payment reminder email",
            urgency="today",
            hitl_risk=HitlRisk.LOW
        )
        
        assert result.do_this == "Send payment reminder email"

    def test_good_news_flag(self):
        """Test is_good_news flag defaults to False."""
        result = FinanceTaskResult(
            task_type="reconciliation",
            headline="Revenue milestone achieved",
            what_is_true="Crossed ₹10 lakh monthly revenue",
            do_this="Celebrate with team",
            urgency="today",
            rupee_impact=1000000,
            hitl_risk=HitlRisk.LOW,
            is_good_news=True
        )
        
        assert result.is_good_news is True


# =============================================================================
# Test FinanceDeskAgent Initialization
# =============================================================================

class TestFinanceDeskAgentInitialization:
    """Test FinanceDeskAgent initialization."""

    def test_agent_initializes_without_params(self, mock_llm_client):
        """Test FinanceDeskAgent initializes without parameters."""
        with patch('src.agents.finance_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.finance_desk.get_chat_model', return_value='gpt-4'):
                agent = FinanceDeskAgent()
                
                assert agent.client is not None
                assert agent.model == 'gpt-4'

    def test_get_finance_desk_agent_singleton(self, mock_llm_client):
        """Test get_finance_desk_agent returns singleton."""
        with patch('src.agents.finance_desk.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.finance_desk.get_chat_model', return_value='gpt-4'):
                # Clear global instance first
                import src.agents.finance_desk as fd
                fd._finance_desk_agent = None
                
                agent1 = get_finance_desk_agent()
                agent2 = get_finance_desk_agent()
                
                assert agent1 is agent2


# =============================================================================
# Test FinanceDeskAgent Capabilities
# =============================================================================

class TestFinanceDeskAgentCapabilities:
    """Test FinanceDeskAgent capabilities."""

    def test_analyze_cfo(self, finance_agent, mock_llm_client):
        """Test CFO capability analyzes financial data."""
        state = FinanceDeskState(
            founder_id="test-founder-id",
            bank_data={"balance": 500000, "monthly_inflow": 200000, "monthly_outflow": 150000},
            accounting_data={"revenue": 600000, "expenses": 300000},
            task_type="cfo",
            result=None
        )
        
        result_state = finance_agent.analyze_cfo(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], FinanceTaskResult)
        assert result_state["result"].task_type == "reconciliation"
        
        # Verify LLM was called
        mock_llm_client.chat.completions.create.assert_called_once()

    def test_analyze_bookkeeper(self, finance_agent, mock_llm_client):
        """Test Bookkeeper capability categorizes transactions."""
        state = FinanceDeskState(
            founder_id="test-founder-id",
            bank_data={
                "balance": 500000,
                "transactions": [
                    {"amount": 5000, "description": "Office supplies", "category": None},
                    {"amount": 10000, "description": "Software subscription", "category": None},
                ]
            },
            accounting_data={},
            task_type="bookkeeper",
            result=None
        )
        
        result_state = finance_agent.analyze_bookkeeper(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], FinanceTaskResult)

    def test_analyze_ar_ap(self, finance_agent, mock_llm_client):
        """Test AR/AP Clerk capability identifies overdue invoices."""
        state = FinanceDeskState(
            founder_id="test-founder-id",
            bank_data={},
            accounting_data={
                "invoices": [
                    {"number": "INV-001", "amount": 50000, "status": "overdue", "days_overdue": 15},
                    {"number": "INV-002", "amount": 30000, "status": "pending"},
                ]
            },
            task_type="ar_ap",
            result=None
        )
        
        result_state = finance_agent.analyze_ar_ap(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], FinanceTaskResult)
        assert result_state["result"].task_type in ["ar_reminder", "ap_due"]

    def test_analyze_payroll(self, finance_agent, mock_llm_client):
        """Test Payroll Clerk capability prepares payroll data."""
        state = FinanceDeskState(
            founder_id="test-founder-id",
            bank_data={},
            accounting_data={
                "employees": [{"name": "John"}, {"name": "Jane"}],
                "next_payroll_date": "2024-03-31",
                "total_payroll": 150000
            },
            task_type="payroll",
            result=None
        )
        
        result_state = finance_agent.analyze_payroll(state)
        
        assert result_state["result"] is not None
        assert isinstance(result_state["result"], FinanceTaskResult)
        assert result_state["result"].task_type == "payroll_prep"


# =============================================================================
# Test LangGraph Workflow
# =============================================================================

class TestFinanceDeskGraph:
    """Test FinanceDesk LangGraph workflow."""

    def test_create_graph_returns_compiled_graph(self, finance_agent):
        """Test create_graph returns a compiled StateGraph."""
        graph = finance_agent.create_graph()
        
        assert graph is not None
        # Graph should have invoke method
        assert hasattr(graph, 'invoke')

    def test_graph_routes_to_cfo(self, finance_agent, mock_llm_client):
        """Test graph routes to CFO capability."""
        graph = finance_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "bank_data": {"balance": 500000},
            "accounting_data": {"revenue": 600000},
            "task_type": "cfo",
        })
        
        assert result is not None
        assert "result" in result

    def test_graph_routes_to_bookkeeper(self, finance_agent, mock_llm_client):
        """Test graph routes to Bookkeeper capability."""
        graph = finance_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "bank_data": {
                "balance": 500000,
                "transactions": [{"amount": 5000, "description": "Supplies", "category": None}]
            },
            "accounting_data": {},
            "task_type": "bookkeeper",
        })
        
        assert result is not None

    def test_graph_routes_to_ar_ap(self, finance_agent, mock_llm_client):
        """Test graph routes to AR/AP capability."""
        graph = finance_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "bank_data": {},
            "accounting_data": {
                "invoices": [{"number": "INV-001", "amount": 50000, "status": "overdue"}]
            },
            "task_type": "ar_ap",
        })
        
        assert result is not None

    def test_graph_routes_to_payroll(self, finance_agent, mock_llm_client):
        """Test graph routes to Payroll capability."""
        graph = finance_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "bank_data": {},
            "accounting_data": {
                "employees": [{"name": "John"}],
                "next_payroll_date": "2024-03-31",
                "total_payroll": 150000
            },
            "task_type": "payroll",
        })
        
        assert result is not None

    def test_graph_default_routing(self, finance_agent, mock_llm_client):
        """Test graph defaults to CFO for unknown task types."""
        graph = finance_agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "bank_data": {"balance": 500000},
            "accounting_data": {},
            "task_type": "unknown_type",
        })
        
        assert result is not None
        assert "result" in result


# =============================================================================
# Test Context Building Helpers
# =============================================================================

class TestFinanceDeskContextBuilding:
    """Test FinanceDeskAgent context building helpers."""

    def test_build_cfo_context(self, finance_agent):
        """Test CFO context building."""
        bank_data = {"balance": 500000, "monthly_inflow": 200000, "monthly_outflow": 150000}
        accounting_data = {"revenue": 600000, "expenses": 300000}
        
        context = finance_agent._build_cfo_context(bank_data, accounting_data)
        
        assert "Bank Balance" in context
        assert "₹500,000" in context
        assert "Monthly Revenue" in context

    def test_build_bookkeeper_context_with_uncategorized(self, finance_agent):
        """Test Bookkeeper context with uncategorized transactions."""
        bank_data = {
            "transactions": [
                {"amount": 5000, "description": "Office supplies", "category": None},
                {"amount": 10000, "description": "Software", "category": "Technology"},
            ]
        }
        
        context = finance_agent._build_bookkeeper_context(bank_data)
        
        assert "Total Transactions: 2" in context
        assert "Uncategorized: 1" in context

    def test_build_ar_ap_context_with_overdue(self, finance_agent):
        """Test AR/AP context with overdue invoices."""
        accounting_data = {
            "invoices": [
                {"number": "INV-001", "amount": 50000, "status": "overdue", "days_overdue": 15},
            ]
        }
        
        context = finance_agent._build_ar_ap_context(accounting_data)
        
        assert "Overdue: 1" in context
        assert "INV-001" in context

    def test_build_payroll_context(self, finance_agent):
        """Test Payroll context building."""
        accounting_data = {
            "employees": [{"name": "John"}, {"name": "Jane"}],
            "next_payroll_date": "2024-03-31",
            "total_payroll": 150000
        }
        
        context = finance_agent._build_payroll_context(accounting_data)
        
        assert "Employees: 2" in context
        assert "₹150,000" in context


# =============================================================================
# Integration Tests (Real LLM)
# =============================================================================

@pytest.mark.skipif(not os.environ.get("AZURE_OPENAI_ENDPOINT"), reason="No Azure OpenAI configured")
class TestFinanceDeskIntegration:
    """Integration tests with real Azure LLM."""

    def test_full_workflow_with_real_llm(self):
        """Test complete Finance Desk workflow with real LLM."""
        agent = FinanceDeskAgent()
        graph = agent.create_graph()
        
        result = graph.invoke({
            "founder_id": "test-founder-id",
            "bank_data": {
                "balance": 500000,
                "monthly_inflow": 200000,
                "monthly_outflow": 150000,
            },
            "accounting_data": {
                "revenue": 600000,
                "expenses": 300000,
            },
            "task_type": "cfo",
        })
        
        assert result is not None
        assert "result" in result
        assert result["result"] is not None
        
        # Verify result structure
        finance_result = result["result"]
        assert isinstance(finance_result, FinanceTaskResult)
        assert len(finance_result.headline.split()) <= 10
        assert " and " not in finance_result.do_this.lower()
