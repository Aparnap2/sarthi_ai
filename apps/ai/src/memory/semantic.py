"""Layer 3: Semantic Memory — Kuzu embedded graph DB."""
from __future__ import annotations
import os
from typing import Any

try:
    import kuzu
    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False


class SemanticMemory:
    def __init__(self, db_path: str = "/tmp/sarthi_kuzu"):
        self.db_path = db_path
        self._db = None
        self._conn = None

    def available(self) -> bool:
        if not KUZU_AVAILABLE:
            return False
        try:
            if self._conn is None:
                self._db = kuzu.Database(self.db_path)
                self._conn = kuzu.Connection(self._db)
                self._conn.execute(
                    "CREATE NODE TABLE IF NOT EXISTS Founder("
                    "tenant_id STRING, archetype STRING, stage STRING, "
                    "confidence DOUBLE, PRIMARY KEY(tenant_id))"
                )
                self._conn.execute(
                    "CREATE NODE TABLE IF NOT EXISTS Anomaly("
                    "id STRING, type STRING, severity STRING, "
                    "timestamp STRING, PRIMARY KEY(id))"
                )
                self._conn.execute(
                    "CREATE REL TABLE IF NOT EXISTS CAUSED("
                    "FROM Anomaly TO Anomaly, confidence DOUBLE)"
                )
            return True
        except Exception:
            return False

    def write_belief(self, tenant_id: str, topic: str, value: str, confidence: float):
        if not self.available():
            return
        try:
            self._conn.execute(
                "INSERT OR UPDATE Founder(tenant_id, $archetype, $stage, $confidence) "
                "WHERE tenant_id=$tid",
                {"tid": tenant_id, "archetype": topic, "stage": value, "confidence": confidence}
            )
        except Exception:
            pass

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        if not self.available():
            return []
        try:
            result = self._conn.execute(cypher, params or {})
            return [dict(row) for row in result]
        except Exception:
            return []
