"""
Legal Desk Agent — Sarthi v4.2 Phase 3.

Unified Legal Desk with 2 virtual employees:
- Contracts Coordinator: Contract tracking, expiry management, renewal coordination
- Compliance Tracker: Regulatory compliance, policy updates, audit preparation

All capabilities return structured LegalOpsResult with:
- Plain language (no legalese)
- Exactly ONE action
- Clear document context
- HITL risk assessment

Usage:
    from src.agents.legal_desk import LegalDeskAgent
    
    agent = LegalDeskAgent()
    graph = agent.create_graph()
    result = graph.invoke({
        "founder_id": "founder-uuid",
        "legal_documents": [...],
        "task_type": "contracts",  # or "compliance"
    })
"""
from typing import TypedDict, Optional, List, Any
from langgraph.graph import StateGraph, END
import json

from src.schemas.desk_results import LegalOpsResult, HitlRisk
from src.config.llm import get_llm_client, get_chat_model


class LegalDeskState(TypedDict):
    """
    State for Legal Desk workflow.
    
    Attributes:
        founder_id: Founder UUID for personalization
        legal_documents: List of legal documents to process
        task_type: Type of Legal task to perform
        result: Final LegalOpsResult (set by workflow)
    """
    founder_id: str
    legal_documents: list
    task_type: str
    result: Optional[LegalOpsResult]


class LegalDeskAgent:
    """
    Unified Legal Desk agent with 2 virtual employees.
    
    Capabilities:
        - analyze_contracts: Contract tracking, expiry, renewals
        - analyze_compliance: Regulatory compliance, policy updates
    
    Each capability uses LLM to analyze legal data and produce structured output
    with plain language, single action, and clear document context.
    """

    def __init__(self):
        """Initialize LegalDeskAgent with LLM client."""
        self.client = get_llm_client()
        self.model = get_chat_model()

    def analyze_contracts(self, state: LegalDeskState) -> LegalDeskState:
        """
        Contracts Coordinator capability: Contract lifecycle management.
        
        Tracks contract expiries, manages renewals, identifies issues.
        
        Args:
            state: LegalDeskState with legal documents
            
        Returns:
            Updated state with Contracts analysis result
        """
        legal_documents = state["legal_documents"]
        
        context = self._build_contracts_context(legal_documents)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the Contracts Coordinator virtual employee for Sarthi.
