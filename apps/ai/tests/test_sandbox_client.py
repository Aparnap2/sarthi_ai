"""Tests for SandboxClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.sandbox_client import SandboxClient, SandboxResult
import base64


@pytest.fixture
def client():
    return SandboxClient()


# ── Happy path ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_numpy_executes(client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "output": "20.0\n",
        "chart": None,
        "error": None,
    }
    mock_post = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.post", mock_post):
        r = await client.run(
            "import numpy as np; print(np.mean([10,20,30]))"
        )
    assert r.success is True
    assert "20.0" in r.output


@pytest.mark.asyncio
async def test_chart_returned_as_base64(client):
    fake_b64 = base64.b64encode(b"PNG_BYTES").decode()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "output": "",
        "chart": fake_b64,
        "error": None,
    }
    mock_post = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.post", mock_post):
        r = await client.run(
            "import matplotlib.pyplot as plt; plt.plot([1,2,3])"
        )
    assert r.chart_b64 == fake_b64
    assert r.chart_bytes() == b"PNG_BYTES"


@pytest.mark.asyncio
async def test_pandas_executes(client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "output": "3\n",
        "chart": None,
        "error": None,
    }
    mock_post = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.post", mock_post):
        r = await client.run(
            "import pandas as pd; print(len(pd.DataFrame({'a': [1,2,3]})))"
        )
    assert r.success is True


@pytest.mark.asyncio
async def test_sklearn_executes(client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "output": "done\n",
        "chart": None,
        "error": None,
    }
    mock_post = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.post", mock_post):
        r = await client.run(
            "from sklearn.linear_model import LinearRegression; print('done')"
        )
    assert r.success is True


# ── Error paths ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_timeout_returns_error_not_exception(client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": False,
        "output": "",
        "chart": None,
        "error": "Stopped: exceeded 10s limit",
    }
    mock_post = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.post", mock_post):
        r = await client.run("while True: pass", timeout=1)
    assert r.success is False
    assert "exceeded" in r.error


@pytest.mark.asyncio
async def test_network_failure_returns_error(client):
    mock_post = AsyncMock(side_effect=Exception("connection refused"))
    with patch("httpx.AsyncClient.post", mock_post):
        r = await client.run("print(1)")
    assert r.success is False
    assert r.error is not None


@pytest.mark.asyncio
async def test_no_chart_returns_none_bytes(client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "output": "42\n",
        "chart": None,
        "error": None,
    }
    mock_post = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.post", mock_post):
        r = await client.run("print(42)")
    assert r.chart_b64 is None
    assert r.chart_bytes() is None


@pytest.mark.asyncio
async def test_success_false_when_error_present(client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": False,
        "output": "",
        "chart": None,
        "error": "ZeroDivisionError: division by zero",
    }
    mock_post = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.post", mock_post):
        r = await client.run("1/0")
    assert r.success is False
    assert "ZeroDivisionError" in r.error


@pytest.mark.asyncio
async def test_concurrent_requests_independent(client):
    import asyncio

    call_count = 0

    async def fake_post(*a, **kw):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        mock.json.return_value = {
            "success": True,
            "output": f"{call_count}\n",
            "chart": None,
            "error": None,
        }
        return mock

    mock_post = AsyncMock(side_effect=fake_post)
    with patch("httpx.AsyncClient.post", mock_post):
        r1, r2 = await asyncio.gather(
            client.run("print(1)"),
            client.run("print(2)"),
        )
    assert r1.output != r2.output
