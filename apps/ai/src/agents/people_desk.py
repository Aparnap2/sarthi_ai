"""
People Desk Agent — Sarthi v4.2 Phase 3.

Unified People Desk with 2 virtual employees:
- HR Coordinator: Onboarding, leave requests, appraisals, offboarding
- Internal Recruiter: JD drafting, interview scheduling, candidate coordination

All capabilities return structured PeopleOpsFinding with:
- Plain language (no HR jargon)
- Exactly ONE action
- Clear employee context
- HITL risk assessment

Usage:
    from src.agents.people_desk import PeopleDeskAgent
    
    agent = PeopleDeskAgent()
    graph = agent.create_graph()
    result = graph.invoke({
        "founder_id": "founder-uuid",
        "hr_events": [...],
        "task_type": "hr_coordinator",  # or "internal_recruiter"
    })
"""
from typing import TypedDict, Optional, List, Any
from langgraph.graph import StateGraph, END
import json

from src.schemas.desk_results import PeopleOpsFinding, HitlRisk
from src.config.llm import get_llm_client, get_chat_model


class PeopleDeskState(TypedDict):
    """
    State for People Desk workflow.
    
    Attributes:
        founder_id: Founder UUID for personalization
        hr_events: List of HR events to process
        task_type: Type of People task to perform
        employee_name: Target employee name (optional)
        result: Final PeopleOpsFinding (set by workflow)
    """
    founder_id: str
    hr_events: list
    task_type: str
    employee_name: Optional[str]
    result: Optional[PeopleOpsFinding]


class PeopleDeskAgent:
    """
    Unified People Desk agent with 2 virtual employees.
    
    Capabilities:
        - analyze_hr_coordinator: Onboarding, leave, appraisals, offboarding
        - analyze_internal_recruiter: JD drafting, interview scheduling
    
    Each capability uses LLM to analyze HR data and produce structured output
    with plain language, single action, and clear employee context.
    """

    def __init__(self):
        """Initialize PeopleDeskAgent with LLM client."""
        self.client = get_llm_client()
        self.model = get_chat_model()

    def analyze_hr_coordinator(self, state: PeopleDeskState) -> PeopleDeskState:
        """
        HR Coordinator capability: Employee lifecycle events.
        
        Handles onboarding, leave requests, appraisals, and offboarding.
        
        Args:
            state: PeopleDeskState with HR events
            
        Returns:
            Updated state with HR Coordinator analysis result
        """
        hr_events = state["hr_events"]
        employee_name = state.get("employee_name")
        
        context = self._build_hr_coordinator_context(hr_events, employee_name)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the HR Coordinator virtual employee for Sarthi.
