"""
Chief of Staff Agent — Sarthi v4.2 Phase 3.

Central routing agent that orchestrates all 6 desks (13 virtual employees):
- Finance Desk: CFO, Bookkeeper, AR/AP Clerk, Payroll Clerk
- People Desk: HR Coordinator, Internal Recruiter
- Legal Desk: Contracts Coordinator, Compliance Tracker
- Intelligence Desk: BI Analyst, Policy Watcher
- IT & Tools Desk: IT Admin
- Admin Desk: EA, Knowledge Manager

CRITICAL: Routes to INTERNAL-OPS desks ONLY.
No external-facing agents (no RevOps, GTM, Market Intel).

Usage:
    from src.agents.chief_of_staff_agent import ChiefOfStaffAgent
    
    agent = ChiefOfStaffAgent()
    graph = agent.create_graph()
    result = graph.invoke({
        "founder_id": "founder-uuid",
        "event_type": "bank_statement",
        "event_payload": {...},
    })
"""
from typing import TypedDict, Optional, Any, Union
from langgraph.graph import StateGraph, END
import json

from src.schemas.desk_results import (
    FinanceTaskResult,
    PeopleOpsFinding,
    LegalOpsResult,
    IntelligenceFinding,
    ITRiskAlert,
    KnowledgeManagerResult,
    DeskResult,
)
from src.agents.finance_desk import FinanceDeskAgent, get_finance_desk_agent
from src.agents.people_desk import PeopleDeskAgent, get_people_desk_agent
from src.agents.legal_desk import LegalDeskAgent, get_legal_desk_agent
from src.agents.intelligence_desk import IntelligenceDeskAgent, get_intelligence_desk_agent
from src.agents.it_desk import ITDeskAgent, get_it_desk_agent
from src.agents.admin_desk import AdminDeskAgent, get_admin_desk_agent
from src.config.llm import get_llm_client, get_chat_model


class ChiefOfStaffState(TypedDict):
    """
    State for Chief of Staff workflow.
    
    Attributes:
        founder_id: Founder UUID for personalization
        event_type: Type of event triggering the workflow
        event_payload: Event data payload
        routed_to: Which desk was selected (set by routing)
        result: Final desk result (set by desk agent)
    """
    founder_id: str
    event_type: str
    event_payload: dict
    routed_to: Optional[str]
    result: Optional[dict]


# Event type to desk routing map
# INTERNAL-OPS ONLY - No external-facing agents
DESK_ROUTING_MAP = {
    # Finance Desk events
    "bank_statement": "finance",
    "transaction_categorized": "finance",
    "invoice_overdue": "finance",
    "payment_received": "finance",
    "payroll_due": "finance",
    "reconciliation_needed": "finance",
    "ar_reminder": "finance",
    "ap_due": "finance",
    "payroll_prep": "finance",
    
    # People Desk events
    "new_hire": "people",
    "employee_onboarding": "people",
    "leave_request": "people",
    "appraisal_due": "people",
    "offboarding": "people",
    "hiring_request": "people",
    "interview_scheduled": "people",
    
    # Legal Desk events
    "contract_uploaded": "legal",
    "contract_expiry": "legal",
    "compliance_due": "legal",
    "regulatory_filing": "legal",
    "policy_update": "legal",
    
    # Intelligence Desk events
    "revenue_anomaly": "intelligence",
    "churn_detected": "intelligence",
    "unit_economics_review": "intelligence",
    "ops_anomaly": "intelligence",
    "policy_change_detected": "intelligence",
    
    # IT & Tools Desk events
    "saas_subscription": "it",
    "tool_unused": "it",
    "access_review_due": "it",
    "security_audit": "it",
    "cost_optimization": "it",
    
    # Admin Desk events
    "meeting_transcript": "admin",
    "calendar_management": "admin",
    "sop_extraction": "admin",
    "documentation_update": "admin",
    "knowledge_capture": "admin",
}

