"""Pytest configuration and fixtures."""

import os
import pytest
import pytest_asyncio
import httpx
import asyncpg
import uuid
import asyncio

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


# =============================================================================
# Neo4j / Graphiti Fixtures for GraphMemoryAgent Tests
# =============================================================================


@pytest.fixture(scope="session")
def neo4j_uri():
    """Return Neo4j Bolt URL for tests."""
    return os.environ.get("NEO4J_URI", "bolt://localhost:7687")


@pytest.fixture(scope="session")
def neo4j_user():
    """Return Neo4j username for tests."""
    return os.environ.get("NEO4J_USER", "neo4j")


@pytest.fixture(scope="session")
def neo4j_password():
    """Return Neo4j password for tests."""
    return os.environ.get("NEO4J_PASSWORD", "saarathi")


@pytest_asyncio.fixture(scope="session")
async def graphiti_client(neo4j_uri, neo4j_user, neo4j_password):
    """
    Create and initialize Graphiti client for tests.

    This fixture:
    1. Creates a Graphiti client connected to Neo4j
    2. Builds indices and constraints (run once per session)
    3. Yields the client for tests
    4. Closes the connection after all tests complete
    """
    from graphiti_core import Graphiti
    from graphiti_core.llm_client.openai_client import OpenAIClient
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    from src.config.llm import get_llm_client, get_model

    # Get LLM client from app config
    llm = get_llm_client()
    model = get_model()
    embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    # LLM config
    llm_config = LLMConfig(
        model=model,
        small_model=model,
    )

    # Create clients
    llm_client = OpenAIClient(
        client=llm,
        config=llm_config,
    )
    embedder_client = OpenAIEmbedder(
        config=OpenAIEmbedderConfig(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY", "test-key"),
            embedding_model=embedding_model,
        ),
    )
    cross_encoder = OpenAIRerankerClient(
        client=llm,
        config=llm_config,
    )

    # Create Graphiti client
    client = Graphiti(
        neo4j_uri,
        neo4j_user,
        neo4j_password,
        llm_client=llm_client,
        embedder=embedder_client,
        cross_encoder=cross_encoder,
    )

    # Initialize indices and constraints (run once)
    await client.build_indices_and_constraints()

    yield client

    # Cleanup
    await client.close()


@pytest_asyncio.fixture
async def graph_agent(graphiti_client):
    """
    Create GraphMemoryAgent instance for tests.
    
    Uses the shared graphiti_client to avoid redundant initialization.
    """
    from src.agents.graph_memory_agent import GraphMemoryAgent
    
    # Create agent with pre-initialized client
    agent = GraphMemoryAgent()
    # Replace the default client with our test client
    agent._g = graphiti_client
    yield agent


# Prevent event loop closure warnings
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