Analyze contracts and return a JSON object with:
{
    "document_type": str,  # e.g., "Vendor Contract", "Customer Agreement"
    "document_name": str,  # Specific contract name
    "expiry_date": str | null,  # ISO format: YYYY-MM-DD
    "action_required": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO legalese: heretofore, whereas, notwithstanding, force majeure, indemnification
- action_required: plain language (e.g., "Renew contract with Vendor X")
- hitl_risk: high for expiring soon, medium for review needed, low for routine"""
                },
                {
                    "role": "user",
                    "content": f"Contract data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = LegalOpsResult(
            document_type=result_data["document_type"],
            document_name=result_data["document_name"],
            expiry_date=result_data.get("expiry_date"),
            action_required=result_data["action_required"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def analyze_compliance(self, state: LegalDeskState) -> LegalDeskState:
        """
        Compliance Tracker capability: Regulatory compliance management.
        
        Tracks compliance requirements, policy updates, audit preparation.
        
        Args:
            state: LegalDeskState with legal documents
            
        Returns:
            Updated state with Compliance analysis result
        """
        legal_documents = state["legal_documents"]
        
        context = self._build_compliance_context(legal_documents)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the Compliance Tracker virtual employee for Sarthi.
Analyze compliance requirements and return a JSON object with:
{
    "document_type": str,  # e.g., "Compliance Policy", "Regulatory Filing"
    "document_name": str,  # Specific compliance item name
    "expiry_date": str | null,  # Due date in ISO format
    "action_required": str,  # Exactly ONE action
    "hitl_risk": "low" | "medium" | "high"
}

RULES:
- NO legalese: jurisdiction, liability, indemnification
- action_required: plain language (e.g., "File monthly GST return")
- hitl_risk: high for regulatory deadlines, medium for policy updates"""
                },
                {
                    "role": "user",
                    "content": f"Compliance data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = LegalOpsResult(
            document_type=result_data["document_type"],
            document_name=result_data["document_name"],
            expiry_date=result_data.get("expiry_date"),
            action_required=result_data["action_required"],
            hitl_risk=HitlRisk(result_data["hitl_risk"])
        )
        
        return state

    def _build_contracts_context(self, legal_documents: list) -> str:
        """Build context string for Contracts analysis."""
        lines = []
        
        contracts = [d for d in legal_documents if d.get("type") == "contract"]
        expiring_soon = [c for c in contracts if c.get("days_until_expiry", 999) < 30]
        
        lines.append(f"Total Contracts: {len(contracts)}")
        lines.append(f"Expiring in 30 days: {len(expiring_soon)}")
        
        if expiring_soon:
            lines.append("\nExpiring Soon:")
            for contract in expiring_soon[:5]:
                lines.append(f"  - {contract.get('name', 'Unknown')}: {contract.get('days_until_expiry', 0)} days left")
                lines.append(f"    Value: ₹{contract.get('value', 0):,}")
                lines.append(f"    Counterparty: {contract.get('counterparty', 'Unknown')}")
        
        return "\n".join(lines)

    def _build_compliance_context(self, legal_documents: list) -> str:
        """Build context string for Compliance analysis."""
        lines = []
        
        compliance_items = [d for d in legal_documents if d.get("type") == "compliance"]
        overdue = [c for c in compliance_items if c.get("status") == "overdue"]
        due_soon = [c for c in compliance_items if c.get("status") == "pending"]
        
        lines.append(f"Total Compliance Items: {len(compliance_items)}")
        lines.append(f"Overdue: {len(overdue)}")
        lines.append(f"Due Soon: {len(due_soon)}")
        
        if overdue:
            lines.append("\nOverdue:")
            for item in overdue[:5]:
                lines.append(f"  - {item.get('name', 'Unknown')}: {item.get('days_overdue', 0)} days overdue")
                lines.append(f"    Penalty: ₹{item.get('penalty', 0):,}")
        
        if due_soon:
            lines.append("\nDue Soon:")
            for item in due_soon[:5]:
                lines.append(f"  - {item.get('name', 'Unknown')}: Due in {item.get('days_until_due', 0)} days")
        
        return "\n".join(lines)

    def create_graph(self) -> StateGraph:
        """
        Create LangGraph workflow for Legal Desk.
        
        Routes to appropriate capability based on task_type:
        - "contracts" → analyze_contracts
        - "compliance" → analyze_compliance
        
        Returns:
            Compiled LangGraph StateGraph
        """
        graph = StateGraph(LegalDeskState)
        
        # Add nodes for each capability
        graph.add_node("contracts", self.analyze_contracts)
        graph.add_node("compliance", self.analyze_compliance)
        
        # Add routing logic
        def route_by_task_type(state: LegalDeskState) -> str:
            """Route to appropriate capability based on task_type."""
            task_type = state.get("task_type", "contracts")
            
            routing_map = {
                "contracts": "contracts",
                "contract_uploaded": "contracts",
                "contract_expiry": "contracts",
                "compliance": "compliance",
                "regulatory_filing": "compliance",
                "policy_update": "compliance",
            }
            
            return routing_map.get(task_type, "contracts")
        
        # Add conditional entry point
        graph.set_conditional_entry_point(route_by_task_type)
        
        # All capabilities lead to END
        graph.add_edge("contracts", END)
        graph.add_edge("compliance", END)
        
        return graph.compile()


# Global instance for reuse
_legal_desk_agent: Optional[LegalDeskAgent] = None


def get_legal_desk_agent() -> LegalDeskAgent:
    """
    Get or create the global LegalDeskAgent instance.
    
    Returns:
        LegalDeskAgent: Singleton instance
    """
    global _legal_desk_agent
    if _legal_desk_agent is None:
        _legal_desk_agent = LegalDeskAgent()
    return _legal_desk_agent
