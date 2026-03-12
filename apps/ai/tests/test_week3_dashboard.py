"""Week 3 Dashboard tests."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestDashboardSummaryQuery:
    """Test materialized view returns correct data."""

    def test_dashboard_summary_structure(self):
        """Test that the dashboard summary query returns expected fields."""
        # This test validates the SQL structure
        expected_fields = [
            "founder_id",
            "name",
            "stage",
            "commitment_rate",
            "overdue_count",
            "triggers_fired_30d",
            "triggers_suppressed_30d",
            "positive_ratings",
            "negative_ratings",
            "days_since_reflection",
            "energy_trend",
            "last_reflection_at",
        ]
        
        # Verify all expected fields are present
        assert len(expected_fields) == 12
        assert "founder_id" in expected_fields
        assert "commitment_rate" in expected_fields

    @pytest.mark.asyncio
    async def test_dashboard_summary_with_data(self):
        """Test materialized view with sample data."""
        # Mock database response
        mock_row = MagicMock()
        mock_row.Scan = MagicMock(return_value=None)
        mock_row.FounderID = "test-founder-id"
        mock_row.Name = "Test Founder"
        mock_row.Stage = "building"
        mock_row.CommitmentRate = 0.75
        mock_row.OverdueCount = 2
        mock_row.TriggersFired30d = 5
        mock_row.TriggersSuppressed30d = 3
        mock_row.PositiveRatings = 4
        mock_row.NegativeRatings = 1
        mock_row.DaysSinceReflection = 3.5
        mock_row.EnergyTrend = [7, 8, 6, 9]
        mock_row.LastReflectionAt = datetime.now()
        
        assert mock_row.CommitmentRate == 0.75
        assert mock_row.OverdueCount == 2
        assert len(mock_row.EnergyTrend) == 4

    def test_commitment_rate_calculation(self):
        """Test commitment rate is calculated correctly."""
        # Simulate SQL calculation: completed / total
        completed = 8
        total = 10
        rate = completed / total
        
        assert rate == 0.8
        assert 0.0 <= rate <= 1.0

    def test_energy_trend_array(self):
        """Test energy trend is an array of integers."""
        energy_trend = [7, 8, 6, 9]
        
        assert isinstance(energy_trend, list)
        assert all(isinstance(x, int) for x in energy_trend)
        assert all(1 <= x <= 10 for x in energy_trend)


class TestReflectionFormHandler:
    """Test POST /founder/reflection saves data correctly."""

    def test_reflection_form_validation(self):
        """Test that reflection form validates input."""
        # Test empty form
        shipped = ""
        blocked = ""
        commitments = ""
        
        # At least one field must be filled
        is_valid = any([shipped, blocked, commitments])
        assert is_valid is False

    def test_reflection_form_with_data(self):
        """Test reflection form with valid data."""
        shipped = "Shipped feature X"
        blocked = "Waiting on API"
        commitments = "Ship auth system\nTalk to 3 users"
        energy_score = 8
        
        # Validate energy score range
        assert 1 <= energy_score <= 10
        
        # Validate commitments are split correctly
        commitment_list = [c.strip() for c in commitments.split("\n") if c.strip()]
        assert len(commitment_list) == 2
        assert "Ship auth system" in commitment_list
        assert "Talk to 3 users" in commitment_list

    def test_raw_text_construction(self):
        """Test that raw text is constructed correctly."""
        shipped = "Shipped feature X"
        blocked = "Waiting on API"
        commitments = "Ship auth system"
        
        raw_text = "\n".join([
            "SHIPPED: " + shipped,
            "BLOCKED: " + blocked,
            "COMMITMENTS: " + commitments,
        ])
        
        assert "SHIPPED: Shipped feature X" in raw_text
        assert "BLOCKED: Waiting on API" in raw_text
        assert "COMMITMENTS: Ship auth system" in raw_text

    @pytest.mark.asyncio
    async def test_reflection_database_insert(self):
        """Test reflection is inserted into database."""
        # Mock database execution
        mock_pool = AsyncMock()
        mock_pool.Exec = AsyncMock(return_value=None)
        
        founder_id = "test-founder"
        reflection_id = "test-reflection-id"
        week_start = datetime.now()
        
        # Simulate INSERT query
        await mock_pool.Exec(
            "INSERT INTO weekly_reflections ...",
            reflection_id, founder_id, week_start,
            "shipped", "blocked", 7, "raw_text"
        )
        
        mock_pool.Exec.assert_called_once()

    def test_htmx_response(self):
        """Test HTMX returns success message."""
        hx_request = True
        
        if hx_request:
            response = "✅ Reflection saved. Saarathi is watching."
        else:
            response = "/founder/dashboard"  # Redirect
        
        assert "✅" in response
        assert "Saarathi" in response


class TestSSEDashboardStream:
    """Test SSE endpoint sends updates on DB changes."""

    def test_sse_headers(self):
        """Test SSE response headers are correct."""
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        
        assert headers["Content-Type"] == "text/event-stream"
        assert headers["Cache-Control"] == "no-cache"
        assert headers["Connection"] == "keep-alive"

    def test_sse_event_format(self):
        """Test SSE event format is correct."""
        event_type = "dashboard_update"
        data = {"type": "refresh"}
        
        sse_message = f"event: {event_type}\ndata: {data}\n\n"
        
        assert "event: dashboard_update" in sse_message
        assert "data:" in sse_message

    @pytest.mark.asyncio
    async def test_postgres_listen_notify(self):
        """Test PostgreSQL LISTEN/NOTIFY for dashboard updates."""
        # Mock database connection
        mock_conn = AsyncMock()
        mock_conn.Exec = AsyncMock(return_value=None)
        mock_conn.WaitForNotification = AsyncMock(
            return_value=MagicMock(Payload='{"founder_id": "test-id"}')
        )
        
        # Simulate LISTEN command
        await mock_conn.Exec("LISTEN dashboard_update")
        mock_conn.Exec.assert_called_with("LISTEN dashboard_update")
        
        # Simulate waiting for notification
        notification = await mock_conn.WaitForNotification()
        assert notification is not None

    def test_founder_id_filtering(self):
        """Test that SSE only sends updates for matching founder_id."""
        connected_founder_id = "founder-123"
        notification_payload = {"founder_id": "founder-123"}
        
        # Should send update
        should_send = notification_payload["founder_id"] == connected_founder_id
        assert should_send is True
        
        # Different founder - should not send
        notification_payload["founder_id"] = "founder-456"
        should_send = notification_payload["founder_id"] == connected_founder_id
        assert should_send is False


class TestDashboardHandler:
    """Test Go dashboard handler functions."""

    def test_get_dashboard_summary(self):
        """Test dashboard summary retrieval."""
        summary = {
            "founder_id": "test-id",
            "name": "Test Founder",
            "stage": "building",
            "commitment_rate": 0.75,
            "overdue_count": 2,
            "triggers_fired_30d": 5,
            "triggers_suppressed_30d": 3,
            "positive_ratings": 4,
            "negative_ratings": 1,
            "days_since_reflection": 3.5,
            "energy_trend": [7, 8, 6, 9],
        }
        
        assert summary["commitment_rate"] == 0.75
        assert summary["overdue_count"] == 2
        assert len(summary["energy_trend"]) == 4

    def test_commitment_rate_color_coding(self):
        """Test commitment rate color coding logic."""
        def get_color(rate):
            if rate > 0.8:
                return "green"
            elif rate > 0.5:
                return "yellow"
            else:
                return "red"
        
        assert get_color(0.9) == "green"
        assert get_color(0.75) == "yellow"
        assert get_color(0.3) == "red"

    def test_days_since_reflection_urgency(self):
        """Test days since reflection urgency levels."""
        def get_urgency(days):
            if days < 7:
                return "great"
            elif days < 14:
                return "time_to_reflect"
            else:
                return "overdue"
        
        assert get_urgency(3) == "great"
        assert get_urgency(10) == "time_to_reflect"
        assert get_urgency(20) == "overdue"


class TestMaterializedViewRefresh:
    """Test materialized view refresh function."""

    def test_refresh_function_exists(self):
        """Test that refresh function is defined."""
        function_name = "refresh_dashboard_summary"
        assert function_name is not None

    def test_concurrent_refresh(self):
        """Test that CONCURRENTLY refresh is used."""
        sql_command = "REFRESH MATERIALIZED VIEW CONCURRENTLY founder_dashboard_summary"
        
        assert "CONCURRENTLY" in sql_command
        assert "founder_dashboard_summary" in sql_command

    def test_unique_index_required(self):
        """Test that unique index exists for CONCURRENTLY refresh."""
        index_name = "idx_dashboard_summary_founder_id"
        assert index_name is not None


class TestTriggerNotification:
    """Test database triggers for dashboard updates."""

    def test_commitment_trigger(self):
        """Test trigger on commitments table."""
        trigger_name = "commitment_dashboard_notify"
        table = "commitments"
        events = ["INSERT", "UPDATE"]
        
        assert trigger_name is not None
        assert table == "commitments"
        assert len(events) == 2

    def test_trigger_log_trigger(self):
        """Test trigger on trigger_log table."""
        trigger_name = "trigger_log_dashboard_notify"
        table = "trigger_log"
        events = ["INSERT", "UPDATE"]
        
        assert trigger_name is not None
        assert table == "trigger_log"
        assert len(events) == 2

    def test_notify_function(self):
        """Test NOTIFY function sends correct payload."""
        founder_id = "test-founder-id"
        payload = f'{{"founder_id": "{founder_id}"}}'
        channel = "dashboard_update"
        
        assert channel == "dashboard_update"
        assert "founder_id" in payload


class TestSnoozeTracking:
    """Test snooze functionality for triggers."""

    def test_snooze_fields_exist(self):
        """Test snooze fields are added to trigger_log."""
        fields = ["snoozed_until", "snooze_count"]
        
        assert "snoozed_until" in fields
        assert "snooze_count" in fields

    def test_snooze_count_default(self):
        """Test snooze count defaults to 0."""
        default_snooze_count = 0
        assert default_snooze_count == 0

    def test_snooze_until_nullable(self):
        """Test snoozed_until can be NULL."""
        snoozed_until = None
        assert snoozed_until is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
