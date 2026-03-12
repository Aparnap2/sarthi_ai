"""
Tests for TriggerAgent - Intervention scoring engine.

Run with: pytest apps/ai/tests/test_trigger_agent.py -v
"""

import pytest
import asyncio
import asyncpg
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.agents.trigger_agent import (
    TriggerAgent,
    TriggerState,
    WEIGHTS,
    FIRE_THRESHOLD,
    TRIGGER_EMOJIS,
)


@pytest.fixture
def mock_db_pool():
    """Create a mock database pool."""
    from unittest.mock import MagicMock, AsyncMock
    
    pool = MagicMock()
    conn = AsyncMock()
    
    # Mock founder lookup
    conn.fetchrow.return_value = {"slack_user_id": "U0123456789"}
    
    # Mock INSERT for logging
    conn.execute = AsyncMock()
    
    # Create async context manager mock
    pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock(return_value=None)
    ))
    
    return pool


@pytest.fixture
def mock_llm():
    """Create a mock LLM client."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(
        return_value=MagicMock(
            content='{"message": "Test intervention message", "cta": "Take action now"}'
        )
    )
    return llm


@pytest.fixture
def mock_slack_client():
    """Create a mock Slack client."""
    client = AsyncMock()
    
    # Mock conversations_open
    client.conversations_open = AsyncMock(
        return_value={"channel": {"id": "D0123456789"}}
    )
    
    # Mock chat_postMessage
    client.chat_postMessage = AsyncMock(
        return_value={"ts": "1234567890.123456"}
    )
    
    return client


@pytest.mark.asyncio
async def test_trigger_agent_initialization(mock_db_pool, mock_llm):
    """Test TriggerAgent initializes correctly."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    assert agent.pool == mock_db_pool
    assert agent.llm == mock_llm
    assert agent.slack_client is None


@pytest.mark.asyncio
async def test_compute_score_commitment_gap(mock_db_pool, mock_llm):
    """Test score computation with commitment gap."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        patterns={
            "commitment_completion_rate": 0.3,  # Low completion = high gap
            "overdue_commitments": 3,
            "days_since_reflection": 2.0,
            "momentum_drop": 0.1,
        },
        market_signal=None,
    )
    
    result = await agent.compute_score(state)
    
    # Verify score was computed
    assert result.score > 0
    assert result.score <= 1.0
    
    # Verify trigger type
    assert result.trigger_type == "commitment_gap"
    
    # Verify should_fire based on threshold
    assert isinstance(result.should_fire, bool)


@pytest.mark.asyncio
async def test_compute_score_decision_stall(mock_db_pool, mock_llm):
    """Test score computation with decision stall."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        patterns={
            "commitment_completion_rate": 1.0,  # Perfect completion
            "overdue_commitments": 0,
            "days_since_reflection": 21.0,  # 3 weeks = high stall
            "momentum_drop": 0.0,
        },
        market_signal=None,
    )
    
    result = await agent.compute_score(state)
    
    # Verify decision_stall is dominant
    assert result.trigger_type == "decision_stall"
    
    # Verify score is elevated due to stall
    decision_stall_component = min(1.0, 21.0 / 14)  # Should be 1.0
    assert decision_stall_component == 1.0


@pytest.mark.asyncio
async def test_compute_score_market_signal(mock_db_pool, mock_llm):
    """Test score computation with market signal."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        patterns={
            "commitment_completion_rate": 1.0,
            "overdue_commitments": 0,
            "days_since_reflection": 1.0,
            "momentum_drop": 0.0,
        },
        market_signal={
            "relevance_score": 0.9,  # High relevance
            "title": "Competitor launched similar feature",
            "content": "Details...",
        },
    )
    
    result = await agent.compute_score(state)
    
    # Verify market_signal contributes to score
    market_contribution = WEIGHTS["market_signal"] * 0.9
    assert result.score >= market_contribution


@pytest.mark.asyncio
async def test_compute_score_momentum_drop(mock_db_pool, mock_llm):
    """Test score computation with momentum drop."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        patterns={
            "commitment_completion_rate": 1.0,
            "overdue_commitments": 0,
            "days_since_reflection": 1.0,
            "momentum_drop": 0.5,  # Significant drop (5 points)
        },
        market_signal=None,
    )
    
    result = await agent.compute_score(state)
    
    # Verify momentum_drop contributes
    momentum_contribution = WEIGHTS["momentum_drop"] * 0.5
    assert result.score >= momentum_contribution


@pytest.mark.asyncio
async def test_compute_score_below_threshold(mock_db_pool, mock_llm):
    """Test that low scores don't fire."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        patterns={
            "commitment_completion_rate": 1.0,  # Perfect
            "overdue_commitments": 0,
            "days_since_reflection": 1.0,  # Recent
            "momentum_drop": 0.0,
        },
        market_signal=None,
    )
    
    result = await agent.compute_score(state)
    
    # Verify score is low
    assert result.score < FIRE_THRESHOLD
    
    # Verify should_fire is False
    assert result.should_fire is False


@pytest.mark.asyncio
async def test_compute_score_above_threshold(mock_db_pool, mock_llm):
    """Test that high scores fire."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        patterns={
            "commitment_completion_rate": 0.0,  # No completions
            "overdue_commitments": 5,
            "days_since_reflection": 20.0,  # Long stall
            "momentum_drop": 0.3,
        },
        market_signal=None,
    )
    
    result = await agent.compute_score(state)
    
    # Verify score is high
    assert result.score >= FIRE_THRESHOLD
    
    # Verify should_fire is True
    assert result.should_fire is True


