"""
Finance Agent State for Sarthi v1.0.

Defines the TypedDict state machine for the Finance Agent LangGraph.
No external imports needed — pure Python typing.
"""
from typing import TypedDict


class FinanceState(TypedDict):
    """
    State machine for Finance Agent.

    Fields:
        tenant_id:             Tenant identifier for multi-tenant isolation
        event:                 Incoming event dict (event_type, vendor, amount, etc.)
        monthly_revenue:       Last 30-day revenue in INR
        monthly_expense:       Last 30-day expenses in INR
        burn_rate:             Monthly burn rate in INR
        runway_months:         Cash runway in months (cash / burn)
        vendor_baselines:      Dict[vendor → {avg_30d, avg_90d, count}]
        anomaly_detected:      True if anomaly score >= 0.5
        anomaly_score:         Anomaly score 0.0 – 1.0
        anomaly_explanation:   LLM-generated plain English explanation
        past_context:          List of past anomalies from Qdrant
        action:                ALERT | DIGEST | SKIP
        output_message:        Formatted Telegram message
        langfuse_trace_id:     Langfuse trace ID for observability
    """
    tenant_id:             str
    event:                 dict
    monthly_revenue:       float
    monthly_expense:       float
    burn_rate:             float
    runway_months:         float
    vendor_baselines:      dict
    anomaly_detected:      bool
    anomaly_score:         float
    anomaly_explanation:   str
    past_context:          list
    action:                str
    output_message:        str
    langfuse_trace_id:     str
