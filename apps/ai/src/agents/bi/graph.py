"""
BI Agent LangGraph for Sarthi v1.0.

Compiles 8 nodes into a state machine graph with SQL retry logic:
  understand_query → generate_sql → execute_sql → decide_viz →
  generate_chart → generate_narrative → write_memory → emit_output → END

SQL Retry Edge:
  - If execute_sql returns error AND retry_count < 2 → retry generate_sql
  - Otherwise → continue to decide_viz
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import BIState
from .nodes import (
    node_understand_query,
    node_generate_sql,
    node_execute_sql,
    node_decide_visualization,
    node_generate_chart,
    node_generate_narrative,
    node_write_bi_memory,
    node_emit_bi_output,
)


def _should_retry_sql(state: BIState) -> str:
    """
    Conditional edge: Check if SQL execution should be retried.

    Retry conditions:
    - retryable flag is True (set by node_execute_sql for transient errors)
    - retry_count < 2 (max 2 retries)

    Args:
        state: Current BIState

    Returns:
        "retry" to go back to generate_sql, "continue" to proceed
    """
    retryable = state.get("retryable", False)
    retry_count = state.get("retry_count", 0)
    max_retries = 2

    if retryable and retry_count < max_retries:
        return "retry"
    return "continue"


def build_bi_graph() -> StateGraph:
    """
    Build and compile the BI Agent LangGraph with MemorySaver checkpointer.

    Graph structure:
      understand_query → generate_sql → execute_sql ↔ (retry loop)
                                              ↓
                                        decide_viz → generate_chart
                                              ↓
                                        generate_narrative → write_memory → emit_output → END

    Returns:
        Compiled StateGraph ready for invocation (with HITL support)
    """
    g = StateGraph(BIState)

    # Register all 8 nodes
    g.add_node("understand_query", node_understand_query)
    g.add_node("generate_sql", node_generate_sql)
    g.add_node("execute_sql", node_execute_sql)
    g.add_node("decide_visualization", node_decide_visualization)
    g.add_node("generate_chart", node_generate_chart)
    g.add_node("generate_narrative", node_generate_narrative)
    g.add_node("write_memory", node_write_bi_memory)
    g.add_node("emit_output", node_emit_bi_output)

    # Set entry point
    g.set_entry_point("understand_query")

    # Linear flow with retry loop on execute_sql
    g.add_edge("understand_query", "generate_sql")
    g.add_edge("generate_sql", "execute_sql")

    # Conditional edge for SQL retry
    g.add_conditional_edges(
        "execute_sql",
        _should_retry_sql,
        {
            "retry": "generate_sql",      # Go back to regenerate SQL
            "continue": "decide_visualization",  # Proceed to visualization
        },
    )

    # Continue linear flow after retry decision
    g.add_edge("decide_visualization", "generate_chart")
    g.add_edge("generate_chart", "generate_narrative")
    g.add_edge("generate_narrative", "write_memory")
    g.add_edge("write_memory", "emit_output")
    g.add_edge("emit_output", END)

    # MemorySaver checkpointer for HITL signals (Phase 4+)
    checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


# Module-level singleton — imported by Temporal worker
bi_graph = build_bi_graph()