# Desk to task type mapping for sub-agent routing
DESK_TASK_TYPES = {
    "finance": {
        "bank_statement": "cfo",
        "transaction_categorized": "bookkeeper",
        "invoice_overdue": "ar_ap",
        "payment_received": "ar_ap",
        "payroll_due": "payroll",
        "reconciliation_needed": "bookkeeper",
        "ar_reminder": "ar_ap",
        "ap_due": "ar_ap",
        "payroll_prep": "payroll",
    },
    "people": {
        "new_hire": "hr_coordinator",
        "employee_onboarding": "hr_coordinator",
        "leave_request": "hr_coordinator",
        "appraisal_due": "hr_coordinator",
        "offboarding": "hr_coordinator",
        "hiring_request": "internal_recruiter",
        "interview_scheduled": "internal_recruiter",
    },
    "legal": {
        "contract_uploaded": "contracts",
        "contract_expiry": "contracts",
        "compliance_due": "compliance",
        "regulatory_filing": "compliance",
        "policy_update": "compliance",
    },
    "intelligence": {
        "revenue_anomaly": "bi_analyst",
        "churn_detected": "bi_analyst",
        "unit_economics_review": "bi_analyst",
        "ops_anomaly": "bi_analyst",
        "policy_change_detected": "policy_watcher",
    },
    "it": {
        "saas_subscription": "saas_management",
        "tool_unused": "saas_management",
        "access_review_due": "access_review",
        "security_audit": "security_review",
        "cost_optimization": "saas_management",
    },
    "admin": {
        "meeting_transcript": "ea",
        "calendar_management": "ea",
        "sop_extraction": "knowledge_manager",
        "documentation_update": "knowledge_manager",
        "knowledge_capture": "knowledge_manager",
    },
}


