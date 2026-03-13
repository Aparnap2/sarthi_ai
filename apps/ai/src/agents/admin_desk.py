"""
Admin Desk Agent — Sarthi v4.2 Phase 3.

Unified Admin Desk with 2 virtual employees:
- EA (Executive Assistant): Meeting coordination, calendar management, task tracking
- Knowledge Manager: SOP extraction, knowledge graph updates, documentation

All capabilities return structured results with:
- Plain language
- Exactly ONE action
- Clear context
- HITL risk assessment

Usage:
    from src.agents.admin_desk import AdminDeskAgent
    
    agent = AdminDeskAgent()
    graph = agent.create_graph()
    result = graph.invoke({
        "founder_id": "founder-uuid",
        "meeting_data": {...},
        "knowledge_data": {...},
        "task_type": "ea",  # or "knowledge_manager"
    })
"""
from typing import TypedDict, Optional, List, Any
from langgraph.graph import StateGraph, END
import json

from src.schemas.desk_results import KnowledgeManagerResult, HitlRisk
from src.config.llm import get_llm_client, get_chat_model


class AdminDeskState(TypedDict):
    """
    State for Admin Desk workflow.
    
    Attributes:
        founder_id: Founder UUID for personalization
        meeting_data: Meeting and calendar data
        knowledge_data: Knowledge and documentation data
        task_type: Type of Admin task to perform
        result: Final result (set by workflow)
    """
    founder_id: str
    meeting_data: dict
    knowledge_data: dict
    task_type: str
    result: Optional[dict]


