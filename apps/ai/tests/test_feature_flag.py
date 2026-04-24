"""
Tests for APScheduler feature flag and bootstrap.

Verifies:
1. USE_APSCHEDULER environment variable forks correctly
2. Bootstrap loads all active tenants
"""
import pytest
import os
from unittest.mock import patch, AsyncMock


def test_apscheduler_env_enabled(monkeypatch):
    """USE_APSCHEDULER=true should activate APScheduler backend."""
    monkeypatch.setenv("USE_APSCHEDULER", "true")

    # Re-import to pick up env var
    import importlib
    import apps.ai.src.main as main_module
    importlib.reload(main_module)

    # Check that USE_SCHEDULER is set
    assert main_module.USE_SCHEDULER is True, \
        "USE_APSCHEDULER=true did not activate APScheduler backend"


def test_apscheduler_env_disabled(monkeypatch):
    """USE_APSCHEDULER=false should fall back to Temporal."""
    monkeypatch.setenv("USE_APSCHEDULER", "false")

    # Re-import to pick up env var
    import importlib
    import apps.ai.src.main as main_module
    importlib.reload(main_module)

    # Check that USE_SCHEDULER is not set
    assert main_module.USE_SCHEDULER is False, \
        "USE_APSCHEDULER=false did not disable APScheduler"


@pytest.mark.asyncio
async def test_bootstrap_registers_all_tenants():
    """Every active tenant must get jobs registered at startup."""
    active_tenants = ["tenant-1", "tenant-2", "tenant-3"]

    mock_register = AsyncMock()

    with patch("apps.ai.src.main.register_tenant_schedules", mock_register), \
         patch("apps.ai.src.main.start_scheduler"):

        from apps.ai.src.main import bootstrap_scheduler

        await bootstrap_scheduler()

        assert mock_register.call_count == len(active_tenants), \
            f"Expected {len(active_tenants)} registrations, got {mock_register.call_count}"

        for tenant_id in active_tenants:
            mock_register.assert_any_call(tenant_id)


@pytest.mark.asyncio
async def test_bootstrap_empty_tenants():
    """Empty tenant list must not raise."""
    mock_register = AsyncMock()

    with patch("apps.ai.src.main.register_tenant_schedules", mock_register), \
         patch("os.environ.get", return_value=""), \
         patch("apps.ai.src.main.start_scheduler"):

        from apps.ai.src.main import bootstrap_scheduler

        # With no tenants, should use "default"
        await bootstrap_scheduler()

        # Should register "default" tenant
        mock_register.assert_called_with("default")


@pytest.mark.asyncio
async def test_bootstrap_single_tenant():
    """Single tenant should work correctly."""
    mock_register = AsyncMock()

    with patch("apps.ai.src.main.register_tenant_schedules", mock_register), \
         patch("apps.ai.src.main.start_scheduler"):

        from apps.ai.src.main import bootstrap_scheduler

        await bootstrap_scheduler()

        # Should register exactly once
        mock_register.assert_called_once()


def test_orchestration_backend_detection():
    """Backend should be detected based on environment."""
    import os

    # Test with APScheduler enabled
    original = os.environ.get("USE_APSCHEDULER")
    try:
        os.environ["USE_APSCHEDULER"] = "true"

        import importlib
        import apps.ai.src.main as main_module
        importlib.reload(main_module)

        assert main_module.USE_SCHEDULER is True

        # Test with APScheduler disabled
        os.environ["USE_APSCHEDULER"] = "false"
        importlib.reload(main_module)

        assert main_module.USE_SCHEDULER is False

    finally:
        if original is not None:
            os.environ["USE_APSCHEDULER"] = original
        elif "USE_APSCHEDULER" in os.environ:
            del os.environ["USE_APSCHEDULER"]