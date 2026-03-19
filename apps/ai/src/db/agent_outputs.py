"""
Agent outputs database operations.

Provides functions to persist and query agent outputs to/from PostgreSQL.
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


def insert_agent_output(
    tenant_id: str,
    agent_name: str,
    headline: str = "",
    urgency: str = "low",
    hitl_sent: bool = False,
    output_json: Optional[Dict[str, Any]] = None,
    output_type: Optional[str] = None,
) -> str:
    """
    Insert agent output to database.

    Args:
        tenant_id: Tenant identifier
        agent_name: Name of the agent
        headline: One-line alert message
        urgency: Urgency level (critical, high, warn, low)
        hitl_sent: Whether HITL (Telegram) was sent
        output_json: Additional structured data
        output_type: Type of output (optional)

    Returns:
        ID of inserted record
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    record_id = str(uuid.uuid4())
    output_json = output_json or {}

    cur.execute(
        """
        INSERT INTO agent_outputs (
            id, tenant_id, agent_name, output_type, headline,
            urgency, hitl_sent, output_json, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            record_id,
            tenant_id,
            agent_name,
            output_type,
            headline,
            urgency,
            hitl_sent,
            psycopg2.extras.Json(output_json),
            datetime.now(timezone.utc),
        ),
    )

    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return result["id"] if result else record_id


def get_recent_outputs(
    tenant_id: str,
    agent_name: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Get recent agent outputs for a tenant.

    Args:
        tenant_id: Tenant identifier
        agent_name: Filter by agent name (optional)
        limit: Max results to return

    Returns:
        List of agent output records
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if agent_name:
        cur.execute(
            """
            SELECT * FROM agent_outputs
            WHERE tenant_id = %s AND agent_name = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (tenant_id, agent_name, limit),
        )
    else:
        cur.execute(
            """
            SELECT * FROM agent_outputs
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


def get_output_by_id(output_id: str) -> Optional[Dict[str, Any]]:
    """
    Get agent output by ID.

    Args:
        output_id: Record ID

    Returns:
        Agent output record or None
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT * FROM agent_outputs WHERE id = %s",
        (output_id,),
    )

    result = cur.fetchone()
    cur.close()
    conn.close()

    return dict(result) if result else None


def delete_outputs_for_tenant(tenant_id: str) -> int:
    """
    Delete all agent outputs for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Number of records deleted
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM agent_outputs WHERE tenant_id = %s",
        (tenant_id,),
    )

    deleted_count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    return deleted_count
