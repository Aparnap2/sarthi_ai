"""
Unit tests for Temporal Workflows and Activities - Phase 4.

Tests cover:
- Activity input validation
- Activity return value structure
- Workflow importability
- Telegram message sending

Run with:
  uv run pytest tests/unit/test_workflows.py -v --timeout=30 --asyncio-mode=auto
"""
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set test environment variables before importing activities
os.environ["TELEGRAM_API_BASE"] = "http://localhost:8085"
os.environ["TELEGRAM_BOT_TOKEN"] = "test-bot-token"


class TestRunFinanceAgent:
    """Tests for run_finance_agent activity."""

    @pytest.mark.asyncio
    async def test_run_finance_agent_returns_required_fields(self):
        """Test that activity returns all required fields."""
        from src.activities.run_finance_agent import run_finance_agent

        # Mock the finance_graph to avoid actual LLM calls
        mock_result = {
            "tenant_id": "test-tenant",
            "action": "DIGEST",
            "anomaly_score": 0.25,
            "anomaly_detected": False,
            "output_message": "Test message",
            "langfuse_trace_id": "trace-123",
        }

        with patch("src.activities.run_finance_agent.finance_graph") as mock_graph:
            mock_graph.invoke = MagicMock(return_value=mock_result)

            result = await run_finance_agent("test-tenant", {"event": "test"})

            # Verify required fields
            assert "tenant_id" in result
            assert "action" in result
            assert "anomaly_score" in result
            assert "anomaly_detected" in result
            assert "output_message" in result
            assert "langfuse_trace_id" in result

            # Verify values
            assert result["tenant_id"] == "test-tenant"
            assert result["action"] == "DIGEST"
            assert isinstance(result["anomaly_score"], float)
            assert isinstance(result["anomaly_detected"], bool)

    @pytest.mark.asyncio
    async def test_run_finance_agent_raises_on_missing_tenant(self):
        """Test that activity raises ValueError on missing tenant_id."""
        from src.activities.run_finance_agent import run_finance_agent

        with pytest.raises(ValueError, match="tenant_id is required"):
            await run_finance_agent("", {"event": "test"})

        with pytest.raises(ValueError, match="tenant_id is required"):
            await run_finance_agent("   ", {"event": "test"})


class TestRunBiAgent:
    """Tests for run_bi_agent activity."""

    @pytest.mark.asyncio
    async def test_run_bi_agent_returns_required_fields(self):
        """Test that activity returns all required fields."""
        from src.activities.run_bi_agent import run_bi_agent

        # Mock the bi_graph to avoid actual LLM calls
        mock_result = {
            "tenant_id": "test-tenant",
            "query": "Test query",
            "generated_sql": "SELECT * FROM test",
            "sql_result": {"rows": [], "columns": [], "count": 0},
            "narrative": "Test narrative",
            "chart_type": "bar",
            "chart_path": "/tmp/chart.png",
            "output_message": "Test message",
            "langfuse_trace_id": "trace-456",
        }

        with patch("src.activities.run_bi_agent.bi_graph") as mock_graph:
            mock_graph.invoke = MagicMock(return_value=mock_result)

            result = await run_bi_agent("test-tenant", "Test query")

            # Verify required fields
            assert "tenant_id" in result
            assert "query" in result
            assert "generated_sql" in result
            assert "sql_result" in result
            assert "narrative" in result
            assert "chart_type" in result
            assert "chart_path" in result
            assert "output_message" in result

            # Verify values
            assert result["tenant_id"] == "test-tenant"
            assert result["query"] == "Test query"
            assert isinstance(result["sql_result"], dict)

    @pytest.mark.asyncio
    async def test_run_bi_agent_raises_on_missing_query(self):
        """Test that activity raises ValueError on missing query."""
        from src.activities.run_bi_agent import run_bi_agent

        with pytest.raises(ValueError, match="query is required"):
            await run_bi_agent("test-tenant", "")

        with pytest.raises(ValueError, match="query is required"):
            await run_bi_agent("test-tenant", "   ")


class TestSendTelegramMessage:
    """Tests for send_telegram_message activity."""

    @pytest.mark.asyncio
    async def test_send_telegram_message_ok(self):
        """Test successful message sending."""
        from src.activities.send_telegram import send_telegram_message

        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("src.activities.send_telegram.httpx.AsyncClient", return_value=mock_client):
            result = await send_telegram_message("test-chat", "Test message")

            # Verify response
            assert result["ok"] is True
            assert result["message_id"] == 123
            assert result["chat_id"] == "test-chat"

            # Verify API call
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "sendMessage" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_send_telegram_message_empty_text(self):
        """Test that activity raises ValueError on empty text."""
        from src.activities.send_telegram import send_telegram_message

        with pytest.raises(ValueError, match="Message text cannot be empty"):
            await send_telegram_message("test-chat", "")

        with pytest.raises(ValueError, match="Message text cannot be empty"):
            await send_telegram_message("test-chat", "   ")


class TestSendTelegramPhoto:
    """Tests for send_telegram_photo activity."""

    @pytest.mark.asyncio
    async def test_send_telegram_photo_missing_file(self):
        """Test that activity raises ValueError on missing file."""
        from src.activities.send_telegram import send_telegram_photo

        with pytest.raises(ValueError, match="Photo path cannot be empty"):
            await send_telegram_photo("test-chat", "")

        with pytest.raises(ValueError, match="Photo path cannot be empty"):
            await send_telegram_photo("test-chat", "   ")

        with pytest.raises(ValueError, match="Photo file not found"):
            await send_telegram_photo("test-chat", "/nonexistent/path.png")


class TestWorkflowImportability:
    """Tests for workflow importability and structure."""

    def test_finance_workflow_importable(self):
        """Test that FinanceWorkflow can be imported and has required methods."""
        from src.workflows.finance_workflow import FinanceWorkflow

        # Verify class exists
        assert FinanceWorkflow is not None

        # Verify required methods exist
        assert hasattr(FinanceWorkflow, "run")
        assert hasattr(FinanceWorkflow, "hitl_action_signal")

        # Verify it's decorated as a workflow (check for __temporal_workflow_run)
        assert hasattr(FinanceWorkflow.run, "__temporal_workflow_run") or hasattr(FinanceWorkflow, "__temporal_class_workflow__")

    def test_bi_workflow_importable(self):
        """Test that BIWorkflow can be imported and has required methods."""
        from src.workflows.bi_workflow import BIWorkflow

        # Verify class exists
        assert BIWorkflow is not None

        # Verify required methods exist
        assert hasattr(BIWorkflow, "run")

        # Verify it's decorated as a workflow
        assert hasattr(BIWorkflow.run, "__temporal_workflow_run") or hasattr(BIWorkflow, "__temporal_class_workflow__")
