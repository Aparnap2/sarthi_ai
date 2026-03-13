"""
IT & Tools Desk Agent — Sarthi v4.2 Phase 3.

Unified IT Desk with 1 virtual employee:
- IT Admin: SaaS tool management, cost optimization, access control, security

All capabilities return structured ITRiskAlert with:
- Plain language (no IT jargon)
- Exactly ONE action
- Clear cost and usage data
- HITL risk assessment

Usage:
    from src.agents.it_desk import ITDeskAgent
    
    agent = ITDeskAgent()
    graph = agent.create_graph()
    result = graph.invoke({
        "founder_id": "founder-uuid",
        "tools_data": {...},
        "task_type": "saas_management",
    })
"""
from typing import TypedDict, Optional, List, Any
from langgraph.graph import StateGraph, END
import json

from src.schemas.desk_results import ITRiskAlert, HitlRisk
from src.config.llm import get_llm_client, get_chat_model


class ITDeskState(TypedDict):
    """
    State for IT Desk workflow.
    
    Attributes:
        founder_id: Founder UUID for personalization
        tools_data: SaaS tools and usage data
        task_type: Type of IT task to perform
        result: Final ITRiskAlert (set by workflow)
    """
    founder_id: str
    tools_data: dict
    task_type: str
    result: Optional[ITRiskAlert]


