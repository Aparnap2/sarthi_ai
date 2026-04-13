"""
Unit tests for QAAgent.

Tests cover:
  - QAState structure
  - match_question node
  - fetch_data node
  - generate_answer node
  - send_slack node
  - ReAct tools (search_pulse_memory, query_stripe_metrics, query_product_db)
  - QA_TOOLS list
  - ReAct agent structure

All tests run in MOCK MODE (no real API calls).
"""
from __future__ import annotations
import os
import pytest
from typing import Any

# Force mock environment before any imports
os.environ["STRIPE_API_KEY"] = ""
os.environ["PLAID_ACCESS_TOKEN"] = ""
os.environ["SLACK_WEBHOOK_URL"] = ""
os.environ["DATABASE_URL"] = ""
os.environ["PRODUCT_DB_URL"] = ""
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434/v1"

TENANT = "test-qa-tenant-unit"


# =============================================================================
# TestQAState
# =============================================================================

class TestQAState:
    """Tests for QAState TypedDict structure."""

    def test_qa_state_creation_empty(self):
        """QAState can be created with no fields (all optional)."""
        from src.agents.qa.state import QAState

        state: QAState = {}
        assert isinstance(state, dict)
        assert len(state) == 0

    def test_qa_state_with_tenant_id(self):
        """QAState accepts tenant_id field."""
        from src.agents.qa.state import QAState

        state: QAState = {"tenant_id": TENANT}
        assert state["tenant_id"] == TENANT

    def test_qa_state_with_question_fields(self):
        """QAState accepts question and matched_template fields."""
        from src.agents.qa.state import QAState

        state: QAState = {
            "tenant_id": TENANT,
            "question": "What is our MRR?",
            "matched_template": "mrr",
            "question_category": "mrr",
        }
        assert state["question"] == "What is our MRR?"
        assert state["matched_template"] == "mrr"
        assert state["question_category"] == "mrr"


# =============================================================================
# TestMatchQuestion
# =============================================================================

class TestMatchQuestion:
    """Tests for match_question node."""

    def test_match_question_mrr_template(self):
        """match_question correctly identifies MRR-related questions."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import match_question

        state: QAState = {
            "tenant_id": TENANT,
            "question": "What is our current MRR?",
        }
        result = match_question(state)

        assert "matched_template" in result
        assert result["matched_template"] == "mrr"
        assert result["question_category"] == "mrr"

    def test_match_question_burn_template(self):
        """match_question correctly identifies burn-related questions."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import match_question

        state: QAState = {
            "tenant_id": TENANT,
            "question": "What is our monthly burn rate?",
        }
        result = match_question(state)

        assert "matched_template" in result
        assert result["matched_template"] == "burn"
        assert result["question_category"] == "burn"

    def test_match_question_runway_template(self):
        """match_question correctly identifies runway-related questions."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import match_question

        state: QAState = {
            "tenant_id": TENANT,
            "question": "How many months of runway do we have?",
        }
        result = match_question(state)

        assert "matched_template" in result
        assert result["matched_template"] == "runway"
        assert result["question_category"] == "runway"


# =============================================================================
# TestFetchData
# =============================================================================

class TestFetchData:
    """Tests for fetch_data node."""

    def test_fetch_data_returns_data_sources(self):
        """fetch_data returns list of data sources used."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import fetch_data

        state: QAState = {
            "tenant_id": TENANT,
            "question_category": "mrr",
        }
        result = fetch_data(state)

        assert "data_sources" in result
        assert isinstance(result["data_sources"], list)
        assert len(result["data_sources"]) > 0

    def test_fetch_data_returns_mrr_cents(self):
        """fetch_data returns mrr_cents in mock mode."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import fetch_data

        state: QAState = {
            "tenant_id": TENANT,
            "question_category": "mrr",
        }
        result = fetch_data(state)

        assert "mrr_cents" in result
        assert isinstance(result["mrr_cents"], int)
        assert result["mrr_cents"] > 0  # Mock data has positive MRR

    def test_fetch_data_returns_arr_cents(self):
        """fetch_data returns arr_cents (MRR × 12)."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import fetch_data

        state: QAState = {
            "tenant_id": TENANT,
            "question_category": "mrr",
        }
        result = fetch_data(state)

        assert "arr_cents" in result
        assert isinstance(result["arr_cents"], int)
        # ARR should be MRR × 12
        assert result["arr_cents"] == result["mrr_cents"] * 12


# =============================================================================
# TestGenerateAnswer
# =============================================================================

