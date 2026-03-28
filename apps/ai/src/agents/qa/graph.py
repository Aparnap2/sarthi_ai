"""
LangGraph compilation for QAAgent.

Graph topology (sequential):
  match_question → fetch_data → retrieve_memory →
  generate_answer → send_slack → END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agents.qa.state import QAState
from src.agents.qa.nodes import (
    match_question,
    fetch_data,
    retrieve_memory,
    generate_answer,
    send_slack,
)


def build_qa_graph() -> StateGraph:
    graph = StateGraph(QAState)

    # Add nodes
    graph.add_node("match_question",    match_question)
    graph.add_node("fetch_data",        fetch_data)
    graph.add_node("retrieve_memory",   retrieve_memory)
    graph.add_node("generate_answer",   generate_answer)
    graph.add_node("send_slack",        send_slack)

    # Sequential edges
    graph.set_entry_point("match_question")
    graph.add_edge("match_question",    "fetch_data")
    graph.add_edge("fetch_data",        "retrieve_memory")
    graph.add_edge("retrieve_memory",   "generate_answer")
    graph.add_edge("generate_answer",   "send_slack")
    graph.add_edge("send_slack",        END)

    return graph.compile()


# Module-level compiled graph
qa_graph = build_qa_graph()
