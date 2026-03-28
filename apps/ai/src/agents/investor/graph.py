"""
LangGraph compilation for InvestorAgent.

Graph topology (sequential):
  fetch_metrics → retrieve_memory → generate_draft →
  build_slack_message → send_slack → END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agents.investor.state import InvestorState
from src.agents.investor.nodes import (
    fetch_metrics,
    retrieve_memory,
    generate_draft,
    build_slack_message,
    send_slack,
)


def build_investor_graph() -> StateGraph:
    """
    Build and compile the InvestorAgent LangGraph.

    Returns:
        Compiled StateGraph ready for invocation
    """
    graph = StateGraph(InvestorState)

    # Add nodes
    graph.add_node("fetch_metrics",       fetch_metrics)
    graph.add_node("retrieve_memory",     retrieve_memory)
    graph.add_node("generate_draft",      generate_draft)
    graph.add_node("build_slack_message", build_slack_message)
    graph.add_node("send_slack",          send_slack)

    # Sequential edges
    graph.set_entry_point("fetch_metrics")
    graph.add_edge("fetch_metrics",       "retrieve_memory")
    graph.add_edge("retrieve_memory",     "generate_draft")
    graph.add_edge("generate_draft",      "build_slack_message")
    graph.add_edge("build_slack_message", "send_slack")
    graph.add_edge("send_slack",          END)

    return graph.compile()


# Module-level compiled graph (importable by Temporal activities)
investor_graph = build_investor_graph()
