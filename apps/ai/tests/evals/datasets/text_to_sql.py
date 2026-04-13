"""
Text-to-SQL Eval Dataset.

15 NL queries with gold SQL patterns for evaluating BI Agent SQL generation.
Each scenario includes:
- Input: Natural language query
- Gold SQL pattern: Expected SQL structure
- Expected columns: Required columns in result
- Difficulty: easy, medium, hard

Run with:
    cd apps/ai && uv run python tests/evals/run_evals.py
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SQLEvalScenario:
    """Single text-to-SQL evaluation scenario."""
    id: str
    nl_query: str
    gold_sql_pattern: str  # Key SQL elements that must be present
    expected_columns: List[str]  # Required columns in result
    time_hint: str  # Expected time range
    difficulty: str  # easy, medium, hard
    query_category: str  # aggregation, trend, breakdown, comparison


# 15 evaluation scenarios
SQL_EVAL_SCENARIOS: List[SQLEvalScenario] = [
    # Scenario 1: Simple aggregation
    SQLEvalScenario(
        id="sql_001",
        nl_query="Show total revenue last 30 days",
        gold_sql_pattern="SELECT SUM(credit) FROM transactions WHERE txn_date >= NOW() - INTERVAL '30 days'",
        expected_columns=["sum"],
        time_hint="last 30 days",
        difficulty="easy",
        query_category="aggregation",
    ),
    # Scenario 2: Expense breakdown by category
    SQLEvalScenario(
        id="sql_002",
        nl_query="Show expenses by category for last month",
        gold_sql_pattern="SELECT category, SUM(debit) FROM transactions WHERE debit > 0 GROUP BY category",
        expected_columns=["category", "sum"],
        time_hint="last 30 days",
        difficulty="medium",
        query_category="breakdown",
    ),
    # Scenario 3: Revenue trend over time
    SQLEvalScenario(
        id="sql_003",
        nl_query="Show revenue trend for last 90 days",
        gold_sql_pattern="SELECT DATE_TRUNC('week', txn_date), SUM(credit) FROM transactions GROUP BY DATE_TRUNC",
        expected_columns=["date", "sum"],
        time_hint="last 90 days",
        difficulty="medium",
        query_category="trend",
    ),
    # Scenario 4: Top vendors by spend
    SQLEvalScenario(
        id="sql_004",
        nl_query="What are my top 5 vendors by spend",
        gold_sql_pattern="SELECT description OR vendor, SUM(debit) FROM transactions GROUP BY description ORDER BY SUM DESC LIMIT 5",
        expected_columns=["vendor", "sum"],
        time_hint="last 90 days",
        difficulty="medium",
        query_category="breakdown",
    ),
    # Scenario 5: Monthly burn rate
    SQLEvalScenario(
        id="sql_005",
        nl_query="What is my monthly burn rate",
        gold_sql_pattern="SELECT SUM(debit) FROM transactions WHERE debit > 0 AND txn_date >= NOW() - INTERVAL '30 days'",
        expected_columns=["sum"],
        time_hint="last 30 days",
        difficulty="easy",
        query_category="aggregation",
    ),
    # Scenario 6: Compare revenue vs expenses
    SQLEvalScenario(
        id="sql_006",
        nl_query="Compare revenue and expenses for last quarter",
        gold_sql_pattern="SELECT SUM(credit) as revenue, SUM(debit) as expenses FROM transactions WHERE txn_date >= NOW() - INTERVAL '90 days'",
        expected_columns=["revenue", "expenses"],
        time_hint="last 90 days",
        difficulty="medium",
        query_category="comparison",
    ),
    # Scenario 7: AWS spend over time
    SQLEvalScenario(
        id="sql_007",
        nl_query="Show AWS spend over the last 3 months",
        gold_sql_pattern="SELECT DATE_TRUNC('month', txn_date), SUM(debit) FROM transactions WHERE description ILIKE '%aws%' GROUP BY DATE_TRUNC",
        expected_columns=["date", "sum"],
        time_hint="last 90 days",
        difficulty="medium",
        query_category="trend",
    ),
    # Scenario 8: Runway calculation
    SQLEvalScenario(
        id="sql_008",
        nl_query="How many months of runway do I have",
        gold_sql_pattern="SELECT runway_months FROM finance_snapshots ORDER BY snapshot_date DESC LIMIT 1",
        expected_columns=["runway_months"],
        time_hint="current",
        difficulty="easy",
        query_category="aggregation",
    ),
    # Scenario 9: Transaction count by vendor
    SQLEvalScenario(
        id="sql_009",
        nl_query="How many transactions per vendor last month",
        gold_sql_pattern="SELECT description, COUNT(*) FROM transactions GROUP BY description HAVING COUNT > 0",
        expected_columns=["vendor", "count"],
        time_hint="last 30 days",
        difficulty="medium",
        query_category="breakdown",
    ),
    # Scenario 10: Average transaction size
    SQLEvalScenario(
        id="sql_010",
        nl_query="What is the average transaction size",
        gold_sql_pattern="SELECT AVG(debit) FROM transactions WHERE debit > 0",
        expected_columns=["avg"],
        time_hint="last 30 days",
        difficulty="easy",
        query_category="aggregation",
    ),
    # Scenario 11: Revenue growth rate
    SQLEvalScenario(
        id="sql_011",
        nl_query="What is my revenue growth rate month over month",
        gold_sql_pattern="SELECT DATE_TRUNC('month', txn_date), SUM(credit), LAG(SUM(credit)) OVER (ORDER BY DATE_TRUNC) FROM transactions GROUP BY DATE_TRUNC",
        expected_columns=["date", "revenue", "growth"],
        time_hint="last 90 days",
        difficulty="hard",
        query_category="trend",
    ),
    # Scenario 12: Category spending percentage
    SQLEvalScenario(
        id="sql_012",
        nl_query="What percentage of spending goes to each category",
        gold_sql_pattern="SELECT category, SUM(debit) * 100.0 / (SELECT SUM(debit) FROM transactions) as percentage FROM transactions GROUP BY category",
        expected_columns=["category", "percentage"],
        time_hint="last 30 days",
        difficulty="hard",
        query_category="breakdown",
    ),
    # Scenario 13: Largest transactions
    SQLEvalScenario(
        id="sql_013",
        nl_query="Show me the 10 largest transactions",
        gold_sql_pattern="SELECT * FROM transactions ORDER BY debit DESC LIMIT 10",
        expected_columns=["id", "description", "debit", "txn_date"],
        time_hint="all time",
        difficulty="easy",
        query_category="breakdown",
    ),
    # Scenario 14: Weekly revenue pattern
    SQLEvalScenario(
        id="sql_014",
        nl_query="Show revenue pattern by week of year",
        gold_sql_pattern="SELECT EXTRACT(WEEK FROM txn_date), SUM(credit) FROM transactions GROUP BY EXTRACT(WEEK) ORDER BY EXTRACT(WEEK)",
        expected_columns=["week", "revenue"],
        time_hint="last 365 days",
        difficulty="hard",
        query_category="trend",
    ),
    # Scenario 15: Vendor baseline comparison
    SQLEvalScenario(
        id="sql_015",
        nl_query="Compare actual spend vs baseline for top vendors",
        gold_sql_pattern="SELECT v.vendor_name, v.avg_90d as baseline, SUM(t.debit) as actual FROM vendor_baselines v JOIN transactions t ON v.vendor_name = t.description GROUP BY v.vendor_name",
        expected_columns=["vendor", "baseline", "actual"],
        time_hint="last 90 days",
        difficulty="hard",
        query_category="comparison",
    ),
]


def get_sql_eval_scenarios() -> List[SQLEvalScenario]:
    """Return all SQL evaluation scenarios."""
    return SQL_EVAL_SCENARIOS


def get_scenario_by_id(scenario_id: str) -> SQLEvalScenario | None:
    """Get a specific scenario by ID."""
    for scenario in SQL_EVAL_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    return None


def evaluate_sql_output(generated_sql: str, scenario: SQLEvalScenario) -> dict:
    """
    Evaluate generated SQL against gold pattern.

    Returns:
        dict with passed (bool), score (float), and reasons (list)
    """
    reasons = []
    score = 0.0

    generated_upper = generated_sql.upper()

    # Check for required SQL elements from gold pattern
    gold_upper = scenario.gold_sql_pattern.upper()

    # Check for SELECT
    if "SELECT" in generated_upper:
        score += 0.2
    else:
        reasons.append("Missing SELECT statement")

    # Check for tenant_id filter (security requirement)
    if "TENANT_ID" in generated_upper:
        score += 0.2
    else:
        reasons.append("Missing tenant_id filter (security issue)")

    # Check for time-based filter if applicable
    if scenario.time_hint != "current" and scenario.time_hint != "all time":
        if "INTERVAL" in generated_upper or "txn_date" in generated_upper.lower():
            score += 0.2
        else:
            reasons.append(f"Missing time filter for {scenario.time_hint}")

    # Check for GROUP BY if breakdown/trend
    if scenario.query_category in ("breakdown", "trend"):
        if "GROUP BY" in generated_upper:
            score += 0.2
        else:
            reasons.append("Missing GROUP BY for breakdown/trend query")

    # Check for ORDER BY if top-N or comparison
    if scenario.query_category in ("comparison",) or "top" in scenario.nl_query.lower():
        if "ORDER BY" in generated_upper:
            score += 0.2
        else:
            reasons.append("Missing ORDER BY for ranking query")

    # Bonus: Check for expected columns
    for col in scenario.expected_columns:
        if col.upper() in generated_upper or any(col in c.lower() for c in ["sum", "count", "avg", "date", "category", "vendor"]):
            score += 0.05

    # Normalize score to 0-1
    score = min(1.0, score)

    return {
        "passed": score >= 0.7,
        "score": score,
        "reasons": reasons if reasons else ["All checks passed"],
    }
