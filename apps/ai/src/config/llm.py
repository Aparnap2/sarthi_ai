"""
Universal LLM client factory.

Change LLM_BASE_URL in .env to swap provider. Zero code changes.

Provider         LLM_BASE_URL
────────────────────────────────────────────────────────────────
OpenRouter       https://openrouter.ai/api/v1
Azure OpenAI     https://{resource}.openai.azure.com/openai/v1
OpenAI           https://api.openai.com/v1
Groq             https://api.groq.com/openai/v1
Ollama (local)   http://localhost:11434/v1
"""
import os
from openai import OpenAI


def get_llm_client() -> OpenAI:
    """
    Get a universal OpenAI-compatible LLM client.

    Returns:
        OpenAI client configured with environment variables
    """
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )


def get_model() -> str:
    """
    Get the configured LLM model name.

    Returns:
        Model name from environment variables
    """
    return os.environ["LLM_MODEL"]
