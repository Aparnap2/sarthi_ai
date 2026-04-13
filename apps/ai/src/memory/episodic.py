"""Layer 2: Episodic Memory — Qdrant event storage with weight decay."""
from __future__ import annotations
import os, uuid, requests
from datetime import datetime, timezone
from typing import Any


def embed_text(text: str) -> list[float]:
    base = os.environ.get("OLLAMA_LOCAL_BASE_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    r = requests.post(f"{base}/api/embeddings", json={"model": model, "prompt": text}, timeout=15)
    r.raise_for_status()
    return r.json()["embedding"]


class EpisodicMemory:
    def __init__(self, collection: str):
        self.collection = collection
        self.base = f"http://{os.environ.get('QDRANT_HOST','localhost')}:{os.environ.get('QDRANT_PORT','6333')}"

    def available(self) -> bool:
        try:
            r = requests.get(f"{self.base}/collections/{self.collection}", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def write(self, tenant_id: str, event_type: str, content: str, **extra: Any) -> str:
        point_id = str(uuid.uuid4())
        vector = embed_text(content[:500])
        payload = {
            "tenant_id": tenant_id, "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "weight": 1.0, "confidence": extra.pop("confidence", 0.8),
            "related_ids": extra.pop("related_ids", []),
            "caused_by": extra.pop("caused_by", None),
            "compressed": extra.pop("compressed", False),
            "content": content, **extra,
        }
        r = requests.put(
            f"{self.base}/collections/{self.collection}/points/{point_id}",
            json={"id": point_id, "vector": vector, "payload": payload}, timeout=15
        )
        r.raise_for_status()
        return point_id

    def search(self, tenant_id: str, query: str, top_k: int = 5,
               event_type: str | None = None) -> list[dict]:
        vector = embed_text(query)
        must = [{"key": "tenant_id", "match": {"value": tenant_id}}]
        if event_type:
            must.append({"key": "event_type", "match": {"value": event_type}})
        r = requests.post(
            f"{self.base}/collections/{self.collection}/points/search",
            json={"vector": vector, "filter": {"must": must},
                  "limit": top_k, "with_payload": True}, timeout=15
        )
        r.raise_for_status()
        return [{"score": x["score"], **x["payload"]} for x in r.json().get("result", [])]
