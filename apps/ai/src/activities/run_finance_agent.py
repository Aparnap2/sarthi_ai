"""
Finance Agent Activity for Temporal.

Wraps the Finance LangGraph agent as a Temporal activity.
LangGraph invoke is sync — wrapped with asyncio.get_event_loop().run_in_executor().
"""
import asyncio
from typing import Any

from temporalio import activity

from src.agents.finance.graph import finance_graph
from src.agents.finance.state import FinanceState


@activity.defn(name="run_finance_agent")
async def run_finance_agent(tenant_id: str, event: dict) -> dict[str, Any]:
    """
    Execute the Finance Agent LangGraph for anomaly detection.

    This activity:
    1. Initializes FinanceState with tenant_id and event
    2. Invokes the finance_graph LangGraph
    3. Returns the output with action, anomaly_score, and output_message

    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        event: Payment event dict with event_type, vendor, amount, currency, timestamp

    Returns:
        dict with keys:
            - tenant_id: str
            - action: ALERT | DIGEST | SKIP
            - anomaly_score: float (0.0 - 1.0)
            - anomaly_detected: bool
            - output_message: str (formatted Telegram message)
            - langfuse_trace_id: str

    Raises:
        ValueError: If tenant_id is missing or empty
        Exception: Propagates any LangGraph execution errors
    """
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required and cannot be empty")

    # Initialize state
    initial_state: FinanceState = {
        "tenant_id": tenant_id,
        "event": event,
        "monthly_revenue": 0.0,
        "monthly_expense": 0.0,
        "burn_rate": 0.0,
        "runway_months": 0.0,
        "vendor_baselines": {},
        "anomaly_detected": False,
        "anomaly_score": 0.0,
        "anomaly_explanation": "",
        "past_context": [],
        "action": "DIGEST",
        "output_message": "",
        "langfuse_trace_id": "",
    }

    # LangGraph invoke is sync — run in executor to avoid blocking event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: finance_graph.invoke(initial_state),
    )

    # Return only the required output fields
    return {
        "tenant_id": result.get("tenant_id", tenant_id),
        "action": result.get("action", "DIGEST"),
        "anomaly_score": result.get("anomaly_score", 0.0),
        "anomaly_detected": result.get("anomaly_detected", False),
        "output_message": result.get("output_message", ""),
        "langfuse_trace_id": result.get("langfuse_trace_id", ""),
    }
