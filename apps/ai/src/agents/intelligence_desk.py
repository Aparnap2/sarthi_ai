"""
Intelligence Desk Agent — Sarthi v4.2 Phase 3.

Unified Intelligence Desk with 2 virtual employees:
- BI Analyst: Unit economics, churn signals, operational anomalies
- Policy Watcher: Internal policy changes, regulatory updates, market shifts

All capabilities return structured IntelligenceFinding with:
- Plain language (no analyst jargon)
- Exactly ONE action
- Clear evidence backing
- HITL risk assessment

Usage:
    from src.agents.intelligence_desk import IntelligenceDeskAgent
    
    agent = IntelligenceDeskAgent()
    graph = agent.create_graph()
    result = graph.invoke({
        "founder_id": "founder-uuid",
        "business_data": {...},
        "task_type": "bi_analyst",  # or "policy_watcher"
    })
"""
from typing import TypedDict, Optional, List, Any
from langgraph.graph import StateGraph, END
import json

from src.schemas.desk_results import IntelligenceFinding, HitlRisk
from src.config.llm import get_llm_client, get_chat_model


class IntelligenceDeskState(TypedDict):
    """
    State for Intelligence Desk workflow.
    
    Attributes:
        founder_id: Founder UUID for personalization
        business_data: Business metrics and data
        policy_data: Policy and regulatory data
        task_type: Type of Intelligence task to perform
        result: Final IntelligenceFinding (set by workflow)
    """
    founder_id: str
    business_data: dict
    policy_data: dict
    task_type: str
    result: Optional[IntelligenceFinding]


