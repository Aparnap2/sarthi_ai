"""
Canonical Event Envelope for Sarthi SOP Runtime.

This is the ONLY shape that flows through Redpanda and Temporal.
PayloadRef points to raw_events table — NEVER contains raw JSON.
"""
from __future__ import annotations
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, field_validator


class EventSource(str, Enum):
    """All event sources in Sarthi."""
    RAZORPAY         = "razorpay"
    ZOHO_BOOKS       = "zoho_books"
    GOOGLE_WORKSPACE = "google_workspace"
    ESIGN            = "esign"
    TELEGRAM         = "telegram"
    CRON             = "cron"
    AWS_COST         = "aws_cost"
    EMAIL_FORWARD    = "email_forward"


class EventEnvelope(BaseModel):
    """
    Canonical event envelope for all Sarthi events.

    Attributes:
        event_id: Unique event identifier (UUID)
        founder_id: Founder who owns this event (UUID)
        source: Event source (razorpay, zoho_books, etc.)
        event_name: Event name from source (e.g., "payment.captured")
        topic: Redpanda topic to publish to
        sop_name: SOP to execute (e.g., "SOP_REVENUE_RECEIVED")
        payload_ref: Storage reference ("raw_events:<uuid>" or "files:<path>")
                     NEVER raw JSON — store in PostgreSQL first
        payload_hash: SHA-256 hash of raw payload
        occurred_at: When the event occurred (from source)
        received_at: When Sarthi received the event
        trace_id: Distributed tracing ID (for Langfuse)
        idempotency_key: Deduplication key (e.g., "razorpay:pay_abc:v1")
        version: Envelope schema version (default "v1")
    """
    event_id:        str
    founder_id:      str
    source:          EventSource
    event_name:      str
    topic:           str
    sop_name:        str
    payload_ref:     str
    payload_hash:    str
    occurred_at:     datetime
    received_at:     datetime
    trace_id:        str
    idempotency_key: str
    version:         str = "v1"

    @field_validator("event_name")
    @classmethod
    def event_name_not_empty(cls, v: str) -> str:
        """Event name must not be empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("event_name must not be empty")
        return v

    @field_validator("payload_ref")
    @classmethod
    def payload_ref_is_storage_ref(cls, v: str) -> str:
        """
        payload_ref must be a storage reference, not raw JSON.

        Valid prefixes:
        - raw_events:<uuid>  — Reference to raw_events table
        - files:<path>       — File system path
        - s3:<bucket>/<key>  — S3 reference
        - pg:<table>:<id>    — PostgreSQL reference

        Raises:
            ValueError: If payload_ref contains raw JSON
        """
        VALID = ("raw_events:", "files:", "s3:", "pg:")
        if v.lstrip().startswith(("{", "[")):
            raise ValueError(
                "payload_ref must be a storage reference like 'raw_events:<uuid>', "
                "not raw JSON. Store in PostgreSQL first."
            )
        if not any(v.startswith(p) for p in VALID):
            raise ValueError(
                f"payload_ref must start with one of {VALID}. Got: {v!r}"
            )
        return v

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
