"""
Compliance database operations.

Stub implementations for TDD. Replace with real SQL when database is ready.
"""
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


async def get_upcoming_deadlines(
    founder_id: str,
    days_ahead: int = 14,
) -> List[Dict[str, Any]]:
    """
    Get upcoming compliance deadlines for founder.

    Args:
        founder_id: Founder ID
        days_ahead: Number of days to look ahead

    Returns:
        List of deadline dicts with filing_type, due_date, days_remaining, today
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Get compliance deadlines: founder={founder_id}, days_ahead={days_ahead}")
    
    today = datetime.now(timezone.utc).date()
    
    # Return stub data for testing
    return [
        {
            "filing_type": "GST_MONTHLY",
            "due_date": today + timedelta(days=8),
            "today": today,
        },
        {
            "filing_type": "TDS_QUARTERLY",
            "due_date": today + timedelta(days=20),
            "today": today,
        },
    ]
