"""
Tests for MemoryAgent - Founder memory management with Qdrant.

Run with: pytest apps/ai/tests/test_memory_agent.py -v
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue, MatchAny

from src.agents.memory_agent import (
    MemoryAgent,
    MemoryWrite,
    MemoryQuery,
    FounderMemoryState,
)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"archetype": "builder", "patterns": ["consistent"], "commitment_completion_rate": 0.8, "customer_frequency": "weekly"}'))]
    )
    return client


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    qdrant = MagicMock()
    
    # Create a proper mock collection with string name
    mock_collection = MagicMock()
    type(mock_collection).name = property(lambda self: "sarthi_founder_memory")
    
    # Mock collection check
    qdrant.get_collections.return_value = MagicMock(
        collections=[mock_collection]
    )
    
    # Mock collection creation
    qdrant.create_collection = MagicMock()
    
    # Mock upsert
    qdrant.upsert = MagicMock()
    
    # Mock search
    qdrant.search.return_value = [
        MagicMock(
            score=0.85,
            payload={
                "founder_id": "test-founder-id",
                "content": "Test reflection content",
                "memory_type": "reflection",
                "confidence": 0.9,
                "source": "system",
                "metadata": {}
            }
        )
    ]
    
    return qdrant


@pytest.fixture
def memory_agent(mock_llm_client, mock_qdrant_client):
    """Create MemoryAgent with mocked dependencies."""
    with patch('src.agents.memory_agent.get_llm_client', return_value=mock_llm_client):
        with patch('src.agents.memory_agent.QdrantClient', return_value=mock_qdrant_client):
            agent = MemoryAgent()
            # Clear call history after initialization but preserve return values
            mock_qdrant_client.reset_mock(return_value=False, side_effect=False)
            mock_llm_client.reset_mock(return_value=False, side_effect=False)
            return agent


class TestMemoryAgentInitialization:
    """Test MemoryAgent initialization."""

    def test_memory_agent_initializes_without_params(self, mock_llm_client, mock_qdrant_client):
        """Test MemoryAgent initializes without any parameters."""
        with patch('src.agents.memory_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.memory_agent.QdrantClient', return_value=mock_qdrant_client):
                agent = MemoryAgent()
                
                assert agent.client is not None
                assert agent.qdrant is not None
                assert agent.COLLECTION_NAME == "sarthi_founder_memory"

    def test_ensure_collection_called_on_init(self, mock_llm_client, mock_qdrant_client):
        """Test _ensure_collection is called during initialization."""
        with patch('src.agents.memory_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.memory_agent.QdrantClient', return_value=mock_qdrant_client):
                MemoryAgent()
                
                mock_qdrant_client.get_collections.assert_called_once()


class TestMemoryAgentWrite:
    """Test MemoryAgent write functionality."""

    def test_write_memory_success(self, memory_agent, mock_qdrant_client):
        """Test writing a memory to Qdrant."""
        memory = MemoryWrite(
            founder_id="test-founder-id",
            content="This week I shipped the MVP and got user feedback.",
            memory_type="reflection",
            confidence=0.9,
            source="user"
        )
        
        point_id = memory_agent.write(memory)
        
        # Verify upsert was called
        mock_qdrant_client.upsert.assert_called_once()
        assert point_id is not None

    def test_write_memory_with_metadata(self, memory_agent, mock_qdrant_client):
        """Test writing a memory with custom metadata."""
        memory = MemoryWrite(
            founder_id="test-founder-id",
            content="Completed customer discovery interviews.",
            memory_type="milestone",
            confidence=1.0,
            source="system",
            metadata={"interview_count": 5, "week": 10}
        )
        
        memory_agent.write(memory)
        
        # Verify upsert was called with correct payload
        call_args = mock_qdrant_client.upsert.call_args
        points = call_args[1]["points"]
        assert len(points) == 1
        payload = points[0].payload
        assert payload["founder_id"] == "test-founder-id"
        assert payload["memory_type"] == "milestone"
        assert payload["metadata"]["interview_count"] == 5

    def test_write_memory_conflict_detection(self, memory_agent, mock_qdrant_client):
        """Test that conflict detection is called during write."""
        memory = MemoryWrite(
            founder_id="test-founder-id",
            content="Test memory",
            memory_type="reflection"
        )
        
        # Mock _find_conflicts to return conflicts
        with patch.object(memory_agent, '_find_conflicts', return_value=["conflict-1"]):
            memory_agent.write(memory)
            
            # Verify upsert was called with conflict info
            call_args = mock_qdrant_client.upsert.call_args
            points = call_args[1]["points"]
            payload = points[0].payload
            assert payload["has_conflicts"] is True
            assert "conflict-1" in payload["conflict_ids"]


class TestMemoryAgentQuery:
    """Test MemoryAgent query functionality."""

    def test_query_memory_success(self, memory_agent, mock_qdrant_client):
        """Test querying memories from Qdrant."""
        query = MemoryQuery(
            founder_id="test-founder-id",
            query_text="customer feedback",
            memory_types=["reflection"],
            top_k=5,
            min_confidence=0.5
        )
        
        results = memory_agent.query(query)
        
        # Verify search was called
        mock_qdrant_client.search.assert_called_once()
        assert len(results) == 1
        assert results[0]["content"] == "Test reflection content"
        assert results[0]["score"] == 0.85

    def test_query_with_multiple_memory_types(self, memory_agent, mock_qdrant_client):
        """Test querying with multiple memory types."""
        query = MemoryQuery(
            founder_id="test-founder-id",
            query_text="weekly progress",
            memory_types=["reflection", "commitment", "milestone"],
            top_k=10
        )
        
        memory_agent.query(query)
        
        # Verify filter includes all memory types
        call_args = mock_qdrant_client.search.call_args
        filter_obj = call_args[1]["query_filter"]
        assert len(filter_obj.must) == 2  # founder_id + memory_types


class TestMemoryAgentEmbed:
    """Test MemoryAgent embedding functionality."""

    def test_embed_generates_vector(self, memory_agent, mock_llm_client):
        """Test that _embed generates a vector."""
        text = "This is a test reflection."
        
        vector = memory_agent._embed(text)
        
        # Verify embeddings.create was called
        mock_llm_client.embeddings.create.assert_called_once()
        assert len(vector) == 1536
        assert vector == [0.1] * 1536

    def test_embed_uses_correct_model(self, memory_agent, mock_llm_client):
        """Test that _embed uses the configured embedding model."""
        with patch.dict(os.environ, {"EMBEDDING_MODEL": "text-embedding-3-small"}):
            memory_agent._embed("test text")
            
            call_args = mock_llm_client.embeddings.create.call_args
            assert call_args[1]["model"] == "text-embedding-3-small"


class TestMemoryAgentPatterns:
    """Test MemoryAgent pattern detection functionality."""

    def test_detect_patterns_returns_structure(self, memory_agent, mock_llm_client, mock_qdrant_client):
        """Test detect_patterns returns expected structure."""
        # Mock the LLM client and model calls inside detect_patterns
        with patch('src.agents.memory_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.memory_agent.get_model', return_value='gpt-4'):
                patterns = memory_agent.detect_patterns("test-founder-id")

                assert "archetype" in patterns
                assert "patterns" in patterns
                assert "commitment_completion_rate" in patterns
                assert "customer_frequency" in patterns

    def test_detect_patterns_queries_memories(self, memory_agent, mock_llm_client, mock_qdrant_client):
        """Test detect_patterns queries relevant memories."""
        with patch('src.agents.memory_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.memory_agent.get_model', return_value='gpt-4'):
                memory_agent.detect_patterns("test-founder-id")

                # Verify search was called for reflections
                assert mock_qdrant_client.search.called


class TestMemoryAgentConflicts:
    """Test MemoryAgent conflict detection."""

    def test_find_conflicts_stub_returns_empty(self, memory_agent):
        """Test _find_conflicts returns empty list (v1 stub)."""
        memory = MemoryWrite(
            founder_id="test-founder-id",
            content="Test memory",
            memory_type="reflection"
        )
        
        conflicts = memory_agent._find_conflicts(memory)
        
        assert conflicts == []


class TestMemoryAgentCollection:
    """Test MemoryAgent collection management."""

    def test_ensure_collection_skips_if_exists(self, memory_agent):
        """Test _ensure_collection doesn't create if collection exists."""
        # Configure the agent's qdrant mock directly with proper name property
        mock_collection = MagicMock()
        type(mock_collection).name = property(lambda self: "sarthi_founder_memory")
        memory_agent.qdrant.get_collections.return_value = MagicMock(
            collections=[mock_collection]
        )
        
        memory_agent._ensure_collection()

        # create_collection should NOT be called
        memory_agent.qdrant.create_collection.assert_not_called()

    def test_ensure_collection_creates_if_missing(self, mock_llm_client, mock_qdrant_client):
        """Test _ensure_collection creates collection if missing."""
        # Mock empty collections
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        
        with patch('src.agents.memory_agent.get_llm_client', return_value=mock_llm_client):
            with patch('src.agents.memory_agent.QdrantClient', return_value=mock_qdrant_client):
                MemoryAgent()
                
                # create_collection should be called
                mock_qdrant_client.create_collection.assert_called_once()
                call_args = mock_qdrant_client.create_collection.call_args
                assert call_args[1]["collection_name"] == "sarthi_founder_memory"


class TestMemoryWriteDataclass:
    """Test MemoryWrite dataclass."""

    def test_memory_write_default_values(self):
        """Test MemoryWrite has correct default values."""
        memory = MemoryWrite(
            founder_id="test-id",
            content="Test content",
            memory_type="reflection"
        )
        
        assert memory.confidence == 1.0
        assert memory.source == "system"
        assert memory.metadata is None


class TestMemoryQueryDataclass:
    """Test MemoryQuery dataclass."""

    def test_memory_query_default_values(self):
        """Test MemoryQuery has correct default values."""
        query = MemoryQuery(
            founder_id="test-id",
            query_text="test query"
        )
        
        assert query.memory_types is None
        assert query.top_k == 10
        assert query.min_confidence == 0.5
