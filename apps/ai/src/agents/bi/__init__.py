"""
BI Agent for Sarthi v1.0.

Business Intelligence agent that converts natural language questions
to SQL queries, executes them, generates charts, and writes narratives.

Usage:
    from src.agents.bi import bi_graph, BIState

    state: BIState = {
        "tenant_id": "uuid-here",
        "query": "What was our revenue last month?",
        "query_type": "",
        "query_category": "",
        "data_sources": [],
        "generated_sql": "",
        "sql_result": {},
        "chart_type": "",
        "chart_path": "",
        "past_queries": [],
        "narrative": "",
        "output_message": "",
        "error": "",
        "retry_count": 0,
        "langfuse_trace_id": "",
    }

    result = bi_graph.invoke(state)
    print(result["output_message"])
"""
from .state import BIState
from .graph import bi_graph
from .nodes import (
    node_understand_query,
    node_generate_sql,
    node_execute_sql,
    node_decide_visualization,
    node_generate_chart,
    node_generate_narrative,
    node_write_bi_memory,
    node_emit_bi_output,
    sanitize_sql,
    _run_chart_code,
    _ensure_chart_container,
)

__all__ = [
    "BIState",
    "bi_graph",
    "node_understand_query",
    "node_generate_sql",
    "node_execute_sql",
    "node_decide_visualization",
    "node_generate_chart",
    "node_generate_narrative",
    "node_write_bi_memory",
    "node_emit_bi_output",
    "sanitize_sql",
    "_run_chart_code",
    "_ensure_chart_container",
]
