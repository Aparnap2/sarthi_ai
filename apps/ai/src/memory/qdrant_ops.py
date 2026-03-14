"""
Qdrant memory operations.

Stub implementations for TDD. Replace with real Qdrant calls when ready.
"""
from __future__ import annotations
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def upsert_memory(
    founder_id: str,
    content: str,
    memory_type: str,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Upsert memory to Qdrant.

    Args:
        founder_id: Founder who owns this memory
        content: Memory content (text)
        memory_type: Type of memory (transaction, revenue_event, bank_statement, etc.)
        source: Source system (telegram, razorpay, bank_statement, etc.)
        metadata: Additional metadata
    """
    # Stub for TDD - replace with real Qdrant upsert
    logger.debug(
        f"Upsert memory: founder={founder_id}, type={memory_type}, "
        f"content={content[:50]}..."
    )


def search_memory(
    founder_id: str,
    query: str,
    memory_type: Optional[str] = None,
    limit: int = 5,
) -> list[Dict[str, Any]]:
    """
    Search memories by query.

    Args:
        founder_id: Founder ID
        query: Search query
        memory_type: Filter by memory type (optional)
        limit: Max results to return

    Returns:
        List of matching memories
    """
    # Stub for TDD
    logger.debug(f"Search memory: founder={founder_id}, query={query[:50]}...")
    return []