class ChiefOfStaffAgent:
    """
    Chief of Staff agent: Routes events to appropriate desk.
    
    INTERNAL-OPS ONLY: Routes exclusively to internal operations desks.
    No external-facing agents (RevOps, GTM, Market Intel) are included.
    
    Desks managed:
        - Finance Desk (4 virtual employees)
        - People Desk (2 virtual employees)
        - Legal Desk (2 virtual employees)
        - Intelligence Desk (2 virtual employees)
        - IT & Tools Desk (1 virtual employee)
        - Admin Desk (2 virtual employees)
    
    Total: 6 desks, 13 virtual employees
    """

    def __init__(self):
        """Initialize ChiefOfStaffAgent with all desk agents."""
        self.client = get_llm_client()
        self.model = get_chat_model()
        
        # Initialize desk agents
        self.finance = get_finance_desk_agent()
        self.people = get_people_desk_agent()
        self.legal = get_legal_desk_agent()
        self.intelligence = get_intelligence_desk_agent()
        self.it = get_it_desk_agent()
        self.admin = get_admin_desk_agent()

    def route_event(self, state: ChiefOfStaffState) -> ChiefOfStaffState:
        """
        Route event to appropriate desk based on event_type.
        
        Uses deterministic routing map for internal-ops events.
        Falls back to LLM-based routing for unknown event types.
        
        Args:
            state: ChiefOfStaffState with event data
            
        Returns:
            Updated state with routed_to desk name
        """
        event_type = state["event_type"]
        
        # Try deterministic routing first
        desk = DESK_ROUTING_MAP.get(event_type)
        
        if desk is None:
            # Fall back to LLM-based routing for unknown events
            desk = self._llm_route_event(event_type, state["event_payload"])
        
        state["routed_to"] = desk
        return state

    def _llm_route_event(self, event_type: str, event_payload: dict) -> str:
        """
        Use LLM to route unknown event types.
        
        Args:
            event_type: Unknown event type string
            event_payload: Event data payload
            
        Returns:
            Desk name (finance, people, legal, intelligence, it, admin)
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the Chief of Staff routing assistant.
Route events to the appropriate internal operations desk.

Available desks:
- finance: Bank statements, invoices, payments, payroll, reconciliation
- people: Hiring, onboarding, leave, appraisals, offboarding
- legal: Contracts, compliance, regulatory filings, policies
- intelligence: Revenue anomalies, churn, operational anomalies
- it: SaaS tools, access control, security, cost optimization
- admin: Meetings, calendars, SOPs, documentation, knowledge

Return ONLY the desk name (lowercase): finance, people, legal, intelligence, it, or admin."""
                },
                {
                    "role": "user",
                    "content": f"Event type: {event_type}\nEvent payload: {json.dumps(event_payload, default=str)[:500]}"
                }
            ],
            temperature=0.0,
        )
        
        desk = response.choices[0].message.content.strip().lower()
        
        # Validate desk name
        valid_desks = {"finance", "people", "legal", "intelligence", "it", "admin"}
        if desk not in valid_desks:
            desk = "admin"  # Default fallback
        
        return desk

    def process_finance(self, state: ChiefOfStaffState) -> ChiefOfStaffState:
        """Route to Finance Desk and process."""
        event_type = state["event_type"]
        task_type = DESK_TASK_TYPES["finance"].get(event_type, "cfo")
        
        finance_graph = self.finance.create_graph()
        result = finance_graph.invoke({
            "founder_id": state["founder_id"],
            "bank_data": state["event_payload"].get("bank_data", {}),
            "accounting_data": state["event_payload"].get("accounting_data", {}),
            "task_type": task_type,
        })
        
        state["result"] = result.get("result", {})
        return state

    def process_people(self, state: ChiefOfStaffState) -> ChiefOfStaffState:
        """Route to People Desk and process."""
        event_type = state["event_type"]
        task_type = DESK_TASK_TYPES["people"].get(event_type, "hr_coordinator")
        
        people_graph = self.people.create_graph()
        result = people_graph.invoke({
            "founder_id": state["founder_id"],
            "hr_events": state["event_payload"].get("hr_events", []),
            "task_type": task_type,
            "employee_name": state["event_payload"].get("employee_name"),
        })
        
        state["result"] = result.get("result", {})
        return state

    def process_legal(self, state: ChiefOfStaffState) -> ChiefOfStaffState:
        """Route to Legal Desk and process."""
        event_type = state["event_type"]
        task_type = DESK_TASK_TYPES["legal"].get(event_type, "contracts")
        
        legal_graph = self.legal.create_graph()
        result = legal_graph.invoke({
            "founder_id": state["founder_id"],
            "legal_documents": state["event_payload"].get("legal_documents", []),
            "task_type": task_type,
        })
        
        state["result"] = result.get("result", {})
        return state

    def process_intelligence(self, state: ChiefOfStaffState) -> ChiefOfStaffState:
        """Route to Intelligence Desk and process."""
        event_type = state["event_type"]
        task_type = DESK_TASK_TYPES["intelligence"].get(event_type, "bi_analyst")
        
        intelligence_graph = self.intelligence.create_graph()
        result = intelligence_graph.invoke({
            "founder_id": state["founder_id"],
            "business_data": state["event_payload"].get("business_data", {}),
            "policy_data": state["event_payload"].get("policy_data", {}),
            "task_type": task_type,
        })
        
        state["result"] = result.get("result", {})
        return state

    def process_it(self, state: ChiefOfStaffState) -> ChiefOfStaffState:
        """Route to IT Desk and process."""
        event_type = state["event_type"]
        task_type = DESK_TASK_TYPES["it"].get(event_type, "saas_management")
        
        it_graph = self.it.create_graph()
        result = it_graph.invoke({
            "founder_id": state["founder_id"],
            "tools_data": state["event_payload"].get("tools_data", {}),
            "task_type": task_type,
        })
        
        state["result"] = result.get("result", {})
        return state

    def process_admin(self, state: ChiefOfStaffState) -> ChiefOfStaffState:
        """Route to Admin Desk and process."""
        event_type = state["event_type"]
        task_type = DESK_TASK_TYPES["admin"].get(event_type, "ea")
        
        admin_graph = self.admin.create_graph()
        result = admin_graph.invoke({
            "founder_id": state["founder_id"],
            "meeting_data": state["event_payload"].get("meeting_data", {}),
            "knowledge_data": state["event_payload"].get("knowledge_data", {}),
            "task_type": task_type,
        })
        
        state["result"] = result.get("result", {})
        return state

    def create_graph(self) -> StateGraph:
        """
        Create LangGraph workflow for Chief of Staff.
        
        Workflow:
        1. route_event: Determine which desk to route to
        2. Process with appropriate desk agent
        3. Return structured result
        
        Returns:
            Compiled LangGraph StateGraph
        """
        graph = StateGraph(ChiefOfStaffState)
        
        # Add routing node
        graph.add_node("route", self.route_event)
        
        # Add desk processing nodes
        graph.add_node("finance", self.process_finance)
        graph.add_node("people", self.process_people)
        graph.add_node("legal", self.process_legal)
        graph.add_node("intelligence", self.process_intelligence)
        graph.add_node("it", self.process_it)
        graph.add_node("admin", self.process_admin)
        
        # Set entry point
        graph.set_entry_point("route")
        
        # Add conditional edges from routing
        def route_to_desk(state: ChiefOfStaffState) -> str:
            """Route to appropriate desk based on routed_to field."""
            desk = state.get("routed_to", "admin")
            return desk
        
        graph.add_conditional_edges("route", route_to_desk)
        
        # All desks lead to END
        graph.add_edge("finance", END)
        graph.add_edge("people", END)
        graph.add_edge("legal", END)
        graph.add_edge("intelligence", END)
        graph.add_edge("it", END)
        graph.add_edge("admin", END)
        
        return graph.compile()


# Global instance for reuse
_chief_of_staff_agent: Optional[ChiefOfStaffAgent] = None


def get_chief_of_staff_agent() -> ChiefOfStaffAgent:
    """
    Get or create the global ChiefOfStaffAgent instance.
    
    Returns:
        ChiefOfStaffAgent: Singleton instance
    """
    global _chief_of_staff_agent
    if _chief_of_staff_agent is None:
        _chief_of_staff_agent = ChiefOfStaffAgent()
    return _chief_of_staff_agent
