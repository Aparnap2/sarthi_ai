"""Context store for state persistence using PostgreSQL JSONB."""

import json
from typing import Any, Dict, Optional
import asyncpg


class ContextStore:
    """Stores agent findings in PostgreSQL JSONB — replaces Redis."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def write(self, task_id: str, agent_role: str, key: str, value: Any) -> None:
        """Write agent findings atomically."""
        findings = {key: value}
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_context (task_id, agent_role, findings, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (task_id, agent_role) DO UPDATE
                    SET findings = agent_context.findings || EXCLUDED.findings,
                        updated_at = NOW()
                """,
                task_id,
                agent_role,
                json.dumps(findings),
            )

    async def read(
        self, task_id: str, agent_role: Optional[str] = None, key: Optional[str] = None
    ) -> Any:
        """Read data from the context store."""
        async with self.pool.acquire() as conn:
            if agent_role:
                row = await conn.fetchrow(
                    """SELECT findings FROM agent_context
                       WHERE task_id = $1 AND agent_role = $2""",
                    task_id,
                    agent_role,
                )
                if not row:
                    return None
                findings = row["findings"]
                return findings.get(key) if key else findings
            else:
                rows = await conn.fetch(
                    """SELECT agent_role, findings FROM agent_context
                       WHERE task_id = $1""",
                    task_id,
                )
                return {row["agent_role"]: row["findings"] for row in rows}

    async def clear(self, task_id: Optional[str] = None) -> None:
        async with self.pool.acquire() as conn:
            if task_id:
                await conn.execute(
                    "DELETE FROM agent_context WHERE task_id = $1", task_id
                )
            else:
                await conn.execute("DELETE FROM agent_context")
