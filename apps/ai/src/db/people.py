"""
People/HR database operations.

Stub implementations for TDD. Replace with real SQL when database is ready.
"""
from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


async def get_upcoming_milestones(
    founder_id: str,
    days_ahead: int = 7,
) -> List[Dict[str, Any]]:
    """
    Get upcoming HR milestones for founder's team.

    Args:
        founder_id: Founder ID
        days_ahead: Number of days to look ahead

    Returns:
        List of milestone dicts with type, employee_name, is_positive
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Get HR milestones: founder={founder_id}, days_ahead={days_ahead}")
    
    # Return stub data for testing
    return [
        {
            "type": "Work Anniversary",
            "employee_name": "Priya Sharma",
            "is_positive": True,
        },
        {
            "type": "Probation Review",
            "employee_name": "Rahul Verma",
            "is_positive": False,
        },
    ]


async def get_recent_milestones(
    founder_id: str,
    days_back: int = 7,
) -> List[Dict[str, Any]]:
    """
    Get recent positive milestones for founder.

    Args:
        founder_id: Founder ID
        days_back: Number of days to look back

    Returns:
        List of milestone dicts with description
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Get recent milestones: founder={founder_id}, days_back={days_back}")
    
    # Return stub data for testing
    return [
        {
            "description": "Closed Series A funding",
        },
    ]
