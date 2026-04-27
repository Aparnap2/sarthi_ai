"""Session Context retrieval for Sarthi V3.0.

This module provides the get_session_context function to retrieve
recent messages for a tenant.

PRD Reference: Section 795-798
"""

import logging
import os
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://sarthi:sarthi@localhost:5432/sarthi")


@dataclass
class SessionMessage:
    """Represents a session message for context retrieval."""

    id: str
    tenant_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: datetime


def _get_db_connection():
    """Get a database connection with graceful fallback."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.warning(f"Database connection failed: {e}. Using fallback mode.")
        return None


from dataclasses import dataclass
from datetime import datetime


def get_session_context(tenant_id: str, limit: int = 10) -> List[dict]:
    """Retrieve the most recent N messages for a tenant.

    This function fetches recent conversation messages that can be used
    to provide context for agent responses.

    Args:
        tenant_id: The tenant identifier
        limit: Maximum number of messages to retrieve (default: 10)

    Returns:
        List of message dictionaries with keys: id, tenant_id, role, content, timestamp

    Example:
        >>> messages = get_session_context("tenant-123", limit=5)
        >>> for msg in messages:
        >>>     print(f"{msg['role']}: {msg['content'][:50]}...")
    """
    conn = _get_db_connection()
    if conn is None:
        logger.warning(f"[FALLBACK] Returning empty context for tenant {tenant_id}")
        return _get_fallback_context(tenant_id, limit)

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, tenant_id, role, content, timestamp
            FROM session_messages
            WHERE tenant_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """

        cursor.execute(query, (tenant_id, limit))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert to list of dicts and reverse to get chronological order
        messages = [dict(row) for row in rows]
        messages.reverse()

        logger.debug(f"Retrieved {len(messages)} messages for tenant {tenant_id}")
        return messages

    except Exception as e:
        logger.error(f"Error fetching session context for tenant {tenant_id}: {e}")
        return _get_fallback_context(tenant_id, limit)


def _get_fallback_context(tenant_id: str, limit: int) -> List[dict]:
    """Get fallback context when database is unavailable.

    Args:
        tenant_id: The tenant identifier
        limit: Number of messages to return

    Returns:
        Empty list (fallback response)
    """
    logger.debug(f"[FALLBACK] No session context available for tenant {tenant_id}")
    return []