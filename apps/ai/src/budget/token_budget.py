"""Token budget manager using PostgreSQL atomic UPDATE — replaces Redis INCRBY."""

import os
import asyncpg


class TokenBudgetManager:
    """Manages per-task LLM token budgets using PostgreSQL atomic UPDATE."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool
        self.default_limit = int(os.getenv("TOKEN_BUDGET_PER_TASK", "50000"))

    async def acquire(self, task_id: str, tokens: int) -> bool:
        """Atomically add tokens to the task budget. Returns True if within limit."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO token_budgets (task_id, tokens_used, tokens_limit)
                VALUES ($1, $2, $3)
                ON CONFLICT (task_id) DO UPDATE
                    SET tokens_used = token_budgets.tokens_used + $2
                RETURNING tokens_used, tokens_limit
                """,
                task_id,
                tokens,
                self.default_limit,
            )
            return row["tokens_used"] <= row["tokens_limit"]

    async def get_remaining(self, task_id: str) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT tokens_limit - tokens_used AS remaining
                   FROM token_budgets WHERE task_id = $1""",
                task_id,
            )
            return row["remaining"] if row else self.default_limit

    async def cleanup(self, task_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM token_budgets WHERE task_id = $1", task_id)
