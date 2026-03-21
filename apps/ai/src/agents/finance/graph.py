"""
Finance Agent LangGraph for Sarthi v1.0.

Compiles 9 nodes into a state machine graph:
  ingest → update_snapshot → load_baseline → detect_anomaly →
  query_memory → reason_explain → decide_action → write_memory → emit_output → END

The graph is a linear pipeline — anomaly detection is score-based
inside node_detect_anomaly, branching is in node_decide_action.
"""
from langgraph.graph import StateGraph, END

from .state import FinanceState
from .nodes import (
    node_ingest_event,
    node_update_snapshot,
    node_load_vendor_baseline,
    node_detect_anomaly,
    node_query_memory,
    node_reason_and_explain,
    node_decide_action,
    node_write_memory,
    node_emit_output,
)


def build_finance_graph() -> StateGraph:
    """
    Build and compile the Finance Agent LangGraph.
    
    Returns:
        Compiled StateGraph ready for invocation
    """
    g = StateGraph(FinanceState)

    # Register all 9 nodes
    g.add_node("ingest", node_ingest_event)
    g.add_node("update_snapshot", node_update_snapshot)
    g.add_node("load_baseline", node_load_vendor_baseline)
    g.add_node("detect_anomaly", node_detect_anomaly)
    g.add_node("query_memory", node_query_memory)
    g.add_node("reason_explain", node_reason_and_explain)
    g.add_node("decide_action", node_decide_action)
    g.add_node("write_memory", node_write_memory)
    g.add_node("emit_output", node_emit_output)

    # Linear pipeline — no conditional edges needed
    # Anomaly detection is score-based; branching is in node_decide_action
    g.set_entry_point("ingest")
    g.add_edge("ingest", "update_snapshot")
    g.add_edge("update_snapshot", "load_baseline")
    g.add_edge("load_baseline", "detect_anomaly")
    g.add_edge("detect_anomaly", "query_memory")
    g.add_edge("query_memory", "reason_explain")
    g.add_edge("reason_explain", "decide_action")
    g.add_edge("decide_action", "write_memory")
    g.add_edge("write_memory", "emit_output")
    g.add_edge("emit_output", END)

    return g.compile()


# Module-level singleton — imported by Temporal worker
finance_graph = build_finance_graph()
