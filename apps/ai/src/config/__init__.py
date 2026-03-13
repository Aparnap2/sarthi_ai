"""Configuration module for AI services."""

from .llm import get_llm_client, get_chat_model, get_embedding_model, reset_client
from .llm_guard import enforce_llm_factory, scan_directory_for_violations

# Backward compatibility alias
get_model = get_chat_model

__all__ = [
    "get_llm_client",
    "get_chat_model",
    "get_embedding_model",
    "get_model",  # Backward compatibility
    "reset_client",
    "enforce_llm_factory",
    "scan_directory_for_violations",
]
