"""LangGraph Agent for feedback triage (classification + severity)."""

from typing import Any, TypedDict

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.config import get_config


# ========================
# State Definition
# ========================


class TriageState(TypedDict):
    """State for the Triage Agent workflow."""

    feedback_id: str
    content: str
    source: str

    # Output
    classification: str  # bug, feature, or question
    severity: str  # low, medium, high, critical
    reasoning: str
    confidence: float


# ========================
# Pydantic Models
# ========================


class TriageResult(BaseModel):
    """Structured output from the Triage Agent."""

    classification: str = Field(
        description="Classification: 'bug', 'feature', or 'question'",
        pattern="^(bug|feature|question)$",
    )
    severity: str = Field(
        description="Severity level: 'low', 'medium', 'high', or 'critical'",
        pattern="^(low|medium|high|critical)$",
    )
    reasoning: str = Field(
        description="Brief explanation of the classification decision",
        min_length=10,
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0",
        ge=0.0,
        le=1.0,
    )
    # Urgency detection (Week 3 upgrade)
    urgency: str = Field(
        default="normal",
        description="Urgency level: 'backlog', 'normal', 'soon', or 'immediate'",
        pattern="^(backlog|normal|soon|immediate)$",
    )
    # SRE metrics
    affected_users: int = Field(
        default=0,
        description="Number of affected users from SRE data",
        ge=0,
    )
    error_rate: float = Field(
        default=0.0,
        description="Error rate from SRE data",
        ge=0.0,
        le=1.0,
    )


# ========================
# LLM Client
# ========================


def get_llm_client() -> AsyncOpenAI:
    """Get configured OpenAI-compatible LLM client (Ollama)."""
    config = get_config().ollama
    return AsyncOpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
    )


# ========================
# Prompt Templates
# ========================


TRIAGE_SYSTEM_PROMPT = """You are a Triage Agent for a software project.

Your job is to analyze incoming user feedback and classify it accurately.

Classification Rules:
- **bug**: The feedback reports something broken, not working, or producing errors.
- **feature**: The feedback requests new functionality or improvements.
- **question**: The feedback asks for help without indicating a problem.

Severity Guidelines:
- **critical**: Data loss, security vulnerability, or complete system failure
- **high**: Major feature broken, affects many users, no workaround
- **medium**: Feature partially broken, affects some users, workaround exists
- **low**: Minor issue, cosmetic, or easy to work around

Output your classification with clear reasoning."""


TRIAGE_HUMAN_PROMPT = """Analyze the following feedback:

---
Feedback ID: {feedback_id}
Source: {source}
Content: {content}
---

{format_instructions}"""


# ========================
# Agent Node
# ========================


async def triage_node(state: TriageState) -> dict[str, Any]:
    """Process feedback and classify it."""
    # Initialize LLM client
    llm = get_llm_client()

    # Create prompt
    parser = PydanticOutputParser(pydantic_object=TriageResult)

    prompt = ChatPromptTemplate.from_messages([
        ("system", TRIAGE_SYSTEM_PROMPT),
        ("human", TRIAGE_HUMAN_PROMPT),
    ])

    # Format the prompt
    formatted_prompt = prompt.format_messages(
        feedback_id=state["feedback_id"],
        source=state["source"],
        content=state["content"],
        format_instructions=parser.get_format_instructions(),
    )

    # Call LLM with structured output
    response = await llm.chat.completions.create(
        messages=[
            {"role": "system", "content": formatted_prompt[0].content},
            {"role": "user", "content": formatted_prompt[1].content},
        ],
        model=get_config().ollama.model,
        temperature=0.1,
    )

    if not response.choices or not response.choices[0].message.content:
        raise ValueError("LLM returned empty response")

    # Parse structured output
    result = parser.parse(response.choices[0].message.content)

    return {
        "classification": result.classification,
        "severity": result.severity,
        "reasoning": result.reasoning,
        "confidence": result.confidence,
    }


# ========================
# Graph Compilation
# ========================


def create_triage_graph() -> StateGraph:
    """Create and compile the Triage Agent workflow graph."""
    workflow = StateGraph(TriageState)
    workflow.add_node("triage", triage_node)
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", END)
    return workflow.compile()


# Create the compiled graph
triage_graph = create_triage_graph()


# ========================
# Convenience Function
# ========================


async def classify_feedback(
    feedback_id: str,
    content: str,
    source: str = "unknown",
) -> TriageResult:
    """Convenience function to classify a single feedback item."""
    initial_state: TriageState = {
        "feedback_id": feedback_id,
        "content": content,
        "source": source,
        "classification": "question",
        "severity": "low",
        "reasoning": "",
        "confidence": 0.0,
    }

    result = await triage_graph.ainvoke(initial_state)

    return TriageResult(
        classification=result["classification"],
        severity=result["severity"],
        reasoning=result["reasoning"],
        confidence=result["confidence"],
    )


# ========================
# Week 3 Upgrade: Urgency Detection
# ========================


def detect_urgency_from_feedback(feedback_text: str) -> str:
    """Detect urgency level from feedback text keywords.

    Args:
        feedback_text: The feedback text to analyze

    Returns:
        Urgency level: 'immediate', 'soon', 'normal', or 'backlog'
    """
    text_lower = feedback_text.lower()

    # Immediate: outage, down, critical, emergency
    if any(kw in text_lower for kw in ["outage", "down", "critical", "emergency", "production is down"]):
        return "immediate"

    # Soon: slow, degraded, performance, affecting users
    if any(kw in text_lower for kw in ["slow", "degraded", "performance", "affecting users", "latency"]):
        return "soon"

    # Backlog: nice to have, enhancement, when possible
    if any(kw in text_lower for kw in ["nice to have", "enhancement", "when possible", "someday"]):
        return "backlog"

    # Default to normal
    return "normal"


def incorporate_sre_data(result: TriageResult, sre_interrupt: dict[str, Any]) -> TriageResult:
    """Incorporate SRE interrupt data into triage result.

    Args:
        result: Original TriageResult
        sre_interrupt: SRE interrupt data with priority, affected_users, error_rate

    Returns:
        Updated TriageResult with urgency and metrics
    """
    priority = sre_interrupt.get("priority", "").upper()
    affected_users = sre_interrupt.get("affected_users", 0)
    error_rate = sre_interrupt.get("error_rate", 0.0)

    # Determine urgency based on SRE priority
    urgency = result.urgency
    severity = result.severity

    if priority == "CRITICAL":
        urgency = "immediate"
        severity = "critical"
    elif priority == "HIGH":
        urgency = "soon"  # SRE HIGH takes precedence
        if severity not in ["critical"]:
            severity = "high"
    elif priority == "MEDIUM":
        if urgency == "backlog":
            urgency = "normal"
    # LOW priority doesn't change urgency

    return TriageResult(
        classification=result.classification,
        severity=severity,
        reasoning=result.reasoning,
        confidence=result.confidence,
        urgency=urgency,
        affected_users=affected_users,
        error_rate=error_rate,
    )
