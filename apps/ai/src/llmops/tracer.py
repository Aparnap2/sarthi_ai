"""Langfuse @traced decorator — zero test impact.
No-op if LANGFUSE_SECRET_KEY not set (unit tests pass through)."""
from __future__ import annotations
import os, functools
from typing import Any

_client = None

def _get_client():
    global _client
    if _client is None:
        try:
            from langfuse import Langfuse
            secret = os.environ.get("LANGFUSE_SECRET_KEY")
            if secret:
                _client = Langfuse(
                    secret_key=secret,
                    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
                    host=os.environ.get("LANGFUSE_HOST", "http://localhost:3001"),
                )
        except Exception:
            pass
    return _client

def traced(agent: str, signature: str):
    """Decorator. Pure pass-through if Langfuse not configured."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            client = _get_client()
            if client is None:
                return fn(*args, **kwargs)
            trace = client.trace(name=f"{agent}.{signature}")
            try:
                result = fn(*args, **kwargs)
                trace.generation(output=str(result)[:500])
                return result
            except Exception as e:
                trace.event(name="error", metadata={"error": str(e)[:200]})
                raise
        return wrapper
    return decorator
