"""
BI Narrative Eval Dataset.

10 SQL result scenarios with gold narrative criteria for evaluating
BI Agent narrative generation.
Each scenario includes:
- Input: SQL result data
- Gold criteria: Required elements in narrative
- Expected tone: informative, urgent, neutral

Run with:
    cd apps/ai && uv run python tests/evals/run_evals.py
"""
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class NarrativeEvalScenario:
    """Single narrative evaluation scenario."""
    id: str
    sql_result: Dict[str, Any]  # Mock SQL result
    query_context: str  # Original query that produced result
    gold_criteria: List[str]  # Required elements in narrative
    expected_tone: str  # informative, urgent, neutral
    min_sentences: int
    max_sentences: int


# 10 evaluation scenarios
NARRATIVE_EVAL_SCENARIOS: List[NarrativeEvalScenario] = [
    # Scenario 1: Revenue summary
    NarrativeEvalScenario(
        id="narrative_001",
        sql_result={
            "rows": [{"sum": 150000.00}],
            "columns": ["sum"],
            "count": 1,
        },
        query_context="Show total revenue last 30 days",
        gold_criteria=[
            "mentions specific amount ₹150,000 or $150,000",
            "mentions time period (30 days or month)",
            "mentions revenue",
            "no unnecessary alarm or urgency",
        ],
        expected_tone="informative",
        min_sentences=1,
        max_sentences=3,
    ),
    # Scenario 2: Expense breakdown
    NarrativeEvalScenario(
        id="narrative_002",
        sql_result={
            "rows": [
                {"category": "infrastructure", "sum": 25000.00},
                {"category": "salaries", "sum": 80000.00},
                {"category": "marketing", "sum": 15000.00},
            ],
            "columns": ["category", "sum"],
            "count": 3,
        },
        query_context="Show expenses by category for last month",
        gold_criteria=[
            "mentions total expenses (₹120,000 or $120,000)",
            "mentions largest category (salaries)",
            "mentions at least 2 categories",
            "provides percentage or proportion insight",
        ],
        expected_tone="informative",
        min_sentences=2,
        max_sentences=4,
    ),
    # Scenario 3: Revenue decline (urgent)
    NarrativeEvalScenario(
        id="narrative_003",
        sql_result={
            "rows": [
                {"month": "2026-01", "revenue": 100000.00},
                {"month": "2026-02", "revenue": 70000.00},
                {"month": "2026-03", "revenue": 45000.00},
            ],
            "columns": ["month", "revenue"],
            "count": 3,
        },
        query_context="Show revenue trend for last 90 days",
        gold_criteria=[
            "mentions declining trend",
            "mentions specific decline (55% or from 100k to 45k)",
            "mentions urgency or concern",
            "suggests investigation or action",
        ],
        expected_tone="urgent",
        min_sentences=2,
        max_sentences=4,
    ),
    # Scenario 4: Top vendors
    NarrativeEvalScenario(
        id="narrative_004",
        sql_result={
            "rows": [
                {"vendor": "AWS", "sum": 15000.00},
                {"vendor": "Stripe", "sum": 8000.00},
                {"vendor": "Google Cloud", "sum": 6000.00},
            ],
            "columns": ["vendor", "sum"],
            "count": 3,
        },
        query_context="What are my top 5 vendors by spend",
        gold_criteria=[
            "mentions top vendor (AWS)",
            "mentions total spend for top vendors",
            "mentions at least 2 vendor names",
            "provides insight on concentration",
        ],
        expected_tone="informative",
        min_sentences=2,
        max_sentences=4,
    ),
    # Scenario 5: Healthy runway
    NarrativeEvalScenario(
        id="narrative_005",
        sql_result={
            "rows": [{"runway_months": 14.5}],
            "columns": ["runway_months"],
            "count": 1,
        },
        query_context="How many months of runway do I have",
        gold_criteria=[
            "mentions specific runway (14.5 months)",
            "mentions healthy or good position",
            "no unnecessary alarm",
            "may mention industry benchmark",
        ],
        expected_tone="neutral",
        min_sentences=1,
        max_sentences=3,
    ),
    # Scenario 6: Critical runway (urgent)
    NarrativeEvalScenario(
        id="narrative_006",
        sql_result={
            "rows": [{"runway_months": 2.3}],
            "columns": ["runway_months"],
            "count": 1,
        },
        query_context="How many months of runway do I have",
        gold_criteria=[
            "mentions specific runway (2.3 months)",
            "mentions critical or urgent",
            "mentions below 3-6 month threshold",
            "recommends immediate action",
        ],
        expected_tone="urgent",
        min_sentences=2,
        max_sentences=4,
    ),
    # Scenario 7: Revenue vs expenses comparison
    NarrativeEvalScenario(
        id="narrative_007",
        sql_result={
            "rows": [{"revenue": 200000.00, "expenses": 180000.00}],
            "columns": ["revenue", "expenses"],
            "count": 1,
        },
        query_context="Compare revenue and expenses for last quarter",
        gold_criteria=[
            "mentions profit or surplus (₹20,000)",
            "mentions margin percentage (10%)",
            "mentions positive or healthy",
            "may suggest maintaining or improving",
        ],
        expected_tone="informative",
        min_sentences=2,
        max_sentences=4,
    ),
    # Scenario 8: Operating loss (urgent)
    NarrativeEvalScenario(
        id="narrative_008",
        sql_result={
            "rows": [{"revenue": 100000.00, "expenses": 150000.00}],
            "columns": ["revenue", "expenses"],
            "count": 1,
        },
        query_context="Compare revenue and expenses for last quarter",
        gold_criteria=[
            "mentions loss or deficit (₹50,000)",
            "mentions expenses exceed revenue",
            "mentions percentage over (50%)",
            "recommends cost reduction or revenue increase",
        ],
        expected_tone="urgent",
        min_sentences=2,
        max_sentences=4,
    ),
    # Scenario 9: No data found
    NarrativeEvalScenario(
        id="narrative_009",
        sql_result={
            "rows": [],
            "columns": [],
            "count": 0,
        },
        query_context="Show revenue for next month",
        gold_criteria=[
            "mentions no data found",
            "explains why (future date or no transactions)",
            "suggests alternative query or time range",
            "no error language",
        ],
        expected_tone="neutral",
        min_sentences=1,
        max_sentences=3,
    ),
    # Scenario 10: Growth rate positive
    NarrativeEvalScenario(
        id="narrative_010",
        sql_result={
            "rows": [
                {"month": "2026-01", "revenue": 100000.00, "growth": None},
                {"month": "2026-02", "revenue": 120000.00, "growth": 20.0},
                {"month": "2026-03", "revenue": 150000.00, "growth": 25.0},
            ],
            "columns": ["month", "revenue", "growth"],
            "count": 3,
        },
        query_context="What is my revenue growth rate month over month",
        gold_criteria=[
            "mentions positive growth trend",
            "mentions specific growth rates (20%, 25%)",
            "mentions accelerating or improving",
            "provides encouraging insight",
        ],
        expected_tone="informative",
        min_sentences=2,
        max_sentences=4,
    ),
]


