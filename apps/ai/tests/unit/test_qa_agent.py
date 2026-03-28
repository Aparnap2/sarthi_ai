"""
Unit tests for QAAgent.

Tests cover:
  - QAState structure
  - match_question node
  - fetch_data node
  - generate_answer node
  - send_slack node

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
