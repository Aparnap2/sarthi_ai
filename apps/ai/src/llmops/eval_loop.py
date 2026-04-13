"""Weekly eval scoring for guardian quality."""
from __future__ import annotations
import os

try:
    import psycopg2
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False


class EvalLoop:
    def __init__(self):
        self.dsn = os.environ.get("DATABASE_URL", os.environ.get("POSTGRES_DSN", ""))

    def available(self) -> bool:
        return PG_AVAILABLE and bool(self.dsn)

    def record_score(self, tenant_id: str, agent_type: str,
                     guardian_score: float, accuracy_score: float,
                     tone_score: float, action_score: float):
        if not self.available():
            return
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO eval_scores(tenant_id,agent_type,guardian_score,accuracy_score,tone_score,action_score) VALUES(%s,%s,%s,%s,%s,%s)",
                        (tenant_id, agent_type, guardian_score, accuracy_score, tone_score, action_score))
                conn.commit()
        except Exception:
            pass

    def needs_reoptimization(self, tenant_id: str, agent_type: str) -> bool:
        if not self.available():
            return False
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT AVG(guardian_score),AVG(accuracy_score),AVG(tone_score),AVG(action_score) FROM eval_scores WHERE tenant_id=%s AND agent_type=%s",
                        (tenant_id, agent_type))
                    row = cur.fetchone()
                    if row and all(v is not None for v in row):
                        return (sum(row) / 4) < 0.6
            return False
        except Exception:
            return False
