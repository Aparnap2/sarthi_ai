"""
Anomaly Explanation Eval Dataset.

20 scenarios with gold criteria for evaluating finance anomaly explanations.
Each scenario includes:
- Input: Event details and context
- Gold criteria: Required elements in the explanation
- Expected score threshold

Run with:
    cd apps/ai && uv run python tests/evals/run_evals.py
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class AnomalyEvalScenario:
    """Single anomaly explanation evaluation scenario."""
    id: str
    event_type: str
    vendor: str
    amount: float
    avg_90d: float
    anomaly_score: float
    runway_months: float
    past_context: str
    gold_criteria: List[str]  # Required elements in explanation
    expected_action: str  # ALERT, DIGEST, or SKIP


# 20 evaluation scenarios
ANOMALY_EVAL_SCENARIOS: List[AnomalyEvalScenario] = [
    # Scenario 1: Classic 2x spend spike
    AnomalyEvalScenario(
        id="anomaly_001",
        event_type="payment.success",
        vendor="aws",
        amount=10000.0,
        avg_90d=5000.0,
        anomaly_score=0.7,
        runway_months=12.0,
        past_context="No similar anomalies in past 90 days",
        gold_criteria=[
            "mentions '2x' or 'double' or '100% increase'",
            "mentions vendor name 'AWS'",
            "mentions specific amounts ($10,000 vs $5,000)",
            "suggests checking usage or investigating cause",
        ],
        expected_action="ALERT",
    ),
    # Scenario 2: First-time vendor
    AnomalyEvalScenario(
        id="anomaly_002",
        event_type="payment.success",
        vendor="new-saas-vendor",
        amount=2000.0,
        avg_90d=0.0,
        anomaly_score=0.5,
        runway_months=8.0,
        past_context="No history for this vendor",
        gold_criteria=[
            "mentions 'first time' or 'new vendor'",
            "mentions vendor name",
            "mentions amount $2,000",
            "suggests verifying subscription or approval",
        ],
        expected_action="ALERT",
    ),
    # Scenario 3: Low runway urgency
    AnomalyEvalScenario(
        id="anomaly_003",
        event_type="payment.success",
        vendor="stripe",
        amount=8000.0,
        avg_90d=4000.0,
        anomaly_score=0.8,
        runway_months=2.5,
        past_context="Previous anomaly 30 days ago, resolved",
        gold_criteria=[
            "mentions '2x' or 'double'",
            "mentions low runway or urgency",
            "mentions runway < 3 months",
            "recommends immediate action",
        ],
        expected_action="ALERT",
    ),
    # Scenario 4: Moderate spike with history
    AnomalyEvalScenario(
        id="anomaly_004",
        event_type="payment.success",
        vendor="google-cloud",
        amount=7500.0,
        avg_90d=5000.0,
        anomaly_score=0.5,
        runway_months=10.0,
        past_context="Similar spike 60 days ago due to ML training",
        gold_criteria=[
            "mentions 1.5x or 50% increase",
            "references past similar event",
            "mentions ML or training if in context",
            "suggests checking if expected",
        ],
        expected_action="DIGEST",
    ),
    # Scenario 5: Small variance (not anomaly)
    AnomalyEvalScenario(
        id="anomaly_005",
        event_type="payment.success",
        vendor="aws",
        amount=5200.0,
        avg_90d=5000.0,
        anomaly_score=0.2,
        runway_months=12.0,
        past_context="Regular monthly spend, consistent",
        gold_criteria=[
            "mentions normal or expected",
            "mentions within variance",
            "no alarm or urgency",
        ],
        expected_action="SKIP",
    ),
    # Scenario 6: Time tick weekly digest
    AnomalyEvalScenario(
        id="anomaly_006",
        event_type="TIME_TICK_WEEKLY",
        vendor="",
        amount=0.0,
        avg_90d=0.0,
        anomaly_score=0.0,
        runway_months=9.0,
        past_context="",
        gold_criteria=[
            "mentions weekly brief or summary",
            "includes revenue/burn/runway numbers",
            "no alarm language",
        ],
        expected_action="DIGEST",
    ),
    # Scenario 7: Critical runway situation
    AnomalyEvalScenario(
        id="anomaly_007",
        event_type="payment.success",
        vendor="azure",
        amount=15000.0,
        avg_90d=6000.0,
        anomaly_score=0.9,
        runway_months=1.8,
        past_context="Multiple anomalies in past 30 days",
        gold_criteria=[
            "mentions 2.5x or 150% increase",
            "mentions critical or urgent",
            "mentions runway < 2 months",
            "recommends immediate review",
            "mentions pattern of anomalies",
        ],
        expected_action="ALERT",
    ),
    # Scenario 8: Recurring vendor spike
    AnomalyEvalScenario(
        id="anomaly_008",
        event_type="payment.success",
        vendor="datadog",
        amount=4000.0,
        avg_90d=2000.0,
        anomaly_score=0.6,
        runway_months=7.0,
        past_context="Spike every quarter due to log retention",
        gold_criteria=[
            "mentions 2x or double",
            "mentions quarterly pattern",
            "mentions log retention if in context",
            "suggests planning for next quarter",
        ],
        expected_action="ALERT",
    ),
    # Scenario 9: Revenue drop on time tick
    AnomalyEvalScenario(
        id="anomaly_009",
        event_type="TIME_TICK_WEEKLY",
        vendor="",
        amount=0.0,
        avg_90d=0.0,
        anomaly_score=0.4,
        runway_months=5.0,
        past_context="Revenue 40% below average this week",
        gold_criteria=[
            "mentions revenue drop",
            "mentions percentage or comparison",
            "suggests investigating collections",
        ],
        expected_action="DIGEST",
    ),
    # Scenario 10: Unknown vendor large payment
    AnomalyEvalScenario(
        id="anomaly_010",
        event_type="payment.success",
        vendor="unknown-vendor-xyz",
        amount=25000.0,
        avg_90d=0.0,
        anomaly_score=0.95,
        runway_months=6.0,
        past_context="No history, vendor not recognized",
        gold_criteria=[
            "mentions first time or new vendor",
            "mentions large amount $25,000",
            "mentions not recognized or unknown",
            "recommends immediate verification",
            "suggests checking with finance team",
        ],
        expected_action="ALERT",
    ),
    # Scenario 11: Moderate spike healthy runway
    AnomalyEvalScenario(
        id="anomaly_011",
        event_type="payment.success",
        vendor="snowflake",
        amount=9000.0,
        avg_90d=6000.0,
        anomaly_score=0.4,
        runway_months=18.0,
        past_context="Gradual increase over 3 months",
        gold_criteria=[
            "mentions 1.5x or 50% increase",
            "mentions gradual trend",
            "mentions healthy runway",
            "suggests monitoring not alarm",
        ],
        expected_action="SKIP",
    ),
    # Scenario 12: Subscription renewal spike
    AnomalyEvalScenario(
        id="anomaly_012",
        event_type="payment.success",
        vendor="salesforce",
        amount=12000.0,
        avg_90d=4000.0,
        anomaly_score=0.75,
        runway_months=10.0,
        past_context="Annual renewal, 3x normal monthly",
        gold_criteria=[
            "mentions 3x or triple",
            "mentions annual renewal",
            "mentions expected or planned",
            "no urgent action needed",
        ],
        expected_action="ALERT",
    ),
    # Scenario 13: Multiple small anomalies pattern
    AnomalyEvalScenario(
        id="anomaly_013",
        event_type="payment.success",
        vendor="various",
        amount=3000.0,
        avg_90d=2000.0,
        anomaly_score=0.5,
        runway_months=4.0,
        past_context="5 small anomalies in past 14 days",
        gold_criteria=[
            "mentions pattern or trend",
            "mentions multiple events",
            "mentions 1.5x or 50% increase",
            "suggests reviewing spending controls",
        ],
        expected_action="ALERT",
    ),
    # Scenario 14: Infrastructure scaling event
    AnomalyEvalScenario(
        id="anomaly_014",
        event_type="payment.success",
        vendor="aws",
        amount=18000.0,
        avg_90d=6000.0,
        anomaly_score=0.8,
        runway_months=8.0,
        past_context="Product launch week, expected 3x traffic",
        gold_criteria=[
            "mentions 3x or triple",
            "mentions product launch or traffic",
            "mentions expected or planned",
            "suggests monitoring for normalization",
        ],
        expected_action="ALERT",
    ),
    # Scenario 15: Currency fluctuation impact
    AnomalyEvalScenario(
        id="anomaly_015",
        event_type="payment.success",
        vendor="atlassian",
        amount=4500.0,
        avg_90d=3500.0,
        anomaly_score=0.3,
        runway_months=11.0,
        past_context="USD invoice, currency conversion variance",
        gold_criteria=[
            "mentions currency or FX",
            "mentions within normal variance",
            "no alarm language",
        ],
        expected_action="SKIP",
    ),
    # Scenario 16: Error duplicate charge
    AnomalyEvalScenario(
        id="anomaly_016",
        event_type="payment.success",
        vendor="stripe",
        amount=5000.0,
        avg_90d=5000.0,
        anomaly_score=0.6,
        runway_months=9.0,
        past_context="Identical charge 2 days ago, possible duplicate",
        gold_criteria=[
            "mentions duplicate or double charge",
            "mentions identical amount",
            "mentions same vendor",
            "recommends contacting vendor",
        ],
        expected_action="ALERT",
    ),
    # Scenario 17: Seasonal business pattern
    AnomalyEvalScenario(
        id="anomaly_017",
        event_type="payment.success",
        vendor="facebook-ads",
        amount=20000.0,
        avg_90d=8000.0,
        anomaly_score=0.7,
        runway_months=7.0,
        past_context="Q4 holiday season, 2.5x ad spend typical",
        gold_criteria=[
            "mentions 2.5x or 150% increase",
            "mentions seasonal or holiday",
            "mentions expected pattern",
            "suggests comparing to last year",
        ],
        expected_action="ALERT",
    ),
    # Scenario 18: Trial period ending
    AnomalyEvalScenario(
        id="anomaly_018",
        event_type="payment.success",
        vendor="notion",
        amount=1200.0,
        avg_90d=0.0,
        anomaly_score=0.5,
        runway_months=15.0,
        past_context="Trial ended, annual plan charged",
        gold_criteria=[
            "mentions first payment or trial ended",
            "mentions annual plan",
            "mentions expected",
        ],
        expected_action="DIGEST",
    ),
    # Scenario 19: Price increase notification
    AnomalyEvalScenario(
        id="anomaly_019",
        event_type="payment.success",
        vendor="github",
        amount=2500.0,
        avg_90d=2000.0,
        anomaly_score=0.3,
        runway_months=12.0,
        past_context="Vendor announced 25% price increase",
        gold_criteria=[
            "mentions price increase",
            "mentions expected or notified",
            "mentions percentage if available",
        ],
        expected_action="SKIP",
    ),
    # Scenario 20: Fraudulent charge suspected
    AnomalyEvalScenario(
        id="anomaly_020",
        event_type="payment.success",
        vendor="unknown-charge",
        amount=8000.0,
        avg_90d=0.0,
        anomaly_score=0.95,
        runway_months=5.0,
        past_context="Vendor not recognized, no approval record",
        gold_criteria=[
            "mentions not recognized or unknown",
            "mentions no approval or unauthorized",
            "mentions potential fraud or dispute",
            "recommends immediate action",
            "suggests contacting bank",
        ],
        expected_action="ALERT",
    ),
]


def get_anomaly_eval_scenarios() -> List[AnomalyEvalScenario]:
    """Return all anomaly evaluation scenarios."""
    return ANOMALY_EVAL_SCENARIOS


def get_scenario_by_id(scenario_id: str) -> AnomalyEvalScenario | None:
    """Get a specific scenario by ID."""
    for scenario in ANOMALY_EVAL_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    return None