Analyze HR events and return a JSON object with:
{
    "employee_name": str,
    "event_type": "onboarding" | "leave_request" | "appraisal" | "offboarding",
    "context": str,  # 2-3 sentences, plain language
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO jargon: PIP, attrition, headcount, FTE
- context: plain language, mention employee by name
- do_this: exactly ONE action (e.g., "Send welcome email to John")
- hitl_risk: high for offboarding, medium for leave requests, low for routine"""
                },
                {
                    "role": "user",
                    "content": f"HR events:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = PeopleOpsFinding(
            employee_name=result_data["employee_name"],
            event_type=result_data["event_type"],
            context=result_data["context"],
            do_this=result_data["do_this"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def analyze_internal_recruiter(self, state: PeopleDeskState) -> PeopleDeskState:
        """
        Internal Recruiter capability: Hiring coordination.
        
        Handles JD drafting, interview scheduling, candidate coordination.
        
        Args:
            state: PeopleDeskState with HR events
            
        Returns:
            Updated state with Internal Recruiter analysis result
        """
        hr_events = state["hr_events"]
        
        context = self._build_recruiter_context(hr_events)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the Internal Recruiter virtual employee for Sarthi.
Analyze hiring needs and return a JSON object with:
{
    "employee_name": str,  # Hiring manager name or "Recruitment Team"
    "event_type": "onboarding",  # Use onboarding for new hire coordination
    "context": str,  # 2-3 sentences about the role
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO jargon: headcount, FTE, requisition
- context: describe the role and urgency
- do_this: exactly ONE action (e.g., "Draft job description for Senior Engineer")
- hitl_risk: medium for new roles, low for scheduling"""
                },
                {
                    "role": "user",
                    "content": f"Recruitment data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = PeopleOpsFinding(
            employee_name=result_data["employee_name"],
            event_type=result_data["event_type"],
            context=result_data["context"],
            do_this=result_data["do_this"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def _build_hr_coordinator_context(self, hr_events: list, employee_name: Optional[str]) -> str:
        """Build context string for HR Coordinator analysis."""
        lines = []
        
        if employee_name:
            lines.append(f"Employee: {employee_name}")
        
        for event in hr_events:
            event_type = event.get("type", "unknown")
            lines.append(f"\nEvent Type: {event_type}")
            
            if event_type == "onboarding":
                lines.append(f"  Start Date: {event.get('start_date', 'TBD')}")
                lines.append(f"  Role: {event.get('role', 'Unknown')}")
                lines.append(f"  Department: {event.get('department', 'Unknown')}")
                
            elif event_type == "leave_request":
                lines.append(f"  Leave Type: {event.get('leave_type', 'Unknown')}")
                lines.append(f"  From: {event.get('from_date')}")
                lines.append(f"  To: {event.get('to_date')}")
                lines.append(f"  Reason: {event.get('reason', 'Personal')}")
                
            elif event_type == "appraisal":
                lines.append(f"  Review Type: {event.get('review_type', 'Annual')}")
                lines.append(f"  Due Date: {event.get('due_date', 'TBD')}")
                lines.append(f"  Current Rating: {event.get('current_rating', 'N/A')}")
                
            elif event_type == "offboarding":
                lines.append(f"  Last Day: {event.get('last_day', 'TBD')}")
                lines.append(f"  Reason: {event.get('reason', 'Unknown')}")
                lines.append(f"  Exit Interview: {event.get('exit_interview', 'Pending')}")
        
        return "\n".join(lines)

    def _build_recruiter_context(self, hr_events: list) -> str:
        """Build context string for Internal Recruiter analysis."""
        lines = []
        
        for event in hr_events:
            event_type = event.get("type", "unknown")
            
            if event_type == "hiring_request":
                lines.append(f"Role: {event.get('role', 'Unknown')}")
                lines.append(f"Department: {event.get('department', 'Unknown')}")
                lines.append(f"Priority: {event.get('priority', 'Normal')}")
                lines.append(f"Hiring Manager: {event.get('hiring_manager', 'Unknown')}")
                lines.append(f"Skills Required: {', '.join(event.get('skills', []))}")
                lines.append(f"Experience Level: {event.get('experience', 'Mid-level')}")
                lines.append(f"Budget: ₹{event.get('budget', 0):,} LPA")
                
            elif event_type == "interview_scheduled":
                lines.append(f"Candidate: {event.get('candidate_name', 'Unknown')}")
                lines.append(f"Role: {event.get('role', 'Unknown')}")
                lines.append(f"Interview Date: {event.get('interview_date', 'TBD')}")
                lines.append(f"Interviewers: {', '.join(event.get('interviewers', []))}")
        
        return "\n".join(lines)

    def create_graph(self) -> StateGraph:
        """
        Create LangGraph workflow for People Desk.
        
        Routes to appropriate capability based on task_type:
        - "hr_coordinator" → analyze_hr_coordinator
        - "internal_recruiter" → analyze_internal_recruiter
        
        Returns:
            Compiled LangGraph StateGraph
        """
        graph = StateGraph(PeopleDeskState)
        
        # Add nodes for each capability
        graph.add_node("hr_coordinator", self.analyze_hr_coordinator)
        graph.add_node("internal_recruiter", self.analyze_internal_recruiter)
        
        # Add routing logic
        def route_by_task_type(state: PeopleDeskState) -> str:
            """Route to appropriate capability based on task_type."""
            task_type = state.get("task_type", "hr_coordinator")
            
            routing_map = {
                "hr_coordinator": "hr_coordinator",
                "onboarding": "hr_coordinator",
                "leave_request": "hr_coordinator",
                "appraisal": "hr_coordinator",
                "offboarding": "hr_coordinator",
                "internal_recruiter": "internal_recruiter",
                "hiring_request": "internal_recruiter",
                "interview_scheduled": "internal_recruiter",
            }
            
            return routing_map.get(task_type, "hr_coordinator")
        
        # Add conditional entry point
        graph.set_conditional_entry_point(route_by_task_type)
        
        # All capabilities lead to END
        graph.add_edge("hr_coordinator", END)
        graph.add_edge("internal_recruiter", END)
        
        return graph.compile()


# Global instance for reuse
_people_desk_agent: Optional[PeopleDeskAgent] = None


def get_people_desk_agent() -> PeopleDeskAgent:
    """
    Get or create the global PeopleDeskAgent instance.
    
    Returns:
        PeopleDeskAgent: Singleton instance
    """
    global _people_desk_agent
    if _people_desk_agent is None:
        _people_desk_agent = PeopleDeskAgent()
    return _people_desk_agent
