"""Test suite for Event Envelope schema (v1.0)."""
import pytest
import uuid
from datetime import datetime, timezone
from src.schemas.event_envelope import EventEnvelope, EventSource


class TestEventEnvelope:

    def _valid(self, **overrides):
        """Create valid envelope with defaults."""
        base = dict(
            tenant_id="tenant_test",
            event_type="PAYMENT_SUCCESS",
            source=EventSource.RAZORPAY,
            payload_ref="raw_events:abc123",
            payload_hash="sha256:deadbeef",
            idempotency_key="razorpay:pay_abc123:v1",
            occurred_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            trace_id="trace_test",
        )
        base.update(overrides)
        return base

    def test_valid_envelope_passes(self):
        """Valid envelope should pass validation."""
        env = EventEnvelope(**self._valid())
        assert env.tenant_id == "tenant_test"
        assert env.event_type == "PAYMENT_SUCCESS"
        assert env.source == EventSource.RAZORPAY

    def test_empty_event_type_fails(self):
        """Empty event_type should fail validation."""
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(event_type=""))

    def test_whitespace_event_type_fails(self):
        """Whitespace-only event_type should fail validation."""
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(event_type="   "))

    def test_raw_json_as_payload_ref_fails(self):
        """Raw JSON as payload_ref should fail validation."""
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(payload_ref='{"amount":5000}'))

    def test_raw_json_array_as_payload_ref_fails(self):
        """Raw JSON array as payload_ref should fail validation."""
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(payload_ref='[{"txn": "abc"}]'))

    def test_invalid_prefix_payload_ref_fails(self):
        """Invalid prefix should fail validation."""
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(payload_ref="invalid:ref"))

    def test_valid_raw_events_prefix(self):
        """Valid raw_events: prefix should pass."""
        env = EventEnvelope(**self._valid(payload_ref="raw_events:uuid-123"))
        assert env.payload_ref == "raw_events:uuid-123"

    def test_valid_files_prefix(self):
        """Valid files: prefix should pass."""
        env = EventEnvelope(**self._valid(payload_ref="files:/path/to/file.pdf"))
        assert env.payload_ref == "files:/path/to/file.pdf"

    def test_all_event_sources_valid(self):
        """All EventSource values should be valid."""
        for src in EventSource:
            env = EventEnvelope(**self._valid(source=src))
            assert env.source == src
