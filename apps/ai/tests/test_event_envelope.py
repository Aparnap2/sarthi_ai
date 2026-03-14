"""Test suite for Event Envelope schema."""
import pytest, uuid
from datetime import datetime, timezone
from src.schemas.event_envelope import EventEnvelope, EventSource


class TestEventEnvelope:

    def _valid(self, **overrides):
        base = dict(
            event_id=str(uuid.uuid4()),
            founder_id=str(uuid.uuid4()),
            source=EventSource.RAZORPAY,
            event_name="payment.captured",
            topic="finance.revenue.captured",
            sop_name="SOP_REVENUE_RECEIVED",
            payload_ref="raw_events:abc123",
            payload_hash="sha256:deadbeef",
            occurred_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            trace_id=str(uuid.uuid4()),
            idempotency_key="razorpay:pay_abc123:v1",
        )
        base.update(overrides)
        return base

    def test_valid_envelope_passes(self):
        env = EventEnvelope(**self._valid())
        assert env.source == EventSource.RAZORPAY
        assert env.sop_name == "SOP_REVENUE_RECEIVED"
        assert env.payload_ref == "raw_events:abc123"

    def test_empty_event_name_raises(self):
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(event_name=""))

    def test_whitespace_event_name_raises(self):
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(event_name="   "))

    def test_raw_json_as_payload_ref_raises(self):
        """payload_ref must be a storage ref, not inline JSON"""
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(payload_ref='{"amount":5000}'))

    def test_raw_json_array_as_payload_ref_raises(self):
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(payload_ref='[{"txn": "abc"}]'))

    def test_invalid_prefix_payload_ref_raises(self):
        with pytest.raises(Exception):
            EventEnvelope(**self._valid(payload_ref="invalid:ref"))

    def test_valid_raw_events_prefix(self):
        env = EventEnvelope(**self._valid(payload_ref="raw_events:uuid-123"))
        assert env.payload_ref == "raw_events:uuid-123"

    def test_valid_files_prefix(self):
        env = EventEnvelope(**self._valid(payload_ref="files:/path/to/file.pdf"))
        assert env.payload_ref == "files:/path/to/file.pdf"

    def test_all_event_sources_valid(self):
        for src in EventSource:
            env = EventEnvelope(**self._valid(source=src))
            assert env.source == src

    def test_version_defaults_to_v1(self):
        env = EventEnvelope(**self._valid())
        assert env.version == "v1"