class IntelligenceDeskAgent:
    """
    Unified Intelligence Desk agent with 2 virtual employees.
    
    Capabilities:
        - analyze_bi: Unit economics, churn signals, operational anomalies
        - analyze_policy: Policy changes, regulatory updates
    
    Each capability uses LLM to analyze data and produce structured output
    with plain language, single action, and clear evidence.
    """

    def __init__(self):
        """Initialize IntelligenceDeskAgent with LLM client."""
        self.client = get_llm_client()
        self.model = get_chat_model()

    def analyze_bi(self, state: IntelligenceDeskState) -> IntelligenceDeskState:
        """
        BI Analyst capability: Business intelligence and anomaly detection.
        
        Analyzes unit economics, identifies churn signals, detects anomalies.
        
        Args:
            state: IntelligenceDeskState with business data
            
        Returns:
            Updated state with BI analysis result
        """
        business_data = state["business_data"]
        
        context = self._build_bi_context(business_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the BI Analyst virtual employee for Sarthi.
Analyze business data and return a JSON object with:
{
    "insight_type": "unit_economics" | "churn_signal" | "ops_anomaly" | "policy_change",
    "headline": str,  # Max 10 words
    "evidence": str,  # Data backing the insight
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO jargon: EBITDA, CAC, LTV, ARR, MRR, burn rate, runway
- headline: max 10 words, plain language
- evidence: include specific numbers and trends
- do_this: exactly ONE action (e.g., "Review pricing for top 5 customers")
- hitl_risk: high for churn signals, medium for anomalies"""
                },
                {
                    "role": "user",
                    "content": f"Business data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = IntelligenceFinding(
            insight_type=result_data["insight_type"],
            headline=result_data["headline"],
            evidence=result_data["evidence"],
            do_this=result_data["do_this"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def analyze_policy(self, state: IntelligenceDeskState) -> IntelligenceDeskState:
        """
        Policy Watcher capability: Policy and regulatory monitoring.
        
        Tracks internal policy changes, regulatory updates, market shifts.
        
        Args:
            state: IntelligenceDeskState with policy data
            
        Returns:
            Updated state with Policy analysis result
        """
        policy_data = state["policy_data"]
        
        context = self._build_policy_context(policy_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the Policy Watcher virtual employee for Sarthi.
Analyze policy changes and return a JSON object with:
{
    "insight_type": "policy_change",
    "headline": str,  # Max 10 words
    "evidence": str,  # What changed and why it matters
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO jargon: compliance, regulatory (use plain terms)
- headline: max 10 words
- evidence: specific policy change details
- do_this: exactly ONE action (e.g., "Update employee handbook section 3.2")
- hitl_risk: high for regulatory changes, medium for policy updates"""
                },
                {
                    "role": "user",
                    "content": f"Policy data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = IntelligenceFinding(
            insight_type=result_data["insight_type"],
            headline=result_data["headline"],
            evidence=result_data["evidence"],
            do_this=result_data["do_this"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def _build_bi_context(self, business_data: dict) -> str:
        """Build context string for BI analysis."""
        lines = []
        
        # Revenue metrics
        revenue = business_data.get("revenue", {})
        lines.append("Revenue Metrics:")
        lines.append(f"  Current Month: ₹{revenue.get('current_month', 0):,}")
        lines.append(f"  Previous Month: ₹{revenue.get('previous_month', 0):,}")
        growth = revenue.get('growth_rate', 0) * 100
        lines.append(f"  Growth Rate: {growth:.1f}%")
        
        # Customer metrics
        customers = business_data.get("customers", {})
        lines.append("\nCustomer Metrics:")
        lines.append(f"  Active Customers: {customers.get('active', 0)}")
        lines.append(f"  New This Month: {customers.get('new', 0)}")
        lines.append(f"  Churned This Month: {customers.get('churned', 0)}")
        churn_rate = customers.get('churn_rate', 0) * 100
        lines.append(f"  Churn Rate: {churn_rate:.1f}%")
        
        # Operational metrics
        ops = business_data.get("operations", {})
        lines.append("\nOperational Metrics:")
        lines.append(f"  Support Tickets: {ops.get('support_tickets', 0)}")
        lines.append(f"  Avg Response Time: {ops.get('avg_response_hours', 0)} hours")
        lines.append(f"  System Downtime: {ops.get('downtime_minutes', 0)} minutes")
        
        # Anomalies
        anomalies = business_data.get("anomalies", [])
        if anomalies:
            lines.append("\nDetected Anomalies:")
            for anomaly in anomalies[:5]:
                lines.append(f"  - {anomaly.get('description', 'Unknown')}")
        
        return "\n".join(lines)

    def _build_policy_context(self, policy_data: dict) -> str:
        """Build context string for Policy analysis."""
        lines = []
        
        # Recent changes
        changes = policy_data.get("recent_changes", [])
        lines.append(f"Recent Policy Changes: {len(changes)}")
        
        for change in changes[:5]:
            lines.append(f"\n  Policy: {change.get('name', 'Unknown')}")
            lines.append(f"  Type: {change.get('type', 'Internal')}")
            lines.append(f"  Effective Date: {change.get('effective_date', 'TBD')}")
            lines.append(f"  Summary: {change.get('summary', 'No summary')}")
            lines.append(f"  Impact: {change.get('impact', 'Unknown')}")
        
        # Regulatory updates
        regulatory = policy_data.get("regulatory_updates", [])
        if regulatory:
            lines.append(f"\nRegulatory Updates: {len(regulatory)}")
            for update in regulatory[:3]:
                lines.append(f"  - {update.get('title', 'Unknown')}: {update.get('deadline', 'No deadline')}")
        
        return "\n".join(lines)

    def create_graph(self) -> StateGraph:
        """
        Create LangGraph workflow for Intelligence Desk.
        
        Routes to appropriate capability based on task_type:
        - "bi_analyst" → analyze_bi
        - "policy_watcher" → analyze_policy
        
        Returns:
            Compiled LangGraph StateGraph
        """
        graph = StateGraph(IntelligenceDeskState)
        
        # Add nodes for each capability
        graph.add_node("bi_analyst", self.analyze_bi)
        graph.add_node("policy_watcher", self.analyze_policy)
        
        # Add routing logic
        def route_by_task_type(state: IntelligenceDeskState) -> str:
            """Route to appropriate capability based on task_type."""
            task_type = state.get("task_type", "bi_analyst")
            
            routing_map = {
                "bi_analyst": "bi_analyst",
                "unit_economics": "bi_analyst",
                "churn_signal": "bi_analyst",
                "ops_anomaly": "bi_analyst",
                "revenue_anomaly": "bi_analyst",
                "policy_watcher": "policy_watcher",
                "policy_change": "policy_watcher",
                "regulatory_update": "policy_watcher",
            }
            
            return routing_map.get(task_type, "bi_analyst")
        
        # Add conditional entry point
        graph.set_conditional_entry_point(route_by_task_type)
        
        # All capabilities lead to END
        graph.add_edge("bi_analyst", END)
        graph.add_edge("policy_watcher", END)
        
        return graph.compile()


# Global instance for reuse
_intelligence_desk_agent: Optional[IntelligenceDeskAgent] = None


def get_intelligence_desk_agent() -> IntelligenceDeskAgent:
    """
    Get or create the global IntelligenceDeskAgent instance.
    
    Returns:
        IntelligenceDeskAgent: Singleton instance
    """
    global _intelligence_desk_agent
    if _intelligence_desk_agent is None:
        _intelligence_desk_agent = IntelligenceDeskAgent()
    return _intelligence_desk_agent
