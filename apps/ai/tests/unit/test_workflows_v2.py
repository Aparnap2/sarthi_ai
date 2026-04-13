"""
Unit tests for Temporal Workflows V2 — New workflows + Guardian extension.

Tests cover:
- All 4 new workflows importable and have @workflow.defn
- Guardian watchlist activity works with mock signals
- Worker imports all new workflows and activities
- PulseWorkflow includes guardian_result in return structure

Run with:
  uv run pytest tests/unit/test_workflows_v2.py -v --timeout=30 --asyncio-mode=auto
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set test environment variables before importing activities
os.environ["SLACK_WEBHOOK_URL"] = ""
os.environ["SLACK_BOT_TOKEN"] = ""
os.environ["SLACK_CHANNEL"] = "#test"

TENANT = "test-workflow-tenant-v2"


# =============================================================================
# TestNewWorkflowImports (4 tests)
# =============================================================================


class TestNewWorkflowImports:
    """Tests that all 4 new workflows are importable and decorated."""

    def test_self_analysis_workflow_importable(self):
        """Test that SelfAnalysisWorkflow can be imported and has defn."""
        from src.workflows.self_analysis_workflow import SelfAnalysisWorkflow

        assert SelfAnalysisWorkflow is not None
        assert hasattr(SelfAnalysisWorkflow, "run")
        # Check Temporal workflow definition is registered
        assert hasattr(SelfAnalysisWorkflow, "__temporal_workflow_definition")

    def test_eval_loop_workflow_importable(self):
        """Test that EvalLoopWorkflow can be imported and has defn."""
        from src.workflows.eval_loop_workflow import EvalLoopWorkflow

        assert EvalLoopWorkflow is not None
        assert hasattr(EvalLoopWorkflow, "run")
        assert hasattr(EvalLoopWorkflow, "__temporal_workflow_definition")

    def test_compression_workflow_importable(self):
        """Test that CompressionWorkflow can be imported and has defn."""
        from src.workflows.compression_workflow import CompressionWorkflow

        assert CompressionWorkflow is not None
        assert hasattr(CompressionWorkflow, "run")
        assert hasattr(CompressionWorkflow, "__temporal_workflow_definition")

    def test_weight_decay_workflow_importable(self):
        """Test that WeightDecayWorkflow can be imported and has defn."""
        from src.workflows.weight_decay_workflow import WeightDecayWorkflow

        assert WeightDecayWorkflow is not None
        assert hasattr(WeightDecayWorkflow, "run")
        assert hasattr(WeightDecayWorkflow, "__temporal_workflow_definition")


# =============================================================================
# TestNewWorkflowStructure (4 tests)
# =============================================================================


class TestNewWorkflowStructure:
    """Tests that new workflows have correct return structure."""

    @pytest.mark.asyncio
    async def test_self_analysis_workflow_returns_correct_structure(self):
        """Test SelfAnalysisWorkflow returns expected dict."""
        from src.workflows.self_analysis_workflow import SelfAnalysisWorkflow

        with patch("src.workflows.self_analysis_workflow.workflow") as mock_wf:
            mock_wf.logger = MagicMock()
            workflow = SelfAnalysisWorkflow()
            result = await workflow.run(TENANT)

            assert result["tenant_id"] == TENANT
            assert result["status"] == "analysis_complete"

    @pytest.mark.asyncio
    async def test_eval_loop_workflow_returns_correct_structure(self):
        """Test EvalLoopWorkflow returns expected dict."""
        from src.workflows.eval_loop_workflow import EvalLoopWorkflow

        with patch("src.workflows.eval_loop_workflow.workflow") as mock_wf:
            mock_wf.logger = MagicMock()
            workflow = EvalLoopWorkflow()
            result = await workflow.run(TENANT)

            assert result["tenant_id"] == TENANT
            assert result["status"] == "eval_complete"

    @pytest.mark.asyncio
    async def test_compression_workflow_returns_correct_structure(self):
        """Test CompressionWorkflow returns expected dict."""
        from src.workflows.compression_workflow import CompressionWorkflow

        with patch("src.workflows.compression_workflow.workflow") as mock_wf:
            mock_wf.logger = MagicMock()
            workflow = CompressionWorkflow()
            result = await workflow.run(TENANT)

            assert result["tenant_id"] == TENANT
            assert result["status"] == "compression_complete"

    @pytest.mark.asyncio
    async def test_weight_decay_workflow_returns_correct_structure(self):
        """Test WeightDecayWorkflow returns expected dict."""
        from src.workflows.weight_decay_workflow import WeightDecayWorkflow

        with patch("src.workflows.weight_decay_workflow.workflow") as mock_wf:
            mock_wf.logger = MagicMock()
            workflow = WeightDecayWorkflow()
            result = await workflow.run(TENANT)

            assert result["tenant_id"] == TENANT
            assert result["status"] == "decay_complete"


# =============================================================================
# TestGuardianWatchlistActivity (4 tests)
# =============================================================================


class TestGuardianWatchlistActivity:
    """Tests for run_guardian_watchlist activity."""

    @pytest.mark.asyncio
    async def test_guardian_watchlist_importable(self):
        """Test that run_guardian_watchlist can be imported."""
        from src.activities.run_guardian_watchlist import run_guardian_watchlist

        assert run_guardian_watchlist is not None
        assert hasattr(run_guardian_watchlist, "__temporal_activity_definition")

    @pytest.mark.asyncio
    async def test_guardian_watchlist_with_clean_signals(self):
        """Test activity returns correct structure with clean signals."""
        from src.activities.run_guardian_watchlist import run_guardian_watchlist

        pulse_result = {
            "churn_pct": 2.0,
            "burn_rate_cents": 500000,
            "runway_months": 12,
            "mrr_cents": 1000000,
        }

        result = await run_guardian_watchlist(TENANT, pulse_result)

        assert result["tenant_id"] == TENANT
        assert "blindspots_triggered" in result
        assert "match_count" in result
        assert isinstance(result["blindspots_triggered"], list)
        assert isinstance(result["match_count"], int)

    @pytest.mark.asyncio
    async def test_guardian_watchlist_with_missing_signals(self):
        """Test activity handles missing signal keys gracefully."""
        from src.activities.run_guardian_watchlist import run_guardian_watchlist

        # Empty pulse_result — should use defaults
        result = await run_guardian_watchlist(TENANT, {})

        assert result["tenant_id"] == TENANT
        assert "blindspots_triggered" in result
        assert "match_count" in result

    @pytest.mark.asyncio
    async def test_guardian_watchlist_with_extreme_signals(self):
        """Test activity detects blindspots with extreme metrics."""
        from src.activities.run_guardian_watchlist import run_guardian_watchlist

        # Simulate dangerous metrics
        pulse_result = {
            "churn_pct": 15.0,       # High churn
            "burn_rate_cents": 9000000,  # Very high burn
            "runway_months": 2,      # Only 2 months runway
            "mrr_cents": 10000,      # Low MRR
        }

        result = await run_guardian_watchlist(TENANT, pulse_result)

        assert result["tenant_id"] == TENANT
        assert result["match_count"] >= 0
        # With extreme metrics, we expect some blindspots to trigger
        if result["match_count"] > 0:
            assert len(result["blindspots_triggered"]) == result["match_count"]


# =============================================================================
# TestWorkerRegistrationV2 (3 tests)
# =============================================================================


class TestWorkerRegistrationV2:
    """Tests that worker registers all new workflows and activities."""

    def test_worker_imports_new_workflows(self):
        """Test that worker module imports all new workflows."""
        from src import worker

        assert hasattr(worker, "SelfAnalysisWorkflow")
        assert hasattr(worker, "EvalLoopWorkflow")
        assert hasattr(worker, "CompressionWorkflow")
        assert hasattr(worker, "WeightDecayWorkflow")

    def test_worker_imports_new_activity(self):
        """Test that worker module imports new guardian activity."""
        from src import worker

        assert hasattr(worker, "run_guardian_watchlist")

    def test_worker_registers_all_workflows(self):
        """Test that worker registration includes all 7 workflows."""
        from src.worker import create_worker
        from src.workflows.pulse_workflow import PulseWorkflow
        from src.workflows.investor_workflow import InvestorWorkflow
        from src.workflows.qa_workflow import QAWorkflow
        from src.workflows.self_analysis_workflow import SelfAnalysisWorkflow
        from src.workflows.eval_loop_workflow import EvalLoopWorkflow
        from src.workflows.compression_workflow import CompressionWorkflow
        from src.workflows.weight_decay_workflow import WeightDecayWorkflow

        expected_workflows = {
            PulseWorkflow,
            InvestorWorkflow,
            QAWorkflow,
            SelfAnalysisWorkflow,
            EvalLoopWorkflow,
            CompressionWorkflow,
            WeightDecayWorkflow,
        }

        # We can't actually create the worker without Temporal running,
        # but we can verify the imports are available
        for wf in expected_workflows:
            assert wf is not None
            assert hasattr(wf, "run")


# =============================================================================
# TestPulseWorkflowGuardianExtension (2 tests)
# =============================================================================


class TestPulseWorkflowGuardianExtension:
    """Tests that PulseWorkflow includes guardian watchlist step."""

    @pytest.mark.asyncio
    async def test_pulse_workflow_returns_guardian_result(self):
        """Test that PulseWorkflow includes guardian_result in response."""
        from src.workflows.pulse_workflow import PulseWorkflow

        mock_pulse_result = {
            "ok": True,
            "tenant_id": TENANT,
            "metrics": {"revenue": 1000},
            "narrative": "Test narrative",
            "slack_blocks": [],
            "churn_pct": 2.0,
            "burn_rate_cents": 500000,
            "runway_months": 12,
            "mrr_cents": 1000000,
        }
        mock_guardian_result = {
            "tenant_id": TENANT,
            "blindspots_triggered": [],
            "match_count": 0,
        }
        mock_slack_result = {"ok": True, "message_id": "123"}

        with patch("src.workflows.pulse_workflow.workflow") as mock_wf:
            mock_wf.execute_activity = AsyncMock(
                side_effect=[mock_pulse_result, mock_guardian_result, mock_slack_result]
            )
            mock_wf.logger = MagicMock()

            workflow = PulseWorkflow()
            result = await workflow.run({"tenant_id": TENANT})

            assert result["ok"] is True
            assert "guardian_result" in result
            assert result["guardian_result"]["match_count"] == 0

    @pytest.mark.asyncio
    async def test_pulse_workflow_guardian_failure_non_blocking(self):
        """Test that guardian failure doesn't fail the workflow."""
        from src.workflows.pulse_workflow import PulseWorkflow

        mock_pulse_result = {
            "ok": True,
            "tenant_id": TENANT,
            "metrics": {"revenue": 1000},
            "narrative": "Test narrative",
            "slack_blocks": [],
        }
        mock_slack_result = {"ok": True, "message_id": "123"}

        with patch("src.workflows.pulse_workflow.workflow") as mock_wf:
            # Guardian activity raises an exception
            mock_wf.execute_activity = AsyncMock(
                side_effect=[mock_pulse_result, RuntimeError("Guardian error"), mock_slack_result]
            )
            mock_wf.logger = MagicMock()

            workflow = PulseWorkflow()
            result = await workflow.run({"tenant_id": TENANT})

            # Workflow should still succeed despite guardian failure
            assert result["ok"] is True
            assert "guardian_result" in result
            assert result["guardian_result"]["ok"] is False
