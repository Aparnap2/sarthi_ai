"""
Universal LLM client factory for Sarthi v4.2.

ONE RULE: All LLM calls MUST go through this module.
No direct AzureOpenAI instantiation in agents. Ever.

Provider Configuration:
    Set environment variables:
    - AZURE_OPENAI_ENDPOINT: https://{resource}.openai.azure.com/
    - AZURE_OPENAI_KEY: Your Azure OpenAI API key
    - AZURE_OPENAI_API_VERSION: API version (default: 2024-02-01)
    - AZURE_OPENAI_CHAT_DEPLOYMENT: Chat model deployment name
    - EMBEDDING_MODEL: Embedding model name (optional, defaults to text-embedding-3-small)
"""
import os
import threading
from openai import AzureOpenAI
from typing import Optional


# Cache for singleton client instance
_client: Optional[AzureOpenAI] = None
_lock = threading.Lock()


def get_llm_client() -> AzureOpenAI:
    """
    Returns configured AzureOpenAI client.

    Uses singleton pattern with thread-safe locking to avoid recreating clients.

    Environment variables required:
        - AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
        - AZURE_OPENAI_KEY: Azure OpenAI API key

    Environment variables optional:
        - AZURE_OPENAI_API_VERSION: API version (defaults to 2024-02-01)

    Returns:
        AzureOpenAI: Configured client instance

    Raises:
        KeyError: If required environment variables are missing
    """
    global _client

    with _lock:
        if _client is None:
            _client = AzureOpenAI(
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_KEY"],
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            )

    return _client


def get_chat_model() -> str:
    """
    Returns chat completion model name.
    
    Environment variables required:
        - AZURE_OPENAI_CHAT_DEPLOYMENT: Chat model deployment name
    
    Returns:
        str: Chat model deployment name
    
    Raises:
        KeyError: If AZURE_OPENAI_CHAT_DEPLOYMENT is not set
    """
    return os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]


def get_embedding_model() -> str:
    """
    Returns embedding model name.

    Environment variables:
        - EMBEDDING_MODEL: Embedding model name (optional)

    Returns:
        str: Embedding model name (defaults to text-embedding-3-small)
    """
    return os.environ.get(
        "EMBEDDING_MODEL",
        "text-embedding-3-small"
    )


def reset_client() -> None:
    """
    Reset the cached client instance.

    Useful for testing or reconfiguration.
    """
    global _client
    with _lock:
        _client = None


# Backward compatibility alias
get_model = get_chat_model
