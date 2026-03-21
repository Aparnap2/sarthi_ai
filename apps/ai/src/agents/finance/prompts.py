"""
DSPy Prompts for Finance Agent.

Defines signature classes for:
- AnomalyExplainer: Explains financial anomalies to founders
- FinanceDigestWriter: Writes weekly finance digests

Uses DSPy ChainOfThought for systematic prompt compilation.
"""
import dspy


class AnomalyExplainer(dspy.Signature):
    """
    Explain a financial anomaly to a startup founder.
    Plain English only. Max 3 sentences. No jargon.
    Reference past context if provided.
    Never use: leverage, synergy, utilize, streamline, paradigm.
    """
    event_type:    str   = dspy.InputField(
        desc="Type of financial event e.g. BANK_WEBHOOK, EXPENSE_RECORDED")
    vendor:        str   = dspy.InputField(
        desc="Vendor or merchant name")
    amount:        float = dspy.InputField(
        desc="Transaction amount in INR")
    avg_90d:       float = dspy.InputField(
        desc="90-day average spend for this vendor in INR, 0 if first time")
    anomaly_score: float = dspy.InputField(
        desc="Anomaly score between 0.0 and 1.0")
    past_context:  str   = dspy.InputField(
        desc="Past memory from Qdrant about this vendor. 'No history' if none.")
    runway_months: float = dspy.InputField(
        desc="Current cash runway in months")

    explanation: str = dspy.OutputField(
        desc=(
            "1-3 sentence plain English explanation. "
            "Mention the multiple (e.g. 2.3x usual). "
            "Reference past context if available. "
            "End with one concrete action hint."
        )
    )


class FinanceDigestWriter(dspy.Signature):
    """
    Write a concise weekly finance digest for a startup founder.
    Bullet points only. Max 5 bullets. Numbers must be exact. No jargon.
    """
    mrr:              float = dspy.InputField(
        desc="Monthly Recurring Revenue in INR")
    burn_rate:        float = dspy.InputField(
        desc="Monthly burn rate in INR")
    runway_months:    float = dspy.InputField(
        desc="Runway in months")
    wow_revenue_pct:  float = dspy.InputField(
        desc="Week-over-week revenue change as a percentage, e.g. 12.5 or -8.3")
    top_expenses:     str   = dspy.InputField(
        desc="Top 3 expense categories as a comma-separated string")

    digest: str = dspy.OutputField(
        desc=(
            "Weekly digest with 3-5 bullets. "
            "Each bullet starts with an emoji (🔴🟡🟢). "
            "Include exact INR numbers. "
            "Last bullet must be one actionable recommendation."
        )
    )
