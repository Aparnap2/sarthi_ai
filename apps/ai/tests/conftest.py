"""Pytest configuration and fixtures."""

import os
import pytest
import pytest_asyncio
import httpx
import redis.asyncio as aioredis
from unittest.mock import AsyncMock, MagicMock

# Read from environment, fall back to localhost for local dev
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


# ── Redis fixture ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def redis_client():
    """Real Redis client. Session-scoped — one connection for all tests."""
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    yield client
    await client.aclose()  # explicit close prevents event loop warnings


# ── HTTP client fixture ───────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def http_client():
    """
    Single httpx.AsyncClient for all E2E tests.
    Session-scoped with explicit aclose() — prevents 'Event loop closed' errors.
    """
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
    ) as client:
        yield client
    # 'async with' handles aclose() automatically — no manual close needed


# ── Per-test isolation: unique task_id ───────────────────────────────────────

@pytest.fixture
def unique_task_id():
    """Every test gets its own task ID — prevents Redis key collisions."""
    import uuid
    return f"e2e-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    from src.config import Config, TemporalConfig, OllamaConfig, QdrantConfig

    return Config(
        temporal=TemporalConfig(
            host="localhost",
            port=7233,
            namespace="default",
            task_queue="AI_TASK_QUEUE",
        ),
        ollama=OllamaConfig(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
            model="qwen2.5-coder:3b",
            embedding_model="nomic-embed-text",
        ),
        qdrant=QdrantConfig(
            url="http://localhost:6333",
            collection="feedback_items",
            similarity_threshold=0.85,
        ),
    )


@pytest.fixture
def sample_feedback():
    """Sample feedback for testing."""
    return {
        "feedback_id": "test-feedback-123",
        "content": "The login button is not working on mobile Safari. When I click it, nothing happens.",
        "source": "discord",
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    class MockChoice:
        message = MagicMock()

    class MockResponse:
        choices = [MockChoice()]

    return MockResponse()
