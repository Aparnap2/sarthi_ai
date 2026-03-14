"""
Transaction database operations.

Stub implementations for TDD. Replace with real SQL when database is ready.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def insert_transaction(
    founder_id: str,
    txn_date: Optional[str],
    description: str,
    debit: float,
    credit: float,
    category: str,
    category_confidence: float,
    source: str,
    external_id: str,
    needs_review: bool = False,
    raw_event_id: Optional[str] = None,
) -> None:
    """
    Insert a transaction into PostgreSQL.

    Args:
        founder_id: Founder who owns this transaction
        txn_date: Transaction date (YYYY-MM-DD)
        description: Transaction description
        debit: Debit amount (0 for credits)
        credit: Credit amount (0 for debits)
        category: Transaction category
        category_confidence: Confidence score (0.0-1.0)
        source: Source system (bank_statement, razorpay, etc.)
        external_id: External reference ID
        needs_review: Whether transaction needs manual review
        raw_event_id: Reference to raw_events table
    """
    # Stub for TDD - replace with real SQL
    logger.debug(
        f"Insert transaction: founder={founder_id}, desc={description[:50]}, "
        f"debit={debit}, credit={credit}, category={category}"
    )


def transaction_exists(
    founder_id: str,
    date: Optional[str],
    amount: float,
    description: str,
) -> bool:
    """
    Check if transaction already exists (deduplication).

    Args:
        founder_id: Founder who owns this transaction
        date: Transaction date
        amount: Transaction amount
        description: Transaction description

    Returns:
        True if duplicate found, False otherwise
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Check duplicate: founder={founder_id}, date={date}, amount={amount}")
    return False


def get_current_mrr(founder_id: str) -> float:
    """
    Get current MRR for founder.

    Args:
        founder_id: Founder ID

    Returns:
        Current MRR in INR
    """
    # Stub for TDD
    logger.debug(f"Get MRR for founder={founder_id}")
    return 0.0


def get_90d_revenue_by_customer(founder_id: str, customer_id: str) -> float:
    """
    Get 90-day revenue from a specific customer.

    Args:
        founder_id: Founder ID
        customer_id: Customer ID

    Returns:
        Total revenue from customer in last 90 days
    """
    # Stub for TDD
    logger.debug(f"Get 90d revenue: founder={founder_id}, customer={customer_id}")
    return 0.0


def get_transaction_by_external_id(
    founder_id: str,
    external_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get transaction by external ID.

    Args:
        founder_id: Founder ID
        external_id: External reference ID

    Returns:
        Transaction dict or None if not found
    """
    # Stub for TDD
    logger.debug(f"Get transaction: founder={founder_id}, external_id={external_id}")
    return None


def count_transactions(founder_id: str) -> int:
    """
    Count total transactions for founder.

    Args:
        founder_id: Founder ID

    Returns:
        Total transaction count
    """
    # Stub for TDD
    logger.debug(f"Count transactions: founder={founder_id}")
    return 0


async def get_overdue_invoices(
    founder_id: str,
) -> List[Dict[str, Any]]:
    """
    Get overdue invoices for founder.

    Args:
        founder_id: Founder ID

    Returns:
        List of invoice dicts with vendor, amount, days_overdue
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Get overdue invoices: founder={founder_id}")
    
    # Return stub data for testing
    return [
        {
            "vendor": "Acme Corp",
            "amount": 50000,
            "days_overdue": 15,
        },
        {
            "vendor": "TechVendor Ltd",
            "amount": 75000,
            "days_overdue": 30,
        },
    ]


async def get_monthly_burn(founder_id: str) -> float:
    """
    Get monthly burn rate for founder.

    Args:
        founder_id: Founder ID

    Returns:
        Monthly burn in INR
    """
    # Stub for TDD - replace with real SQL
    logger.debug(f"Get monthly burn: founder={founder_id}")
    return 50000.0  # ₹50,000 default


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
            "description": "Hit ₹5L MRR",
        },
    ]