class ITDeskAgent:
    """
    Unified IT Desk agent with IT Admin virtual employee.
    
    Capabilities:
        - analyze_saas: SaaS tool management, cost optimization
        - analyze_access: Access control, security review
        - analyze_security: Security posture, vulnerability assessment
    
    Each capability uses LLM to analyze IT data and produce structured output
    with plain language, single action, and clear cost/usage data.
    """

    def __init__(self):
        """Initialize ITDeskAgent with LLM client."""
        self.client = get_llm_client()
        self.model = get_chat_model()

    def analyze_saas(self, state: ITDeskState) -> ITDeskState:
        """
        IT Admin capability: SaaS tool management and cost optimization.
        
        Identifies unused tools, optimizes costs, manages renewals.
        
        Args:
            state: ITDeskState with tools data
            
        Returns:
            Updated state with SaaS analysis result
        """
        tools_data = state["tools_data"]
        
        context = self._build_saas_context(tools_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the IT Admin virtual employee for Sarthi.
Analyze SaaS tools and return a JSON object with:
{
    "tool_name": str,  # Name of the tool
    "monthly_cost": int,  # Cost in INR
    "days_unused": int,  # Days since last active use
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO jargon: provision, deprovision, SaaS, license, SSO, MFA
- do_this: plain language (e.g., "Cancel unused subscription")
- hitl_risk: high for security issues, medium for cost waste, low for routine
- Focus on cost optimization and unused tools"""
                },
                {
                    "role": "user",
                    "content": f"SaaS tools data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = ITRiskAlert(
            tool_name=result_data["tool_name"],
            monthly_cost=result_data["monthly_cost"],
            days_unused=result_data["days_unused"],
            do_this=result_data["do_this"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def analyze_access(self, state: ITDeskState) -> ITDeskState:
        """
        IT Admin capability: Access control review.
        
        Reviews user access, identifies orphaned accounts, manages permissions.
        
        Args:
            state: ITDeskState with tools data
            
        Returns:
            Updated state with access analysis result
        """
        tools_data = state["tools_data"]
        
        context = self._build_access_context(tools_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the IT Admin virtual employee for Sarthi.
Analyze access patterns and return a JSON object with:
{
    "tool_name": str,  # Tool with access issue
    "monthly_cost": int,  # Associated cost
    "days_unused": int,  # Days since last access
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO jargon: provision, SSO, MFA, IAM
- do_this: plain language (e.g., "Remove access for departed employee")
- hitl_risk: high for security risks, medium for access review"""
                },
                {
                    "role": "user",
                    "content": f"Access data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = ITRiskAlert(
            tool_name=result_data["tool_name"],
            monthly_cost=result_data["monthly_cost"],
            days_unused=result_data["days_unused"],
            do_this=result_data["do_this"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def analyze_security(self, state: ITDeskState) -> ITDeskState:
        """
        IT Admin capability: Security posture assessment.
        
        Reviews security settings, identifies vulnerabilities, recommends fixes.
        
        Args:
            state: ITDeskState with tools data
            
        Returns:
            Updated state with security analysis result
        """
        tools_data = state["tools_data"]
        
        context = self._build_security_context(tools_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the IT Admin virtual employee for Sarthi.
Analyze security posture and return a JSON object with:
{
    "tool_name": str,  # Tool with security concern
    "monthly_cost": int,  # Associated cost
    "days_unused": int,  # Days since security review
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO jargon: vulnerability, penetration, exploit
- do_this: plain language (e.g., "Enable two-factor authentication")
- hitl_risk: high for critical security issues"""
                },
                {
                    "role": "user",
                    "content": f"Security data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = ITRiskAlert(
            tool_name=result_data["tool_name"],
            monthly_cost=result_data["monthly_cost"],
            days_unused=result_data["days_unused"],
            do_this=result_data["do_this"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def _build_saas_context(self, tools_data: dict) -> str:
        """Build context string for SaaS analysis."""
        lines = []
        
        tools = tools_data.get("tools", [])
        unused = [t for t in tools if t.get("days_since_last_use", 0) > 30]
        expensive = [t for t in tools if t.get("monthly_cost", 0) > 5000]
        
        lines.append(f"Total Tools: {len(tools)}")
        lines.append(f"Unused (>30 days): {len(unused)}")
        lines.append(f"High Cost (>₹5000/month): {len(expensive)}")
        
        total_monthly = sum(t.get("monthly_cost", 0) for t in tools)
        lines.append(f"Total Monthly Cost: ₹{total_monthly:,}")
        
        if unused:
            lines.append("\nUnused Tools:")
            for tool in unused[:5]:
                lines.append(f"  - {tool.get('name', 'Unknown')}: {tool.get('days_since_last_use', 0)} days unused")
                lines.append(f"    Monthly Cost: ₹{tool.get('monthly_cost', 0):,}")
                lines.append(f"    Assigned Users: {tool.get('assigned_users', 0)}")
        
        return "\n".join(lines)

    def _build_access_context(self, tools_data: dict) -> str:
        """Build context string for access analysis."""
        lines = []
        
        access_issues = tools_data.get("access_issues", [])
        orphaned = [a for a in access_issues if a.get("type") == "orphaned"]
        excessive = [a for a in access_issues if a.get("type") == "excessive_permissions"]
        
        lines.append(f"Total Access Issues: {len(access_issues)}")
        lines.append(f"Orphaned Accounts: {len(orphaned)}")
        lines.append(f"Excessive Permissions: {len(excessive)}")
        
        if orphaned:
            lines.append("\nOrphaned Accounts:")
            for account in orphaned[:5]:
                lines.append(f"  - {account.get('user_email', 'Unknown')}: {account.get('tool', 'Unknown')}")
                lines.append(f"    Last Access: {account.get('last_access', 'Unknown')}")
        
        return "\n".join(lines)

    def _build_security_context(self, tools_data: dict) -> str:
        """Build context string for security analysis."""
        lines = []
        
        security_issues = tools_data.get("security_issues", [])
        
        lines.append(f"Total Security Issues: {len(security_issues)}")
        
        if security_issues:
            lines.append("\nSecurity Issues:")
            for issue in security_issues[:5]:
                lines.append(f"  - {issue.get('tool', 'Unknown')}: {issue.get('severity', 'Unknown')} severity")
                lines.append(f"    Issue: {issue.get('description', 'Unknown')}")
                lines.append(f"    Affected Users: {issue.get('affected_users', 0)}")
        
        # Tools without 2FA
        no_2fa = tools_data.get("tools_without_2fa", [])
        if no_2fa:
            lines.append(f"\nTools Without 2FA: {len(no_2fa)}")
            for tool in no_2fa[:3]:
                lines.append(f"  - {tool.get('name', 'Unknown')}")
        
        return "\n".join(lines)

    def create_graph(self) -> StateGraph:
        """
        Create LangGraph workflow for IT Desk.
        
        Routes to appropriate capability based on task_type:
        - "saas_management" → analyze_saas
        - "access_review" → analyze_access
        - "security_review" → analyze_security
        
        Returns:
            Compiled LangGraph StateGraph
        """
        graph = StateGraph(ITDeskState)
        
        # Add nodes for each capability
        graph.add_node("saas_management", self.analyze_saas)
        graph.add_node("access_review", self.analyze_access)
        graph.add_node("security_review", self.analyze_security)
        
        # Add routing logic
        def route_by_task_type(state: ITDeskState) -> str:
            """Route to appropriate capability based on task_type."""
            task_type = state.get("task_type", "saas_management")
            
            routing_map = {
                "saas_management": "saas_management",
                "saas_subscription": "saas_management",
                "cost_optimization": "saas_management",
                "access_review": "access_review",
                "access_control": "access_review",
                "security_review": "security_review",
                "security_audit": "security_review",
            }
            
            return routing_map.get(task_type, "saas_management")
        
        # Add conditional entry point
        graph.set_conditional_entry_point(route_by_task_type)
        
        # All capabilities lead to END
        graph.add_edge("saas_management", END)
        graph.add_edge("access_review", END)
        graph.add_edge("security_review", END)
        
        return graph.compile()


# Global instance for reuse
_it_desk_agent: Optional[ITDeskAgent] = None


def get_it_desk_agent() -> ITDeskAgent:
    """
    Get or create the global ITDeskAgent instance.
    
    Returns:
        ITDeskAgent: Singleton instance
    """
    global _it_desk_agent
    if _it_desk_agent is None:
        _it_desk_agent = ITDeskAgent()
    return _it_desk_agent
