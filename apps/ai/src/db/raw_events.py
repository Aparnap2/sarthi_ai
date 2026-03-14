"""
Raw events database operations.

Stub implementations for TDD. Replace with real SQL when database is ready.
"""
from __future__ import annotations
from typing import Optional, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)


def fetch_raw_event_by_id(event_id: str) -> Dict[str, Any]:
    """
    Fetch raw event by UUID.

    Args:
        event_id: Event UUID

    Returns:
        Parsed payload dict

    Raises:
        ValueError: If event not found
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Fetch raw event: event_id={event_id}")
    # Return empty dict for TDD - tests will mock this
    return {}


async def insert_raw_event(
    founder_id: str,
    source: str,
    event_name: str,
    topic: str,
    sop_name: str,
    payload: Dict[str, Any],
) -> str:
    """
    Insert raw event into PostgreSQL.

    Args:
        founder_id: Founder ID
        source: Event source (telegram, razorpay, etc.)
        event_name: Event name (e.g., "payment.captured")
        topic: Topic for routing
        sop_name: SOP to handle this event
        payload: Event payload

    Returns:
        Event UUID
    """
    # Stub for TDD
    logger.debug(f"Insert raw event: founder={founder_id}, event={event_name}")
    return str(uuid.uuid4())
