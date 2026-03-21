"""
BI Agent Activity for Temporal.

Wraps the BI LangGraph agent as a Temporal activity.
LangGraph invoke is sync — wrapped with asyncio.get_event_loop().run_in_executor().
"""
import asyncio
from typing import Any

from temporalio import activity

from src.agents.bi.graph import bi_graph
from src.agents.bi.state import BIState


@activity.defn(name="run_bi_agent")
async def run_bi_agent(tenant_id: str, query: str) -> dict[str, Any]:
    """
    Execute the BI Agent LangGraph for natural language to SQL queries.

    This activity:
    1. Initializes BIState with tenant_id and query
    2. Invokes the bi_graph LangGraph
    3. Returns the output with narrative, chart info, and SQL result

    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        query: Natural language question (e.g., "Total expenses by vendor last 30 days?")

    Returns:
        dict with keys:
            - tenant_id: str
            - query: str (original query)
            - generated_sql: str (SQL query generated)
            - sql_result: dict with rows, columns, count
            - narrative: str (plain English explanation)
            - chart_type: str (line | bar | pie | none)
            - chart_path: str (PNG path or "")
            - output_message: str (formatted Telegram message)
            - langfuse_trace_id: str

    Raises:
        ValueError: If tenant_id or query is missing/empty
        Exception: Propagates any LangGraph execution errors
    """
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required and cannot be empty")
    if not query or not query.strip():
        raise ValueError("query is required and cannot be empty")

    # Initialize state
    initial_state: BIState = {
        "tenant_id": tenant_id,
        "query": query,
        "query_type": "ADHOC",
        "query_category": "",
        "data_sources": [],
        "generated_sql": "",
        "sql_result": {"rows": [], "columns": [], "count": 0},
        "chart_type": "none",
        "chart_path": "",
        "chart_x_col": "",
        "chart_y_col": "",
        "past_queries": [],
        "narrative": "",
        "output_message": "",
        "error": "",
        "retry_count": 0,
        "langfuse_trace_id": "",
    }

    # LangGraph invoke is sync — run in executor to avoid blocking event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: bi_graph.invoke(initial_state),
    )

    # Return only the required output fields
    return {
        "tenant_id": result.get("tenant_id", tenant_id),
        "query": result.get("query", query),
        "generated_sql": result.get("generated_sql", ""),
        "sql_result": result.get("sql_result", {"rows": [], "columns": [], "count": 0}),
        "narrative": result.get("narrative", ""),
        "chart_type": result.get("chart_type", "none"),
        "chart_path": result.get("chart_path", ""),
        "output_message": result.get("output_message", ""),
        "langfuse_trace_id": result.get("langfuse_trace_id", ""),
    }
