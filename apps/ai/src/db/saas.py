"""
SaaS/IT database operations.

Stub implementations for TDD. Replace with real SQL when database is ready.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


async def get_unused_tools(
    founder_id: str,
    days_unused: int = 60,
) -> List[Dict[str, Any]]:
    """
    Get SaaS tools that haven't been used in specified days.

    Args:
        founder_id: Founder ID
        days_unused: Number of days of inactivity

    Returns:
        List of tool dicts with name, monthly_cost
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Get unused tools: founder={founder_id}, days_unused={days_unused}")
    
    # Return stub data for testing
    return [
        {
            "name": "Figma Pro",
            "monthly_cost": 1500,
        },
        {
            "name": "Notion AI",
            "monthly_cost": 800,
        },
    ]


async def get_cloud_spend_delta(
    founder_id: str,
) -> Optional[float]:
    """
    Get cloud spend delta (percentage increase from previous month).

    Args:
        founder_id: Founder ID

    Returns:
        Delta as decimal (e.g., 0.30 for 30% increase) or None if no data
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Get cloud spend delta: founder={founder_id}")
    
    # Return stub data for testing (35% increase)
    return 0.35