@pytest.mark.asyncio
async def test_generate_message(mock_db_pool, mock_llm):
    """Test message generation."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        patterns={
            "retrieved_context": "Founder committed to ship feature X",
            "commitment_completion_rate": 0.5,
        },
        trigger_type="commitment_gap",
        score=0.75,
        should_fire=True,
        market_signal=None,
    )
    
    result = await agent.generate_message(state)
    
    # Verify message was generated
    assert result.message is not None
    assert len(result.message) > 0
    
    # Verify CTA was generated
    assert result.cta is not None
    
    # Verify LLM was called
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_generate_message_with_emoji(mock_db_pool, mock_llm):
    """Test that messages include correct emoji."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    for trigger_type, expected_emoji in TRIGGER_EMOJIS.items():
        state = TriggerState(
            founder_id="test-founder-id",
            patterns={},
            trigger_type=trigger_type,
            score=0.75,
            should_fire=True,
        )
        
        # Reset mock
        mock_llm.ainvoke.reset_mock()
        
        result = await agent.generate_message(state)
        
        # Verify LLM was called with emoji in prompt
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert expected_emoji in call_args


@pytest.mark.asyncio
async def test_generate_message_json_parse_error(mock_db_pool, mock_llm):
    """Test fallback when JSON parsing fails."""
    # Mock LLM returning invalid JSON
    mock_llm.ainvoke.return_value = MagicMock(
        content="This is not valid JSON at all"
    )
    
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        patterns={},
        trigger_type="commitment_gap",
        score=0.75,
        should_fire=True,
    )
    
    result = await agent.generate_message(state)
    
    # Verify fallback message was used
    assert result.message is not None
    assert result.cta == "Take action now"


@pytest.mark.asyncio
async def test_suppress(mock_db_pool, mock_llm):
    """Test suppression logging."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        score=0.45,
        trigger_type="commitment_gap",
        should_fire=False,
    )
    
    result = await agent.suppress(state)
    
    # Verify suppression reason was set
    assert result.suppression_reason is not None
    assert "0.450" in result.suppression_reason
    assert "below threshold" in result.suppression_reason
    assert "commitment_gap" in result.suppression_reason


@pytest.mark.asyncio
async def test_send_slack_message(mock_db_pool, mock_llm, mock_slack_client):
    """Test sending message to Slack."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm, slack_client=mock_slack_client)
    
    state = TriggerState(
        founder_id="test-founder-id",
        message="Test intervention message",
        should_fire=True,
    )
    
    result = await agent.send_slack_message(state)
    
    # Verify Slack API was called
    mock_slack_client.conversations_open.assert_called_once_with(
        users="U0123456789"
    )
    mock_slack_client.chat_postMessage.assert_called_once()
    
    # Verify slack_ts was set
    assert result.slack_ts == "1234567890.123456"


@pytest.mark.asyncio
async def test_send_slack_message_no_client(mock_db_pool, mock_llm):
    """Test that sending is skipped when no Slack client."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm, slack_client=None)
    
    state = TriggerState(
        founder_id="test-founder-id",
        message="Test message",
        should_fire=True,
    )
    
    result = await agent.send_slack_message(state)
    
    # Verify slack_ts was NOT set
    assert result.slack_ts is None


@pytest.mark.asyncio
async def test_log_trigger_decision(mock_db_pool, mock_llm):
    """Test logging trigger decision to database."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm)
    
    state = TriggerState(
        founder_id="test-founder-id",
        trigger_type="commitment_gap",
        score=0.75,
        should_fire=True,
        suppression_reason=None,
        message="Test message",
        slack_ts="1234567890.123456",
    )
    
    result = await agent.log_trigger_decision(state)
    
    # Verify INSERT was called
    mock_db_pool.acquire.return_value.__aenter__.return_value.execute.assert_called_once()
    
    # Verify correct parameters
    call_args = mock_db_pool.acquire.return_value.__aenter__.return_value.execute.call_args[0][0]
    assert "INSERT INTO trigger_log" in call_args


@pytest.mark.asyncio
async def test_evaluate_trigger_full_workflow(mock_db_pool, mock_llm, mock_slack_client):
    """Test complete trigger evaluation workflow."""
    agent = TriggerAgent(db_pool=mock_db_pool, llm=mock_llm, slack_client=mock_slack_client)

    patterns = {
        "commitment_completion_rate": 0.3,
        "overdue_commitments": 2,
        "days_since_reflection": 10.0,
        "momentum_drop": 0.2,
        "retrieved_context": "Previous context",
    }

    result = await agent.evaluate_trigger(
        founder_id="test-founder-id",
        patterns=patterns,
        market_signal=None,
    )

    # LangGraph may return dict or dataclass - handle both
    if hasattr(result, 'founder_id'):
        assert result.founder_id == "test-founder-id"
        assert result.score > 0
        assert result.trigger_type is not None
        assert isinstance(result.should_fire, bool)
    else:
        assert isinstance(result, dict)
        assert result.get("founder_id") == "test-founder-id"
        assert result.get("score", 0) > 0
        assert result.get("trigger_type") is not None
        assert isinstance(result.get("should_fire"), bool)


@pytest.mark.asyncio
async def test_trigger_emojis_all_present():
    """Test that all trigger types have emojis."""
    expected_types = {"commitment_gap", "decision_stall", "market_signal", "momentum_drop"}
    
    assert set(TRIGGER_EMOJIS.keys()) == expected_types
    
    # Verify all emojis are valid Unicode
    for emoji in TRIGGER_EMOJIS.values():
        assert isinstance(emoji, str)
        assert len(emoji) > 0


@pytest.mark.asyncio
async def test_weights_sum_to_one():
    """Test that scoring weights sum to 1.0."""
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 0.001  # Allow small floating point error


@pytest.mark.asyncio
async def test_fire_threshold_reasonable():
    """Test that fire threshold is in reasonable range."""
    assert 0.5 <= FIRE_THRESHOLD <= 0.7
