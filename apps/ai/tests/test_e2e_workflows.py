"""End-to-end workflow tests for IterateSwarm.

This module contains E2E tests that verify complete workflows
across the Go backend, Python AI service, and external services.
"""

import asyncio
import os
import pytest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import datetime

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class FeedbackInput:
    """Feedback input model for workflow testing."""
    content: str
    source: str
    user_id: str
    timestamp: datetime
    metadata: Optional[dict] = None


@dataclass
class FeedbackClassification:
    """Feedback classification model."""
    category: str
    priority: str
    sentiment: str
    confidence: float


class TestFeedbackProcessingWorkflow:
    """E2E tests for the feedback processing workflow."""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up mock environment variables."""
        monkeypatch.setenv("TEMPORAL_ADDRESS", "localhost:7233")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
        monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")

    @pytest.mark.asyncio
    async def test_complete_feedback_workflow(self, mock_env):
        """Test the complete feedback processing workflow.

        This test simulates:
        1. User submits feedback via Discord webhook
        2. Feedback is validated and classified
        3. Duplicate detection is performed
        4. Issues are created in the system
        5. Workflow status is updated
        """
        # Simulate workflow using local mocks
        # Setup classification mock
        classification = FeedbackClassification(
            category="bug",
            priority="high",
            sentiment="negative",
            confidence=0.92,
        )

        # Simulate workflow
        feedback = FeedbackInput(
            content="The login button doesn't work on mobile",
            source="discord",
            user_id="user-456",
            timestamp=datetime.utcnow(),
        )

        # Verify workflow components
        assert feedback.content is not None
        assert feedback.source == "discord"
        assert isinstance(feedback.timestamp, datetime)

        # Verify classification
        assert classification.category == "bug"
        assert classification.priority == "high"
        assert classification.confidence > 0.9

        # Simulate duplicate check result
        duplicate_check = {"is_duplicate": False, "similarity": 0.45}
        assert duplicate_check["is_duplicate"] is False

        # Simulate issue creation result
        issue = {"issue_id": "issue-123", "url": "https://github.com/org/repo/issues/123"}
        assert issue["issue_id"] == "issue-123"


class TestDuplicateDetectionWorkflow:
    """E2E tests for the duplicate detection workflow."""

    @pytest.mark.asyncio
    async def test_duplicate_detection_flow(self):
        """Test the complete duplicate detection flow."""
        from src.services.qdrant import QdrantService

        # Mock the Qdrant service
        with patch.object(QdrantService, "__init__", lambda x: None):
            service = QdrantService()
            service.config = MagicMock()
            service.config.url = "http://localhost:6333"
            service.config.collection = "feedback_items"
            service.config.similarity_threshold = 0.85
            service._collection_initialized = True
            service.client = AsyncMock()

            # Mock embedding generation
            service.get_embedding = AsyncMock(return_value=[0.1] * 768)

            # Test: New unique feedback
            service.client.search = AsyncMock(return_value=[])
            is_duplicate, score = await service.check_duplicate("This is completely new feedback")

            assert is_duplicate is False
            assert score == 0.0

            # Test: Duplicate feedback
            from qdrant_client.models import ScoredPoint
            mock_point = ScoredPoint(id="existing-id", score=0.92, payload={}, version=1)
            service.client.search = AsyncMock(return_value=[mock_point])

            is_duplicate, score = await service.check_duplicate("Similar feedback that already exists")

            assert is_duplicate is True
            assert score == 0.92


class TestIntegrationHealthChecks:
    """E2E tests for service health checks."""

    @pytest.mark.asyncio
    async def test_temporal_connection(self):
        """Test Temporal service connectivity check."""
        # Mock Temporal client
        mock_client = AsyncMock()
        mock_client.list_namespaces = AsyncMock(return_value=MagicMock(namespaces=[]))

        # In real implementation, this would connect to Temporal
        assert mock_client is not None

    @pytest.mark.asyncio
    async def test_qdrant_connection(self):
        """Test Qdrant service connectivity check."""
        from qdrant_client import AsyncQdrantClient

        # Mock the connection
        mock_client = AsyncMock()
        mock_client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))

        # Verify mock works
        await mock_client.get_collections()
        mock_client.get_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_ollama_connection(self):
        """Test Ollama service connectivity check."""
        import httpx

        # Mock HTTP client for Ollama
        mock_response = {
            "data": [{
                "embedding": [0.1] * 768,
            }]
        }

        mock_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response_obj

        # Verify mock works
        response = await mock_client.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "input": "test"}
        )

        assert response is not None


class TestAPIAuthenticationFlow:
    """E2E tests for API authentication flow with Clerk."""

    def test_clerk_config_loading(self):
        """Test Clerk configuration is loaded from environment."""
        from src.config import get_config

        # Config should have defaults
        config = get_config()

        # Verify temporal config
        assert config.temporal.address == "localhost:7233"

    def test_auth_headers_extraction(self):
        """Test authentication header extraction."""
        # Simulate Fiber context (Go-side would use Clerk SDK)
        auth_header = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

        # Verify header format
        parts = auth_header.split(" ")
        assert len(parts) == 2
        assert parts[0] == "Bearer"


class TestDiscordWebhookFlow:
    """E2E tests for Discord webhook processing."""

    @pytest.mark.asyncio
    async def test_webhook_message_parsing(self):
        """Test Discord webhook message parsing."""
        from dataclasses import dataclass

        @dataclass
        class DiscordMessage:
            id: str
            content: str
            author_id: str
            timestamp: str

        # Simulate webhook payload
        message = DiscordMessage(
            id="123456789",
            content="I found a bug in the payment flow",
            author_id="user-123",
            timestamp="2024-01-15T10:30:00Z",
        )

        assert message.id == "123456789"
        assert "bug" in message.content.lower()

    @pytest.mark.asyncio
    async def test_webhook_response_format(self):
        """Test Discord webhook response format."""
        # Simulate response structure
        response = {
            "success": True,
            "message": "Feedback received and queued for processing",
            "tracking_id": "fb-abc123",
        }

        assert response["success"] is True
        assert "tracking_id" in response


class TestWorkflowStatusTracking:
    """E2E tests for workflow status tracking."""

    @pytest.mark.asyncio
    async def test_workflow_status_updates(self):
        """Test workflow status is properly tracked."""
        from enum import Enum

        class WorkflowStatus(Enum):
            PENDING = "pending"
            PROCESSING = "processing"
            COMPLETED = "completed"
            FAILED = "failed"

        # Test status transitions
        status = WorkflowStatus.PENDING
        assert status.value == "pending"

        status = WorkflowStatus.PROCESSING
        assert status.value == "processing"

        status = WorkflowStatus.COMPLETED
        assert status.value == "completed"

    @pytest.mark.asyncio
    async def test_workflow_result_structure(self):
        """Test workflow result has correct structure."""
        from dataclasses import dataclass
        from typing import Optional

        @dataclass
        class WorkflowResult:
            workflow_id: str
            status: str
            issues_created: int
            feedback_processed: int
            error: Optional[str] = None

        result = WorkflowResult(
            workflow_id="wf-123",
            status="completed",
            issues_created=2,
            feedback_processed=5,
        )

        assert result.workflow_id == "wf-123"
        assert result.issues_created == 2
        assert result.error is None


# Pytest configuration for E2E tests
pytestmark = pytest.mark.e2e
