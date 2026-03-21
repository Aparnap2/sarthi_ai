"""
Qdrant memory operations.

Real implementations using Qdrant client for semantic memory storage.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
import logging
import os
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
)

logger = logging.getLogger(__name__)

# Qdrant configuration
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = os.environ.get("QDRANT_PORT", "6333")
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "sarthi_memory")
EMBEDDING_DIM = 768  # nomic-embed-text produces 768-dim vectors

# Singleton client
_client: Optional[QdrantClient] = None


def _get_client() -> QdrantClient:
    """Get or create Qdrant client singleton."""
    global _client
    if _client is None:
        _client = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))
        _ensure_collection_exists(_client)
    return _client


def _ensure_collection_exists(client: QdrantClient) -> None:
    """Create collection if it doesn't exist."""
    try:
        client.get_collection(COLLECTION_NAME)
    except Exception:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


def _get_embedding(text: str) -> List[float]:
    """
    Get embedding vector for text using Ollama.

    Args:
        text: Text to embed

    Returns:
        List of floats (768-dim vector)
    """
    from openai import OpenAI

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    embed_model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

    client = OpenAI(base_url=base_url, api_key="ollama")
    response = client.embeddings.create(model=embed_model, input=text)
    return response.data[0].embedding


def _generate_point_id(tenant_id: str, content: str) -> str:
    """Generate deterministic point ID from tenant and content."""
    key = f"{tenant_id}:{content}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def upsert_memory(
    tenant_id: str,
    content: str,
    memory_type: str,
    agent: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Upsert memory to Qdrant.

    Args:
        tenant_id: Tenant who owns this memory
        content: Memory content (text)
        memory_type: Type of memory (finance_anomaly, revenue_event, etc.)
        agent: Agent that created this memory
        metadata: Additional metadata

    Returns:
        Point ID of the upserted memory
    """
    client = _get_client()

    # Generate embedding
    vector = _get_embedding(content)

    # Generate deterministic point ID
    point_id = _generate_point_id(tenant_id, content)

    # Prepare payload
    payload = {
        "tenant_id": tenant_id,
        "content": content,
        "memory_type": memory_type,
        "agent": agent,
        **(metadata or {}),
    }

    # Upsert point
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )

    logger.debug(
        f"Upserted memory: tenant={tenant_id}, type={memory_type}, "
        f"agent={agent}, point_id={point_id}"
    )

    return point_id


def query_memory(
    tenant_id: str,
    query_text: str,
    memory_types: Optional[List[str]] = None,
    top_k: int = 5,
    min_score: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Query memories by semantic similarity.

    Args:
        tenant_id: Tenant ID to filter by
        query_text: Query text for semantic search
        memory_types: Filter by memory types (optional)
        top_k: Max results to return
        min_score: Minimum similarity score threshold

    Returns:
        List of matching memories with content and metadata
    """
    client = _get_client()

    # Generate query embedding
    query_vector = _get_embedding(query_text)

    # Build filter
    filter_conditions = [
        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
    ]

    if memory_types:
        filter_conditions.append(
            FieldCondition(key="memory_type", match=MatchValue(value=memory_types[0]))
        )

    search_filter = Filter(must=filter_conditions) if filter_conditions else None

    # Search using query_points (correct Qdrant API)
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=search_filter,
        limit=top_k,
        score_threshold=min_score,
    )

    # Format results
    memories = []
    for result in results.points:
        if result.payload:
            memories.append(
                {
                    "content": result.payload.get("content", ""),
                    "memory_type": result.payload.get("memory_type", ""),
                    "agent": result.payload.get("agent", ""),
                    "score": result.score,
                    "point_id": result.id,
                }
            )

    logger.debug(
        f"Query memory: tenant={tenant_id}, query={query_text[:50]}..., "
        f"found {len(memories)} results"
    )

    return memories


def search_memory(
    tenant_id: str,
    query: str,
    memory_type: Optional[str] = None,
    limit: int = 5,
) -> list[Dict[str, Any]]:
    """
    Search memories by query.

    Args:
        tenant_id: Tenant ID
        query: Search query
        memory_type: Filter by memory type (optional)
        limit: Max results to return

    Returns:
        List of matching memories
    """
    return query_memory(
        tenant_id=tenant_id,
        query_text=query,
        memory_types=[memory_type] if memory_type else None,
        top_k=limit,
        min_score=0.0,
    )


def delete_memory(tenant_id: str, point_id: str) -> bool:
    """
    Delete a memory by point ID.

    Args:
        tenant_id: Tenant ID (for verification)
        point_id: Point ID to delete

    Returns:
        True if deleted, False otherwise
    """
    client = _get_client()

    # Verify ownership
    try:
        point = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[point_id],
        )
        if not point or point[0].payload.get("tenant_id") != tenant_id:
            return False
    except Exception:
        return False

    # Delete
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=[point_id],
    )

    logger.debug(f"Deleted memory: tenant={tenant_id}, point_id={point_id}")
    return True


def clear_tenant_memory(tenant_id: str) -> int:
    """
    Clear all memory for a tenant.

    Args:
        tenant_id: Tenant ID to clear

    Returns:
        Number of points deleted
    """
    client = _get_client()

    # Get all points for tenant
    all_points = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
        ),
        limit=10000,
    )

    point_ids = [point.id for point in all_points[0]]

    if point_ids:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=point_ids,
        )

    logger.debug(f"Cleared {len(point_ids)} memories for tenant={tenant_id}")
    return len(point_ids)
