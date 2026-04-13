"""
LangGraph compilation for QAAgent.

Two agent patterns are exported:

1. qa_graph (backward-compatible):
   Sequential graph: match_question → fetch_data → retrieve_memory →
                     generate_answer → send_slack → END

2. qa_agent (ReAct pattern via create_react_agent):
   LLM + tools (search_pulse_memory, query_stripe_metrics, query_product_db)
   with autonomous tool selection and reasoning.
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
    QA_TOOLS,
)
from src.agents.qa.prompts import REACT_SYSTEM_PROMPT


# =============================================================================
# Backward-compatible sequential graph
# =============================================================================

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


# Module-level compiled graph (backward-compatible)
qa_graph = build_qa_graph()


# =============================================================================
# ReAct agent via create_react_agent
# =============================================================================

def build_qa_react_agent():
    """Build a ReAct agent with tools for autonomous Q&A.

    Uses ChatOllama with qwen3:0.6b and three tools:
      - search_pulse_memory
      - query_stripe_metrics
      - query_product_db
    """
    try:
        # langchain >= 1.2: new API with system_prompt
        from langchain.agents import create_agent
        _use_new_api = True
    except ImportError:
        # langgraph.prebuilt fallback with prompt kwarg
        from langgraph.prebuilt import create_react_agent as create_agent
        _use_new_api = False
    from langchain_ollama import ChatOllama

    llm = ChatOllama(
        model="qwen3:0.6b",
        base_url="http://localhost:11434",
        temperature=0.2,
    )

    if _use_new_api:
        agent = create_agent(
            model=llm,
            tools=QA_TOOLS,
            system_prompt=REACT_SYSTEM_PROMPT,
        )
    else:
        agent = create_agent(
            model=llm,
            tools=QA_TOOLS,
            prompt=REACT_SYSTEM_PROMPT,
        )

    return agent


# Module-level ReAct agent
qa_agent = build_qa_react_agent()