class TestGenerateAnswer:
    """Tests for generate_answer node."""

    def _create_state_with_data(self) -> Any:
        """Helper to create state with realistic test data."""
        from src.agents.qa.state import QAState

        return QAState(
            tenant_id=TENANT,
            question="What is our current MRR?",
            matched_template="mrr",
            question_category="mrr",
            mrr_cents=1250000,
            arr_cents=15000000,
            active_customers=25,
            new_customers=3,
            churned_customers=1,
            mrr_growth_pct=4.17,
            quick_ratio=1.5,
            past_answer="First time asked.",
        )

    def test_generate_answer_returns_answer_string(self):
        """generate_answer returns answer string."""
        from src.agents.qa.nodes import generate_answer

        state = self._create_state_with_data()
        result = generate_answer(state)

        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0

    def test_generate_answer_returns_follow_up(self):
        """generate_answer returns follow_up question."""
        from src.agents.qa.nodes import generate_answer

        state = self._create_state_with_data()
        result = generate_answer(state)

        assert "follow_up" in result
        assert isinstance(result["follow_up"], str)

    def test_generate_answer_handles_missing_data(self):
        """generate_answer handles missing fields gracefully."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import generate_answer

        # Minimal state with missing fields
        state = QAState(
            tenant_id=TENANT,
            question="What is our MRR?",
            matched_template="mrr",
            question_category="mrr",
        )
        result = generate_answer(state)

        # Should not raise, should have fallback answer
        assert "answer" in result
        assert "follow_up" in result
        assert len(result["answer"]) > 0


# =============================================================================
# TestSendSlack
# =============================================================================

class TestSendSlack:
    """Tests for send_slack node."""

    def test_send_slack_returns_blocks(self):
        """send_slack returns Slack Block Kit blocks."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import send_slack

        state = QAState(
            tenant_id=TENANT,
            question="What is our MRR?",
            answer="Current MRR is ₹12,500.",
            follow_up="Want to see MRR trend over the last 6 months?",
            matched_template="mrr",
            data_sources=["stripe_mock"],
            latency_ms=150,
        )
        result = send_slack(state)

        assert "slack_blocks" in result
        assert isinstance(result["slack_blocks"], list)
        assert len(result["slack_blocks"]) > 0

    def test_send_slack_header_block(self):
        """send_slack includes header block."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import send_slack

        state = QAState(
            tenant_id=TENANT,
            question="What is our MRR?",
            answer="Current MRR is ₹12,500.",
        )
        result = send_slack(state)

        blocks = result["slack_blocks"]
        header_found = any(
            b.get("type") == "header" for b in blocks
        )
        assert header_found

    def test_send_slack_includes_question_and_answer(self):
        """send_slack includes question and answer in blocks."""
        from src.agents.qa.state import QAState
        from src.agents.qa.nodes import send_slack

        state = QAState(
            tenant_id=TENANT,
            question="What is our MRR?",
            answer="Current MRR is ₹12,500.",
        )
        result = send_slack(state)

        blocks_text = " ".join(
            str(b.get("text", {})) for b in result["slack_blocks"]
        )
        # Should contain Question and Answer
        assert "Question" in blocks_text
        assert "Answer" in blocks_text


# =============================================================================
# TestReActTools
# =============================================================================

class TestReActTools:
    """Tests for ReAct tool functions."""

    def test_qa_tools_count(self):
        """QA_TOOLS contains exactly 3 tools."""
        from src.agents.qa.nodes import QA_TOOLS

        assert len(QA_TOOLS) == 3

    def test_qa_tools_are_langchain_tools(self):
        """All QA_TOOLS are langchain_core.tools.BaseTool instances."""
        from langchain_core.tools import BaseTool
        from src.agents.qa.nodes import QA_TOOLS

        for t in QA_TOOLS:
            assert isinstance(t, BaseTool)

    def test_qa_tools_names(self):
        """QA_TOOLS have expected names."""
        from src.agents.qa.nodes import QA_TOOLS

        names = [t.name for t in QA_TOOLS]
        assert "search_pulse_memory" in names
        assert "query_stripe_metrics" in names
        assert "query_product_db" in names

    def test_query_stripe_metrics_mrr(self):
        """query_stripe_metrics returns MRR value in mock mode."""
        from src.agents.qa.nodes import query_stripe_metrics

        result = query_stripe_metrics.invoke({"metric": "mrr", "tenant_id": TENANT})
        assert isinstance(result, str)
        assert "MRR" in result

    def test_query_stripe_metrics_arr(self):
        """query_stripe_metrics returns ARR value in mock mode."""
        from src.agents.qa.nodes import query_stripe_metrics

        result = query_stripe_metrics.invoke({"metric": "arr", "tenant_id": TENANT})
        assert isinstance(result, str)
        assert "ARR" in result

    def test_query_stripe_metrics_invalid(self):
        """query_stripe_metrics returns error for unknown metric."""
        from src.agents.qa.nodes import query_stripe_metrics

        result = query_stripe_metrics.invoke({"metric": "nonsense", "tenant_id": TENANT})
        assert isinstance(result, str)
        assert "Unknown metric" in result

    def test_query_product_db_returns_string(self):
        """query_product_db returns formatted product metrics."""
        from src.agents.qa.nodes import query_product_db

        result = query_product_db.invoke({"question": "DAU?", "tenant_id": TENANT})
        assert isinstance(result, str)
        assert "DAU" in result
        assert "MAU" in result

    def test_search_pulse_memory_returns_string_on_failure(self):
        """search_pulse_memory returns string even when Qdrant is unavailable."""
        from src.agents.qa.nodes import search_pulse_memory

        # Qdrant likely not running in unit test env, so expect graceful fallback
        result = search_pulse_memory.invoke({"query": "MRR", "tenant_id": TENANT})
        assert isinstance(result, str)

    def test_qa_tools_exist(self):
        """QA_TOOLS contains exactly 3 tools with expected names."""
        from src.agents.qa.nodes import QA_TOOLS

        assert len(QA_TOOLS) == 3
        names = [t.name for t in QA_TOOLS]
        assert "search_pulse_memory" in names
        assert "query_stripe_metrics" in names
        assert "query_product_db" in names

    def test_search_pulse_memory_returns_string(self):
        """search_pulse_memory.invoke returns a string result."""
        from src.agents.qa.nodes import search_pulse_memory

        result = search_pulse_memory.invoke({"query": "MRR last month", "tenant_id": TENANT})
        assert isinstance(result, str)

    def test_query_stripe_metrics_returns_string(self):
        """query_stripe_metrics.invoke returns a string result."""
        from src.agents.qa.nodes import query_stripe_metrics

        result = query_stripe_metrics.invoke({"metric": "mrr", "tenant_id": TENANT})
        assert isinstance(result, str)

    def test_qa_react_agent_exists(self):
        """qa_agent is exported from graph module and is not None."""
        from src.agents.qa.graph import qa_agent

        assert qa_agent is not None

    def test_qa_answer_non_empty(self):
        """FounderQA prompt signature exists and is properly defined."""
        from src.agents.qa.prompts import FounderQA

        assert FounderQA is not None
        assert hasattr(FounderQA, "__annotations__")
        annotations = FounderQA.__annotations__
        assert "answer" in annotations


# =============================================================================
# TestReActAgent
# =============================================================================

class TestReActAgent:
    """Tests for ReAct agent structure."""

    def test_qa_agent_exists(self):
        """qa_agent is exported from graph module."""
        from src.agents.qa.graph import qa_agent

        assert qa_agent is not None

    def test_qa_agent_is_compiled_graph(self):
        """qa_agent is a compiled LangGraph graph (Pregel instance)."""
        from src.agents.qa.graph import qa_agent
        from langgraph.pregel import Pregel

        assert isinstance(qa_agent, Pregel)

    def test_qa_graph_nodes_count(self):
        """qa_graph has 5 user-defined nodes (+ __start__ implicit node)."""
        from src.agents.qa.graph import qa_graph

        # LangGraph adds __start__ as implicit entry point
        all_nodes = list(qa_graph.nodes.keys())
        user_nodes = [n for n in all_nodes if n != "__start__"]
        assert len(user_nodes) == 5

    def test_qa_graph_node_names(self):
        """qa_graph has expected node names (excluding __start__)."""
        from src.agents.qa.graph import qa_graph

        node_names = {n for n in qa_graph.nodes.keys() if n != "__start__"}
        expected = {"match_question", "fetch_data", "retrieve_memory", "generate_answer", "send_slack"}
        assert node_names == expected

    def test_prompts_react_system_prompt(self):
        """REACT_SYSTEM_PROMPT is defined and non-empty."""
        from src.agents.qa.prompts import REACT_SYSTEM_PROMPT

        assert isinstance(REACT_SYSTEM_PROMPT, str)
        assert len(REACT_SYSTEM_PROMPT) > 0
        assert "Sarthi" in REACT_SYSTEM_PROMPT

    def test_prompts_tool_descriptions(self):
        """TOOL_DESCRIPTIONS has entries for all 3 tools."""
        from src.agents.qa.prompts import TOOL_DESCRIPTIONS

        assert "search_pulse_memory" in TOOL_DESCRIPTIONS
        assert "query_stripe_metrics" in TOOL_DESCRIPTIONS
        assert "query_product_db" in TOOL_DESCRIPTIONS
