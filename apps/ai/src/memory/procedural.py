"""Layer 4: Procedural Memory — PostgreSQL DSPy program storage."""
from __future__ import annotations
import os, json
from typing import Any

try:
    import psycopg2
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False


class ProceduralMemory:
    def __init__(self):
        self.dsn = os.environ.get("POSTGRES_DSN", os.environ.get("DATABASE_URL", ""))

    def available(self) -> bool:
        if not PG_AVAILABLE or not self.dsn:
            return False
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "CREATE TABLE IF NOT EXISTS dspy_programs("
                        "id UUID PRIMARY KEY DEFAULT gen_random_uuid(), "
                        "tenant_id UUID, agent_name TEXT, signature_name TEXT, "
                        "program_json JSONB, eval_score FLOAT, "
                        "optimized_at TIMESTAMPTZ DEFAULT NOW(), active BOOLEAN DEFAULT TRUE)"
                    )
                conn.commit()
            return True
        except Exception:
            return False

    def save(self, tenant_id: str, agent: str, signature: str,
             program: dict, score: float):
        if not self.available():
            return
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO dspy_programs(tenant_id,agent_name,signature_name,program_json,eval_score) "
                        "VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (tenant_id, agent, signature, json.dumps(program), score)
                    )
                conn.commit()
        except Exception:
            pass

    def load(self, tenant_id: str, agent: str, signature: str) -> dict | None:
        if not self.available():
            return None
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT program_json FROM dspy_programs "
                        "WHERE tenant_id=%s AND agent_name=%s AND signature_name=%s "
                        "AND active=TRUE ORDER BY optimized_at DESC LIMIT 1",
                        (tenant_id, agent, signature)
                    )
                    row = cur.fetchone()
                    return json.loads(row[0]) if row else None
        except Exception:
            return None