def get_narrative_eval_scenarios() -> List[NarrativeEvalScenario]:
    """Return all narrative evaluation scenarios."""
    return NARRATIVE_EVAL_SCENARIOS


def get_scenario_by_id(scenario_id: str) -> NarrativeEvalScenario | None:
    """Get a specific scenario by ID."""
    for scenario in NARRATIVE_EVAL_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    return None


def evaluate_narrative_output(narrative: str, scenario: NarrativeEvalScenario) -> dict:
    """
    Evaluate generated narrative against gold criteria.

    Returns:
        dict with passed (bool), score (float), and reasons (list)
    """
    reasons = []
    score = 0.0
    narrative_lower = narrative.lower()

    # Check sentence count
    sentences = [s.strip() for s in narrative.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    sentence_count = len(sentences)

    if scenario.min_sentences <= sentence_count <= scenario.max_sentences:
        score += 0.2
    else:
        reasons.append(f"Sentence count {sentence_count} outside range [{scenario.min_sentences}-{scenario.max_sentences}]")

    # Check tone appropriateness
    if scenario.expected_tone == "urgent":
        urgent_words = ["urgent", "critical", "immediate", "concern", "decline", "loss", "alert"]
        if any(word in narrative_lower for word in urgent_words):
            score += 0.15
        else:
            reasons.append("Missing urgent tone for critical data")
    elif scenario.expected_tone == "informative":
        # Should not have alarm words unless data is critical
        alarm_words = ["critical", "urgent", "alert", "danger"]
        if not any(word in narrative_lower for word in alarm_words):
            score += 0.15
        else:
            reasons.append("Unnecessary alarm in informative narrative")

    # Check gold criteria
    criteria_matched = 0
    for criterion in scenario.gold_criteria:
        # Simple keyword matching for evaluation
        criterion_keywords = criterion.lower().replace("mentions ", "").replace("suggests ", "").split()
        if any(kw in narrative_lower for kw in criterion_keywords if len(kw) > 3):
            criteria_matched += 1

    criteria_score = (criteria_matched / len(scenario.gold_criteria)) * 0.65
    score += criteria_score

    if criteria_matched < len(scenario.gold_criteria) * 0.7:
        reasons.append(f"Only {criteria_matched}/{len(scenario.gold_criteria)} gold criteria met")

    # Normalize score
    score = min(1.0, score)

    return {
        "passed": score >= 0.7,
        "score": round(score, 2),
        "reasons": reasons if reasons else ["All checks passed"],
        "sentence_count": sentence_count,
    }
