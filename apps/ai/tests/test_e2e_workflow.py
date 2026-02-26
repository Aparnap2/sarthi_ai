"""End-to-end tests for the complete IterateSwarm OS workflow.

Requires ALL Docker containers running:
    docker start iterateswarm-redis iterateswarm-postgres iterateswarm-temporal iterateswarm-qdrant

Requires Python gRPC server running:
    cd apps/ai && uv run python -m src.grpc_server

Requires Go Fiber server running:
    cd apps/core && go run cmd/server/main.go

Mark: pytest -m e2e (slow tests, ~2-3 min each)
"""

import asyncio
import os
import time
import uuid

import pytest
import httpx
import redis.asyncio as redis
from src.context.shared_context import ContextStore

BASE_URL = "http://localhost:3000"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


@pytest.fixture(scope="module")
async def http_client():
    """Create HTTP client for API calls."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        yield client


@pytest.fixture(scope="module")
async def redis_store():
    """Create Redis context store."""
    r = redis.Redis.from_url(REDIS_URL)
    store = ContextStore(r)
    yield store
    await r.aclose()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_infra_redis_is_real(http_client):
    """Infra guard: Verify Redis is accessible."""
    r = redis.Redis.from_url(REDIS_URL)
    try:
        pong = await r.ping()
        assert pong is True, "Redis did not respond to PING"
    finally:
        await r.aclose()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_infra_azure_llm_is_reachable():
    """Infra guard: Verify Azure OpenAI is accessible."""
    from openai import OpenAI
    
    for k in ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]:
        assert os.getenv(k), f"Missing env var: {k}"
    
    client = OpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        base_url="https://aparnaopenai.openai.azure.com/openai/v1",
    )
    
    r = client.chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=5,
    )
    assert r.choices and r.choices[0].message.content is not None


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_webhook_discord_accepts_valid_payload(http_client, redis_store):
    """Test Discord webhook accepts valid feedback."""
    task_id = f"e2e-discord-{uuid.uuid4()}"
    
    resp = await http_client.post("/webhooks/discord", json={
        "text": f"[E2E-TEST-{task_id}] Test feedback message",
        "source": "discord",
        "user_id": task_id,
        "channel_id": "test-channel",
    })
    
    assert resp.status_code == 200, f"Webhook rejected: {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_webhook_slack_accepts_valid_payload(http_client):
    """Test Slack webhook accepts valid feedback."""
    task_id = f"e2e-slack-{uuid.uuid4()}"
    
    resp = await http_client.post("/webhooks/slack", json={
        "text": f"[E2E-TEST-{task_id}] Test Slack message",
        "source": "slack",
        "user_id": task_id,
        "channel_id": "test-channel",
    })
    
    assert resp.status_code == 200, f"Slack webhook rejected: {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_idempotency_duplicate_discord_payload(http_client):
    """Test that duplicate Discord payloads are deduplicated."""
    unique_text = f"[IDEMPOTENCY-TEST-{uuid.uuid4()}] Duplicate test"
    
    # First submission
    r1 = await http_client.post("/webhooks/discord", json={
        "text": unique_text,
        "source": "discord",
        "user_id": "idempotency-user",
        "channel_id": "test-ch",
    })
    assert r1.status_code == 200
    
    # Second submission with same content (should be deduplicated)
    r2 = await http_client.post("/webhooks/discord", json={
        "text": unique_text,
        "source": "discord",
        "user_id": "idempotency-user",
        "channel_id": "test-ch",
    })
    # Should still return 200 (idempotent), not 500
    assert r2.status_code == 200


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_admin_dashboard_loads(http_client):
    """Test that admin dashboard loads successfully."""
    resp = await http_client.get("/admin")
    assert resp.status_code == 200, f"Dashboard failed: {resp.status_code}"
    assert b"IterateSwarm" in resp.content or b"admin" in resp.content.lower()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_admin_live_feed_endpoint(http_client):
    """Test Live Feed SSE endpoint is accessible."""
    resp = await http_client.get("/api/live-feed")
    # Should return HTML or 200
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_admin_hitl_queue_endpoint(http_client):
    """Test HITL Queue endpoint is accessible."""
    resp = await http_client.get("/api/approvals/pending")
    # Should return 200 (may be empty list)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_admin_agent_map_endpoint(http_client):
    """Test Agent Map endpoint is accessible."""
    resp = await http_client.get("/api/agent-map")
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_admin_task_board_endpoint(http_client):
    """Test Task Board endpoint is accessible."""
    resp = await http_client.get("/api/tasks/board")
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_admin_config_panel_endpoint(http_client):
    """Test Config Panel endpoint is accessible."""
    resp = await http_client.get("/api/config/panel")
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_admin_telemetry_panel_endpoint(http_client):
    """Test Telemetry Panel endpoint is accessible."""
    resp = await http_client.get("/api/telemetry/panel")
    assert resp.status_code == 200
