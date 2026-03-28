"""
LangGraph compilation for PulseAgent.

Graph topology (sequential):
  fetch_data → retrieve_memory → compute_metrics →
  generate_narrative → build_slack_message → send_slack →
  persist_snapshot → END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agents.pulse.state import PulseState
from src.agents.pulse.nodes import (
    fetch_data,
    retrieve_memory,
    compute_metrics,
    generate_narrative,
    build_slack_message,
    send_slack,
    persist_snapshot,
)


def build_pulse_graph() -> StateGraph:
    """
    Build and compile the PulseAgent LangGraph.

    Returns:
        Compiled StateGraph ready for invocation
    """
    graph = StateGraph(PulseState)

    # Add nodes
    graph.add_node("fetch_data",          fetch_data)
    graph.add_node("retrieve_memory",     retrieve_memory)
    graph.add_node("compute_metrics",     compute_metrics)
    graph.add_node("generate_narrative",  generate_narrative)
    graph.add_node("build_slack_message", build_slack_message)
    graph.add_node("send_slack",          send_slack)
    graph.add_node("persist_snapshot",    persist_snapshot)

    # Sequential edges
    graph.set_entry_point("fetch_data")
    graph.add_edge("fetch_data",          "retrieve_memory")
    graph.add_edge("retrieve_memory",     "compute_metrics")
    graph.add_edge("compute_metrics",     "generate_narrative")
    graph.add_edge("generate_narrative",  "build_slack_message")
    graph.add_edge("build_slack_message", "send_slack")
    graph.add_edge("send_slack",          "persist_snapshot")
    graph.add_edge("persist_snapshot",    END)

    return graph.compile()


# Module-level compiled graph (importable by Temporal activities)
pulse_graph = build_pulse_graph()
