"""Configuration module for AI services."""

from .llm import get_llm_client, get_model

__all__ = ["get_llm_client", "get_model"]