class AdminDeskAgent:
    """
    Unified Admin Desk agent with 2 virtual employees.
    
    Capabilities:
        - analyze_ea: Meeting coordination, calendar management, task tracking
        - analyze_knowledge_manager: SOP extraction, knowledge graph updates
    
    Each capability uses LLM to analyze data and produce structured output
    with plain language, single action, and clear context.
    """

    def __init__(self):
        """Initialize AdminDeskAgent with LLM client."""
        self.client = get_llm_client()
        self.model = get_chat_model()

    def analyze_ea(self, state: AdminDeskState) -> AdminDeskState:
        """
        EA (Executive Assistant) capability: Meeting and calendar management.
        
        Coordinates meetings, manages calendar, tracks action items.
        
        Args:
            state: AdminDeskState with meeting data
            
        Returns:
            Updated state with EA analysis result
        """
        meeting_data = state["meeting_data"]
        
        context = self._build_ea_context(meeting_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the EA (Executive Assistant) virtual employee for Sarthi.
Analyze meeting and calendar data, return a JSON object with:
{
    "topic": str,  # Meeting or task topic
    "extracted_sop": str,  # Step-by-step instructions if applicable
    "neo4j_nodes_added": int,  # Number of knowledge items created
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- Plain language only
- extracted_sop: step-by-step format (numbered or bulleted)
- do_this: exactly ONE action (e.g., "Schedule follow-up with Team X")
- hitl_risk: high for important meetings, low for routine scheduling
- If no SOP applicable, set extracted_sop to "N/A" and neo4j_nodes_added to 0"""
                },
                {
                    "role": "user",
                    "content": f"Meeting data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        # Return as dict that matches KnowledgeManagerResult structure for consistency
        state["result"] = {
            "topic": result_data["topic"],
            "extracted_sop": result_data["extracted_sop"],
            "neo4j_nodes_added": result_data["neo4j_nodes_added"],
            "do_this": result_data["do_this"],
            "hitl_risk": result_data["hitl_risk"],
            "result_type": "ea_task"
        }
        
        return state

    def analyze_knowledge_manager(self, state: AdminDeskState) -> AdminDeskState:
        """
        Knowledge Manager capability: SOP extraction and knowledge graph updates.
        
        Extracts SOPs from meetings/documents, updates knowledge graph.
        
        Args:
            state: AdminDeskState with knowledge data
            
        Returns:
            Updated state with Knowledge Manager analysis result
        """
        knowledge_data = state["knowledge_data"]
        
        context = self._build_knowledge_context(knowledge_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the Knowledge Manager virtual employee for Sarthi.
Extract SOPs and update knowledge graph, return a JSON object with:
{
    "topic": str,  # Topic of the knowledge
    "extracted_sop": str,  # Step-by-step SOP (numbered or bulleted)
    "neo4j_nodes_added": int,  # Number of knowledge graph nodes created
    "do_this": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- Plain language only
- extracted_sop: MUST have step-by-step structure (1., 2., 3. or -, *, •)
- extracted_sop: at least 20 characters
- neo4j_nodes_added: count of concepts/entities extracted
- do_this: exactly ONE action (e.g., "Save to Notion knowledge base")
- hitl_risk: low for routine documentation"""
                },
                {
                    "role": "user",
                    "content": f"Knowledge data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = KnowledgeManagerResult(
            topic=result_data["topic"],
            extracted_sop=result_data["extracted_sop"],
            neo4j_nodes_added=result_data["neo4j_nodes_added"],
            do_this=result_data["do_this"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def _build_ea_context(self, meeting_data: dict) -> str:
        """Build context string for EA analysis."""
        lines = []
        
        # Upcoming meetings
        meetings = meeting_data.get("meetings", [])
        upcoming = [m for m in meetings if m.get("status") == "scheduled"]
        
        lines.append(f"Total Meetings: {len(meetings)}")
        lines.append(f"Upcoming: {len(upcoming)}")
        
        if upcoming:
            lines.append("\nUpcoming Meetings:")
            for meeting in upcoming[:5]:
                lines.append(f"  - {meeting.get('title', 'Untitled')}: {meeting.get('date', 'TBD')}")
                lines.append(f"    Attendees: {', '.join(meeting.get('attendees', []))}")
                lines.append(f"    Duration: {meeting.get('duration_minutes', 0)} minutes")
        
        # Action items
        action_items = meeting_data.get("action_items", [])
        pending = [a for a in action_items if a.get("status") == "pending"]
        
        lines.append(f"\nPending Action Items: {len(pending)}")
        for item in pending[:5]:
            lines.append(f"  - {item.get('description', 'Unknown')} (Due: {item.get('due_date', 'TBD')})")
        
        return "\n".join(lines)

    def _build_knowledge_context(self, knowledge_data: dict) -> str:
        """Build context string for Knowledge Manager analysis."""
        lines = []
        
        # Documents to process
        documents = knowledge_data.get("documents", [])
        
        lines.append(f"Documents to Process: {len(documents)}")
        
        if documents:
            lines.append("\nDocuments:")
            for doc in documents[:5]:
                lines.append(f"  - {doc.get('title', 'Untitled')}")
                lines.append(f"    Type: {doc.get('type', 'Unknown')}")
                lines.append(f"    Content Preview: {doc.get('preview', 'No preview')[:100]}...")
        
        # Existing knowledge graph stats
        kg_stats = knowledge_data.get("knowledge_graph_stats", {})
        lines.append(f"\nKnowledge Graph Stats:")
        lines.append(f"  Total Nodes: {kg_stats.get('total_nodes', 0)}")
        lines.append(f"  Total Relationships: {kg_stats.get('total_relationships', 0)}")
        
        return "\n".join(lines)

    def create_graph(self) -> StateGraph:
        """
        Create LangGraph workflow for Admin Desk.
        
        Routes to appropriate capability based on task_type:
        - "ea" → analyze_ea
        - "knowledge_manager" → analyze_knowledge_manager
        
        Returns:
            Compiled LangGraph StateGraph
        """
        graph = StateGraph(AdminDeskState)
        
        # Add nodes for each capability
        graph.add_node("ea", self.analyze_ea)
        graph.add_node("knowledge_manager", self.analyze_knowledge_manager)
        
        # Add routing logic
        def route_by_task_type(state: AdminDeskState) -> str:
            """Route to appropriate capability based on task_type."""
            task_type = state.get("task_type", "ea")
            
            routing_map = {
                "ea": "ea",
                "meeting_transcript": "ea",
                "calendar_management": "ea",
                "task_tracking": "ea",
                "knowledge_manager": "knowledge_manager",
                "sop_extraction": "knowledge_manager",
                "documentation": "knowledge_manager",
            }
            
            return routing_map.get(task_type, "ea")
        
        # Add conditional entry point
        graph.set_conditional_entry_point(route_by_task_type)
        
        # All capabilities lead to END
        graph.add_edge("ea", END)
        graph.add_edge("knowledge_manager", END)
        
        return graph.compile()


# Global instance for reuse
_admin_desk_agent: Optional[AdminDeskAgent] = None


def get_admin_desk_agent() -> AdminDeskAgent:
    """
    Get or create the global AdminDeskAgent instance.
    
    Returns:
        AdminDeskAgent: Singleton instance
    """
    global _admin_desk_agent
    if _admin_desk_agent is None:
        _admin_desk_agent = AdminDeskAgent()
    return _admin_desk_agent
