"""
Tests for MemoryAgent - Founder memory management with Qdrant.

Run with: pytest apps/ai/tests/test_memory_agent.py -v
"""

import pytest
import asyncio
import asyncpg
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.memory_agent import MemoryAgent, FounderMemoryState


@pytest.fixture
def mock_db_pool():
    """Create a mock database pool."""
    from unittest.mock import AsyncMock, MagicMock
    from contextlib import asynccontextmanager
    
    pool = MagicMock()
    conn = AsyncMock()
    
    # Mock commitment stats
    conn.fetchrow.side_effect = [
        # First call: commitment_stats
        {"completion_rate": 0.75, "overdue_count": 1},
        # Second call: last_activity
        {"days_since_last_reflection": 5.0},
    ]
    
    # Mock energy trend
    conn.fetch.return_value = [
        {"energy_score": 8},
        {"energy_score": 7},
        {"energy_score": 6},
    ]
    
    # Create async context manager mock
    async def acquire_ctx():
        return conn
    
    pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock(return_value=None)
    ))
    
    return pool


@pytest.fixture
def mock_llm():
    """Create a mock LLM client."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="Test response"))
    return llm


@pytest.fixture
def mock_qdrant():
    """Create a mock Qdrant service."""
    qdrant = MagicMock()
    qdrant.client = AsyncMock()
    qdrant.get_embedding = AsyncMock(return_value=[0.1] * 768)
    
    # Mock collection check
    qdrant.client.get_collections.return_value = MagicMock(
        collections=[MagicMock(name="existing_collection")]
    )
    
    # Mock collection creation
    qdrant.client.create_collection = AsyncMock()
    
    # Mock upsert
    qdrant.client.upsert = AsyncMock()
    
    # Mock search
    qdrant.client.search = AsyncMock(return_value=[
        MagicMock(
            score=0.85,
            payload={
                "text": "Test reflection",
                "week_start": "2024-01-01",
                "founder_id": "test-founder-id",
            }
        )
    ])
    
    return qdrant


@pytest.mark.asyncio
async def test_memory_agent_initialization(mock_db_pool, mock_llm, mock_qdrant):
    """Test MemoryAgent initializes correctly."""
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)
    
    assert agent.pool == mock_db_pool
    assert agent.llm == mock_llm
    assert agent.qdrant == mock_qdrant
    assert agent.collection == "founder_memory"


@pytest.mark.asyncio
async def test_embed_and_store_with_reflection(mock_db_pool, mock_llm, mock_qdrant):
    """Test embedding and storing a new reflection."""
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)
    
    state = FounderMemoryState(
        founder_id="test-founder-id",
        new_reflection="This week I shipped the MVP and got user feedback.",
        week_start="2024-01-15",
        shipped="MVP launch",
        blocked="Need more user feedback",
        energy_score=8,
        raw_text="This week I shipped the MVP and got user feedback.",
    )
    
    result = await agent.embed_and_store(state)
    
    # Verify embedding was called
    mock_qdrant.get_embedding.assert_called_once()
    
    # Verify upsert was called
    mock_qdrant.client.upsert.assert_called_once()
    
    # Verify embedding_id was set
    assert result.embedding_id is not None
    assert result.embedding_id.startswith("test-founder-id_")


@pytest.mark.asyncio
async def test_embed_and_store_without_reflection(mock_db_pool, mock_llm, mock_qdrant):
    """Test that no embedding occurs when there's no new reflection."""
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)
    
    state = FounderMemoryState(
        founder_id="test-founder-id",
        new_reflection=None,
    )
    
    result = await agent.embed_and_store(state)
    
    # Verify embedding was NOT called
    mock_qdrant.get_embedding.assert_not_called()
    mock_qdrant.client.upsert.assert_not_called()
    
    # Verify state unchanged
    assert result.embedding_id is None


@pytest.mark.asyncio
async def test_retrieve_relevant_context(mock_db_pool, mock_llm, mock_qdrant):
    """Test retrieving relevant context from Qdrant."""
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)
    
    state = FounderMemoryState(
        founder_id="test-founder-id",
    )
    
    result = await agent.retrieve_relevant_context(state)
    
    # Verify search was called with founder filter
    mock_qdrant.client.search.assert_called_once()
    
    # Verify context was extracted
    assert result.retrieved_context is not None
    assert "[2024-01-01]" in result.retrieved_context
    assert "Test reflection" in result.retrieved_context


@pytest.mark.asyncio
async def test_compute_behavioral_patterns(mock_db_pool, mock_llm, mock_qdrant):
    """Test computing behavioral patterns from database."""
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)
    
    state = FounderMemoryState(
        founder_id="test-founder-id",
        retrieved_context="Previous context",
    )
    
    result = await agent.compute_behavioral_patterns(state)
    
    # Verify patterns were computed
    assert result.patterns is not None
    assert "commitment_completion_rate" in result.patterns
    assert "overdue_commitments" in result.patterns
    assert "days_since_reflection" in result.patterns
    assert "momentum_drop" in result.patterns
    
    # Verify values
    assert result.patterns["commitment_completion_rate"] == 0.75
    assert result.patterns["overdue_commitments"] == 1
    assert result.patterns["days_since_reflection"] == 5.0
    assert result.patterns["momentum_drop"] > 0  # (8-6)/10 = 0.2


