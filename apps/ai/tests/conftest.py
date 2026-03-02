"""Pytest configuration and fixtures."""

import os
import pytest
import pytest_asyncio
import httpx
import asyncpg
import uuid

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://iterateswarm:iterateswarm@localhost:5432/iterateswarm"
)

API_URL = os.getenv("API_BASE_URL", "http://localhost:3000")


@pytest_asyncio.fixture(scope="session")
async def db_pool():
    """PostgreSQL connection pool for all tests."""
    pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=5)
    yield pool
    await pool.close()


@pytest_asyncio.fixture(scope="session")
async def http_client():
    async with httpx.AsyncClient(
        base_url=API_URL,
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
    ) as client:
        yield client


@pytest.fixture
def unique_task_id():
    return f"e2e-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_config():
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
    return {
        "feedback_id": "test-feedback-123",
        "content": "The login button is not working on mobile Safari.",
        "source": "discord",
    }


# Prevent event loop closure warnings
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
