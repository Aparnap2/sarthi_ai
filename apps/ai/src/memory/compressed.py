"""Layer 5: Compressed Long-Term Memory — Qdrant founder_patterns."""
from __future__ import annotations
import os, uuid, requests
from typing import Any


class CompressedMemory:
    def __init__(self):
        self.collection = "founder_patterns"
        self.base = f"http://{os.environ.get('QDRANT_HOST','localhost')}:{os.environ.get('QDRANT_PORT','6333')}"

    def available(self) -> bool:
        try:
            r = requests.get(f"{self.base}/collections/{self.collection}", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def write(self, tenant_id: str, patterns: dict):
        if not self.available():
            return
        point_id = str(uuid.uuid4())
        payload = {
            "tenant_id": tenant_id, "event_type": "compressed_pattern",
            "weight": 1.0, "confidence": 0.85, "compressed": True, **patterns
        }
        try:
            requests.put(
                f"{self.base}/collections/{self.collection}/points/{point_id}",
                json={"id": point_id, "vector": [0.0] * 768, "payload": payload},
                timeout=15
            )
        except Exception:
            pass

    def search(self, tenant_id: str, top_k: int = 3) -> list[dict]:
        if not self.available():
            return []
        try:
            r = requests.post(
                f"{self.base}/collections/{self.collection}/points/search",
                json={
                    "vector": [0.0] * 768,
                    "filter": {"must": [{"key": "tenant_id", "match": {"value": tenant_id}}]},
                    "limit": top_k, "with_payload": True
                },
                timeout=15
            )
            return [{"score": x["score"], **x["payload"]} for x in r.json().get("result", [])]
        except Exception:
            return []
