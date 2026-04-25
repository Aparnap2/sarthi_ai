"""
Universal LLM client factory for Sarthi v4.2.

ONE RULE: All LLM calls MUST go through this module.
No direct AzureOpenAI instantiation in agents. Ever.

Provider Configuration:
    Option 1 - Azure OpenAI:
        - AZURE_OPENAI_ENDPOINT: https://{resource}.openai.azure.com/
        - AZURE_OPENAI_KEY: Your Azure OpenAI API key
        - AZURE_OPENAI_API_VERSION: API version (default: 2024-02-01)
        - AZURE_OPENAI_CHAT_DEPLOYMENT: Chat model deployment name
    
    Option 2 - Ollama (OpenAI-compatible):
        - OLLAMA_BASE_URL: http://localhost:11434/v1
        - OLLAMA_CHAT_MODEL: qwen3:0.6b
        - OLLAMA_EMBED_MODEL: nomic-embed-text:latest
    
    Option 3 - OpenAI:
        - OPENAI_API_KEY: Your OpenAI API key
        - OPENAI_CHAT_MODEL: gpt-4o-mini
        - OPENAI_EMBED_MODEL: text-embedding-3-small

    Option 4 - Groq:
        - GROQ_API_KEY: Your Groq API key
        - GROQ_CHAT_MODEL: llama-3.1-8b-instant
"""
import os
import threading
from openai import AzureOpenAI, OpenAI
from typing import Optional, Union


# Cache for singleton client instance
_client: Optional[Union[AzureOpenAI, OpenAI]] = None
_lock = threading.Lock()

# Provider type: "azure", "ollama", "openai", "groq"
_provider: Optional[str] = None


def _detect_provider() -> str:
    """
    Auto-detect LLM provider from environment variables.

    Priority order:
    1. Azure OpenAI (if AZURE_OPENAI_ENDPOINT is set)
    2. Ollama (if OLLAMA_BASE_URL is set)
    3. Groq (if GROQ_API_KEY is set)
    4. OpenAI (if OPENAI_API_KEY is set)

    Returns:
        str: Provider name

    Raises:
        ValueError: If no provider is configured
    """
    if os.environ.get("AZURE_OPENAI_ENDPOINT"):
        return "azure"
    if os.environ.get("OLLAMA_BASE_URL"):
        return "ollama"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    raise ValueError(
        "No LLM provider configured. Set one of: "
        "AZURE_OPENAI_ENDPOINT, OLLAMA_BASE_URL, GROQ_API_KEY, or OPENAI_API_KEY"
    )


def get_llm_client() -> Union[AzureOpenAI, OpenAI]:
    """
    Returns configured LLM client (Azure OpenAI or OpenAI-compatible).

    Uses singleton pattern with thread-safe locking to avoid recreating clients.

    Auto-detects provider from environment variables.

    Returns:
        AzureOpenAI or OpenAI: Configured client instance

    Raises:
        ValueError: If no provider is configured
        KeyError: If required environment variables are missing
    """
    global _client, _provider

    with _lock:
        if _client is None:
            _provider = _detect_provider()

            if _provider == "azure":
                _client = AzureOpenAI(
                    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                    api_key=os.environ["AZURE_OPENAI_KEY"],
                    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                )
            elif _provider == "ollama":
                base_url = os.environ["OLLAMA_BASE_URL"]
                # Cloud uses https://ollama.com, local uses http://localhost:11434
                # Add /v1 suffix for OpenAI-compatible SDK
                if not base_url.endswith("/v1"):
                    base_url = base_url.rstrip("/")
                    if "/api" in base_url:
                        base_url = base_url.replace("/api", "/v1")
                    elif not "/v1" in base_url:
                        base_url = base_url + "/v1"
                _client = OpenAI(
                    base_url=base_url,
                    api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
                )
            elif _provider == "groq":
                _client = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=os.environ["GROQ_API_KEY"],
                )
            elif _provider == "openai":
                _client = OpenAI(
                    api_key=os.environ["OPENAI_API_KEY"],
                )

    return _client


def get_chat_model() -> str:
    """
    Returns chat completion model name based on provider.

    Environment variables by provider:
        - Azure: AZURE_OPENAI_CHAT_DEPLOYMENT
        - Ollama: OLLAMA_CHAT_MODEL
        - Groq: GROQ_CHAT_MODEL
        - OpenAI: OPENAI_CHAT_MODEL

    Returns:
        str: Chat model name

    Raises:
        ValueError: If no provider is configured or model not set
    """
    provider = _provider or _detect_provider()

    if provider == "azure":
        return os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
    elif provider == "ollama":
        return os.environ.get("OLLAMA_CHAT_MODEL", "qwen3:0.6b")
    elif provider == "groq":
        return os.environ.get("GROQ_CHAT_MODEL", "llama-3.1-8b-instant")
    elif provider == "openai":
        return os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    raise ValueError(f"Unknown provider: {provider}")


def get_embedding_model() -> str:
    """
    Returns embedding model name based on provider.

    Environment variables by provider:
        - Azure: EMBEDDING_MODEL (defaults to text-embedding-3-small)
        - Ollama: OLLAMA_EMBED_MODEL
        - Groq: Not supported
        - OpenAI: OPENAI_EMBED_MODEL

    Returns:
        str: Embedding model name
    """
    provider = _provider or _detect_provider()

    if provider == "azure":
        return os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    elif provider == "ollama":
        return os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    elif provider == "groq":
        raise ValueError("Groq does not support embeddings")
    elif provider == "openai":
        return os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    raise ValueError(f"Unknown provider: {provider}")


def reset_client() -> None:
    """
    Reset the cached client instance.

    Useful for testing or reconfiguration.
    """
    global _client, _provider
    with _lock:
        _client = None
        _provider = None


# Backward compatibility alias
get_model = get_chat_model
