"""
LangGraph compilation for AnomalyAgent.

Graph topology (sequential):
  retrieve_anomaly_memory → generate_explanation →
  generate_action → build_slack_message → send_slack → END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agents.anomaly.state import AnomalyState
from src.agents.anomaly.nodes import (
    retrieve_anomaly_memory,
    generate_explanation,
    generate_action,
    build_slack_message,
    send_slack,
)


def build_anomaly_graph() -> StateGraph:
    graph = StateGraph(AnomalyState)

    # Add nodes
    graph.add_node("retrieve_anomaly_memory", retrieve_anomaly_memory)
    graph.add_node("generate_explanation",    generate_explanation)
    graph.add_node("generate_action",         generate_action)
    graph.add_node("build_slack_message",     build_slack_message)
    graph.add_node("send_slack",              send_slack)

    # Sequential edges
    graph.set_entry_point("retrieve_anomaly_memory")
    graph.add_edge("retrieve_anomaly_memory", "generate_explanation")
    graph.add_edge("generate_explanation",    "generate_action")
    graph.add_edge("generate_action",         "build_slack_message")
    graph.add_edge("build_slack_message",     "send_slack")
    graph.add_edge("send_slack",              END)

    return graph.compile()


# Module-level compiled graph
anomaly_graph = build_anomaly_graph()