@pytest.mark.asyncio
async def test_compute_behavioral_patterns_no_data(mock_db_pool, mock_llm, mock_qdrant):
    """Test computing patterns when no data exists."""
    # Mock empty results
    conn = AsyncMock()
    conn.fetchrow.side_effect = [
        {"completion_rate": None, "overdue_count": None},
        {"days_since_last_reflection": None},
    ]
    conn.fetch.return_value = []
    
    mock_db_pool.acquire.return_value.__aenter__.return_value = conn
    
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)
    
    state = FounderMemoryState(
        founder_id="test-founder-id",
    )
    
    result = await agent.compute_behavioral_patterns(state)
    
    # Verify defaults
    assert result.patterns["commitment_completion_rate"] == 0.0
    assert result.patterns["overdue_commitments"] == 0
    assert result.patterns["days_since_reflection"] == 0.0
    assert result.patterns["momentum_drop"] == 0


@pytest.mark.asyncio
async def test_store_reflection_in_db(mock_db_pool, mock_llm, mock_qdrant):
    """Test storing reflection in PostgreSQL."""
    conn = AsyncMock()
    conn.fetchrow.return_value = {"id": "reflection-uuid"}
    mock_db_pool.acquire.return_value.__aenter__.return_value = conn

    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)

    state = FounderMemoryState(
        founder_id="test-founder-id",
        new_reflection="Test reflection",
        week_start="2024-01-15",
        shipped="Test shipped",
        blocked="Test blocked",
        energy_score=7,
        raw_text="Test reflection",
        embedding_id="test-embedding-id",
    )

    result = await agent.store_reflection_in_db(state)

    # Verify INSERT was called
    conn.fetchrow.assert_called_once()

    # Verify embedding_id was passed (7th positional arg, index 6)
    call_args = conn.fetchrow.call_args[0]
    # call_args[0] = (sql_string, founder_id, week_start, shipped, blocked, energy_score, raw_text, embedding_id)
    assert call_args[7] == "test-embedding-id"  # embedding_id parameter


@pytest.mark.asyncio
async def test_process_reflection_full_workflow(mock_db_pool, mock_llm, mock_qdrant):
    """Test complete reflection processing workflow."""
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)

    # Mock all database calls
    conn = AsyncMock()
    # fetchrow is called 3 times in order: store_in_db (1), compute_patterns (2)
    conn.fetchrow.side_effect = [
        {"id": "reflection-uuid"},  # store_reflection_in_db
        {"completion_rate": 0.8, "overdue_count": 0},  # compute_behavioral_patterns
        {"days_since_last_reflection": 3.0},  # compute_behavioral_patterns
    ]
    conn.fetch.return_value = [
        {"energy_score": 8},
        {"energy_score": 8},
    ]
    mock_db_pool.acquire.return_value.__aenter__.return_value = conn

    result = await agent.process_reflection(
        founder_id="test-founder-id",
        reflection_text="This week I made great progress!",
        week_start="2024-01-15",
        shipped="Feature X",
        blocked=None,
        energy_score=9,
    )

    # LangGraph may return dict or dataclass - handle both
    if hasattr(result, 'founder_id'):
        assert result.founder_id == "test-founder-id"
        assert result.patterns is not None
        assert result.embedding_id is not None
    else:
        assert isinstance(result, dict)
        assert result.get("founder_id") == "test-founder-id"
        assert result.get("patterns") is not None
        assert result.get("embedding_id") is not None


@pytest.mark.asyncio
async def test_get_founder_context_without_new_reflection(mock_db_pool, mock_llm, mock_qdrant):
    """Test getting context without storing a new reflection."""
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)

    result = await agent.get_founder_context(founder_id="test-founder-id")

    # LangGraph may return dict or dataclass - handle both
    if hasattr(result, 'retrieved_context'):
        assert result.retrieved_context is not None
        assert result.patterns is not None
    else:
        assert isinstance(result, dict)
        assert result.get("retrieved_context") is not None
        assert result.get("patterns") is not None


@pytest.mark.asyncio
async def test_ensure_collection_creates_if_missing(mock_db_pool, mock_llm, mock_qdrant):
    """Test that collection is created if it doesn't exist."""
    # Mock empty collections
    mock_qdrant.client.get_collections.return_value = MagicMock(collections=[])
    
    agent = MemoryAgent(db_pool=mock_db_pool, llm=mock_llm, qdrant_service=mock_qdrant)
    await agent._ensure_collection()
    
    # Verify collection was created
    mock_qdrant.client.create_collection.assert_called_once()
    assert mock_qdrant.client.create_collection.call_args[1]["collection_name"] == "founder_memory"
