"""Layer 1: Working Memory — Redis-backed in-flight state."""
from __future__ import annotations
import json, os
from typing import Any

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class WorkingMemory:
    def __init__(self, tenant_id: str, run_id: str):
        self.tenant_id = tenant_id
        self.run_id = run_id
        self.prefix = f"wm:{tenant_id}:{run_id}"
        self._redis = None

    @property
    def redis(self):
        if self._redis is None:
            if not REDIS_AVAILABLE:
                self._redis = _InMemoryFallback()
            else:
                url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
                try:
                    self._redis = redis.from_url(url, decode_responses=True)
                    self._redis.ping()
                except Exception:
                    self._redis = _InMemoryFallback()
        return self._redis

    def set(self, key: str, value: Any, ttl: int = 3600):
        try:
            self.redis.setex(f"{self.prefix}:{key}", ttl, json.dumps(value, default=str))
        except Exception:
            pass

    def get(self, key: str) -> Any | None:
        try:
            val = self.redis.get(f"{self.prefix}:{key}")
            return json.loads(val) if val else None
        except Exception:
            return None

    def increment(self, key: str) -> int:
        try:
            return self.redis.incr(f"{self.prefix}:{key}")
        except Exception:
            return 0

    def clear(self):
        try:
            keys = self.redis.keys(f"{self.prefix}:*")
            if keys:
                self.redis.delete(*keys)
        except Exception:
            pass

    def available(self) -> bool:
        try:
            self.redis.ping()
            return True
        except Exception:
            return False


class _InMemoryFallback:
    def __init__(self):
        self._store = {}

    def setex(self, k, t, v):
        self._store[k] = v

    def get(self, k):
        return self._store.get(k)

    def delete(self, *ks):
        for k in ks:
            self._store.pop(k, None)

    def keys(self, p):
        import fnmatch
        return [k for k in self._store if fnmatch.fnmatch(k, p)]

    def ping(self):
        pass

    def incr(self, k):
        self._store[k] = self._store.get(k, 0) + 1
        return self._store[k]
