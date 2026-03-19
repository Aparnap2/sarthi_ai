"""
HITL (Human-in-the-Loop) actions database operations.

Provides functions to persist and query HITL actions to/from PostgreSQL.
These are used for Telegram callback tracking.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
import uuid


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://iterateswarm:iterateswarm@localhost:5433/iterateswarm")


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def insert_hitl_action(
    tenant_id: str,
    agent_name: str,
    message_sent: str,
    buttons: Optional[List[str]] = None,
    founder_response: Optional[str] = None,
) -> str:
    """
    Insert HITL action to database.

    Args:
        tenant_id: Tenant identifier
        agent_name: Name of the agent that triggered this
        message_sent: Message text sent to founder
        buttons: List of callback buttons (optional)
        founder_response: Founder's response (optional, set later)

    Returns:
        ID of inserted record
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    record_id = str(uuid.uuid4())
    buttons_json = buttons or []

    cur.execute(
        """
        INSERT INTO hitl_actions (
            id, tenant_id, agent_name, message_sent,
            buttons, founder_response, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            record_id,
            tenant_id,
            agent_name,
            message_sent,
            psycopg2.extras.Json(buttons_json),
            founder_response,
            datetime.now(timezone.utc),
        ),
    )

    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return result["id"] if result else record_id


def update_hitl_response(
    action_id: str,
    founder_response: str,
) -> bool:
    """
    Update HITL action with founder's response.

    Args:
        action_id: Record ID to update
        founder_response: Founder's response text

    Returns:
        True if updated successfully
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE hitl_actions
        SET founder_response = %s, responded_at = %s
        WHERE id = %s
        """,
        (founder_response, datetime.now(timezone.utc), action_id),
    )

    updated = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()

    return updated


def get_pending_hitl_actions(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Get pending HITL actions (no founder response yet).

    Args:
        tenant_id: Tenant identifier

    Returns:
        List of pending HITL action records
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT * FROM hitl_actions
        WHERE tenant_id = %s AND founder_response IS NULL
        ORDER BY created_at DESC
        """,
        (tenant_id,),
    )

    results = cur.fetchall()
    cur.close()
    conn.close()

    return [dict(row) for row in results]


def get_hitl_action_by_id(action_id: str) -> Optional[Dict[str, Any]]:
    """
    Get HITL action by ID.

    Args:
        action_id: Record ID

    Returns:
        HITL action record or None
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT * FROM hitl_actions WHERE id = %s",
        (action_id,),
    )

    result = cur.fetchone()
    cur.close()
    conn.close()

    return dict(result) if result else None


def get_recent_hitl_actions(
    tenant_id: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Get recent HITL actions for a tenant.

    Args:
        tenant_id: Tenant identifier
        limit: Max results to return

    Returns:
        List of HITL action records
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT * FROM hitl_actions
        WHERE tenant_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (tenant_id, limit),
    )

    results = cur.fetchall()
    cur.close()
    conn.close()

    return [dict(row) for row in results]


def delete_hitl_actions_for_tenant(tenant_id: str) -> int:
    """
    Delete all HITL actions for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Number of records deleted
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM hitl_actions WHERE tenant_id = %s",
        (tenant_id,),
    )

    deleted_count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    return deleted_count
