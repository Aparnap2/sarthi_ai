"""Tests for WorkingMemory (Layer 1: Redis/in-memory)."""
import pytest
from src.memory.working import WorkingMemory, _InMemoryFallback, REDIS_AVAILABLE


class TestWorkingMemory:
    def test_set_and_get(self):
        wm = WorkingMemory("tenant-a", "run-1")
        wm.set("data", {"mrr": 9000})
        result = wm.get("data")
        assert result == {"mrr": 9000}

    def test_get_nonexistent_key_returns_none(self):
        wm = WorkingMemory("tenant-a", "run-1")
        assert wm.get("nonexistent") is None

    def test_increment_counter(self):
        wm = WorkingMemory("tenant-a", "run-1")
        wm.clear()
        assert wm.increment("counter") == 1
        assert wm.increment("counter") == 2

    def test_clear_removes_all_keys(self):
        wm = WorkingMemory("tenant-a", "run-1")
        wm.set("a", 1)
        wm.set("b", 2)
        wm.clear()
        assert wm.get("a") is None
        assert wm.get("b") is None

    def test_available_returns_true_with_fallback(self):
        wm = WorkingMemory("tenant-a", "run-1")
        assert wm.available() is True

    def test_tenant_isolation(self):
        wm1 = WorkingMemory("tenant-a", "run-1")
        wm2 = WorkingMemory("tenant-b", "run-1")
        wm1.set("data", "from-a")
        wm2.set("data", "from-b")
        assert wm1.get("data") == "from-a"
        assert wm2.get("data") == "from-b"


class TestInMemoryFallback:
    def test_setex_and_get(self):
        fb = _InMemoryFallback()
        fb.setex("key", 3600, "value")
        assert fb.get("key") == "value"

    def test_delete(self):
        fb = _InMemoryFallback()
        fb.setex("key", 3600, "value")
        fb.delete("key")
        assert fb.get("key") is None

    def test_keys_pattern(self):
        fb = _InMemoryFallback()
        fb.setex("wm:a:1", 3600, "v1")
        fb.setex("wm:a:2", 3600, "v2")
        fb.setex("wm:b:1", 3600, "v3")
        keys = fb.keys("wm:a:*")
        assert len(keys) == 2

    def test_incr(self):
        fb = _InMemoryFallback()
        assert fb.incr("counter") == 1
        assert fb.incr("counter") == 2
