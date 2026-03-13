"""
Finance Desk Agent — Sarthi v4.2 Phase 3.

Unified Finance Desk with 4 virtual employees:
- CFO: Runway analysis, burn rate, financial forecasting
- Bookkeeper: Transaction categorization, reconciliation
- AR/AP Clerk: Accounts receivable reminders, accounts payable tracking
- Payroll Clerk: Payroll preparation, statutory compliance

All capabilities return structured FinanceTaskResult with:
- Plain language (no finance jargon)
- Exactly ONE action
- Clear urgency and rupee impact
- HITL risk assessment

Usage:
    from src.agents.finance_desk import FinanceDeskAgent
    
    agent = FinanceDeskAgent()
    graph = agent.create_graph()
    result = graph.invoke({
        "founder_id": "founder-uuid",
        "bank_data": {...},
        "accounting_data": {...},
    })
"""
from typing import TypedDict, Optional, List, Any
from langgraph.graph import StateGraph, END
import json

from src.schemas.desk_results import FinanceTaskResult, HitlRisk
from src.config.llm import get_llm_client, get_chat_model


class FinanceDeskState(TypedDict):
    """
    State for Finance Desk workflow.
    
    Attributes:
        founder_id: Founder UUID for personalization
        bank_data: Bank statement/transaction data
        accounting_data: Accounting ledger data
        task_type: Type of finance task to perform
        result: Final FinanceTaskResult (set by workflow)
    """
    founder_id: str
    bank_data: dict
    accounting_data: dict
    task_type: str
    result: Optional[FinanceTaskResult]


class FinanceDeskAgent:
    """
    Unified Finance Desk agent with 4 virtual employees.
    
    Capabilities:
        - analyze_cfo: Strategic financial analysis (runway, burn, forecast)
        - analyze_bookkeeper: Transaction categorization and reconciliation
        - analyze_ar_ap: Accounts receivable/payable management
        - analyze_payroll: Payroll preparation and compliance
    
    Each capability uses LLM to analyze data and produce structured output
    with plain language, single action, and clear urgency.
    """

    def __init__(self):
        """Initialize FinanceDeskAgent with LLM client."""
        self.client = get_llm_client()
        self.model = get_chat_model()

    def analyze_cfo(self, state: FinanceDeskState) -> FinanceDeskState:
        """
        CFO capability: Strategic financial analysis.
        
        Analyzes runway, burn rate, and financial forecasts.
        Returns actionable insights with rupee impact.
        
        Args:
            state: FinanceDeskState with bank and accounting data
            
        Returns:
            Updated state with CFO analysis result
        """
        bank_data = state["bank_data"]
        accounting_data = state["accounting_data"]
        
        # Build context for LLM
        context = self._build_cfo_context(bank_data, accounting_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the CFO virtual employee for Sarthi.
Analyze the financial data and return a JSON object with:
{
    "headline": str,  # Max 10 words, no jargon
    "what_is_true": str,  # 2-3 sentences with ₹ amounts
    "do_this": str,  # Exactly ONE action, verb-first
    "urgency": "today" | "this_week" | "this_month",
    "rupee_impact": int | null,
    "hitl_risk": "low" | "medium" | "high",
    "is_good_news": bool
}

RULES:
- NO jargon: EBITDA, DSO, bps, working capital, liquidity, accrual, amortization
- Headline: max 10 words
- do_this: exactly ONE action (no "and", "then", "also")
- Use plain language a founder can understand
- Always include ₹ amounts where relevant"""
                },
                {
                    "role": "user",
                    "content": f"Financial data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = FinanceTaskResult(
            task_type="reconciliation",
            headline=result_data["headline"],
            what_is_true=result_data["what_is_true"],
            do_this=result_data["do_this"],
            urgency=result_data["urgency"],
            rupee_impact=result_data.get("rupee_impact"),
            hitl_risk=HitlRisk(result_data["hitl_risk"]),
            is_good_news=result_data.get("is_good_news", False)
        )
        
        return state

    def analyze_bookkeeper(self, state: FinanceDeskState) -> FinanceDeskState:
        """
        Bookkeeper capability: Transaction categorization and reconciliation.
        
        Categorizes uncategorized transactions and identifies reconciliation issues.
        
        Args:
            state: FinanceDeskState with bank and accounting data
            
        Returns:
            Updated state with Bookkeeper analysis result
        """
        bank_data = state["bank_data"]
        
        context = self._build_bookkeeper_context(bank_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the Bookkeeper virtual employee for Sarthi.
Analyze transactions and return a JSON object with:
{
    "headline": str,  # Max 10 words
    "what_is_true": str,  # 2-3 sentences with ₹ amounts
    "do_this": str,  # Exactly ONE action
    "urgency": "today" | "this_week" | "this_month",
    "rupee_impact": int | null,
    "hitl_risk": "low" | "medium" | "high",
    "is_good_news": bool
}

RULES:
- NO jargon: reconciliation, accrual, amortization
- Focus on uncategorized transactions or mismatches
- do_this: exactly ONE action"""
                },
                {
                    "role": "user",
                    "content": f"Transaction data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = FinanceTaskResult(
            task_type="reconciliation",
            headline=result_data["headline"],
            what_is_true=result_data["what_is_true"],
            do_this=result_data["do_this"],
            urgency=result_data["urgency"],
            rupee_impact=result_data.get("rupee_impact"),
            hitl_risk=HitlRisk(result_data["hitl_risk"]),
            is_good_news=result_data.get("is_good_news", False)
        )
        
        return state

    def analyze_ar_ap(self, state: FinanceDeskState) -> FinanceDeskState:
        """
        AR/AP Clerk capability: Accounts receivable and payable management.
        
        Identifies overdue invoices, upcoming payments, and aging issues.
        
        Args:
            state: FinanceDeskState with bank and accounting data
            
        Returns:
            Updated state with AR/AP analysis result
        """
        accounting_data = state["accounting_data"]
        
        context = self._build_ar_ap_context(accounting_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the AR/AP Clerk virtual employee for Sarthi.
Analyze receivables and payables, return JSON:
{
    "headline": str,  # Max 10 words
    "what_is_true": str,  # 2-3 sentences with ₹ amounts
    "do_this": str,  # Exactly ONE action
    "urgency": "today" | "this_week" | "this_month",
    "rupee_impact": int | null,
    "hitl_risk": "low" | "medium" | "high",
    "is_good_news": bool
}

RULES:
- NO jargon: DSO, aging, working capital
- Focus on payments due or overdue
- do_this: exactly ONE action (e.g., "Send reminder to Customer X")"""
                },
                {
                    "role": "user",
                    "content": f"AR/AP data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        # Determine task type based on analysis
        task_type = "ar_reminder" if "receivable" in context.lower() or "invoice" in context.lower() else "ap_due"
        
        state["result"] = FinanceTaskResult(
            task_type=task_type,
            headline=result_data["headline"],
            what_is_true=result_data["what_is_true"],
            do_this=result_data["do_this"],
            urgency=result_data["urgency"],
            rupee_impact=result_data.get("rupee_impact"),
            hitl_risk=HitlRisk(result_data["hitl_risk"]),
            is_good_news=result_data.get("is_good_news", False)
        )
        
        return state

    def analyze_payroll(self, state: FinanceDeskState) -> FinanceDeskState:
        """
        Payroll Clerk capability: Payroll preparation and statutory compliance.
        
        Prepares payroll data, identifies compliance requirements.
        
        Args:
            state: FinanceDeskState with bank and accounting data
            
        Returns:
            Updated state with Payroll analysis result
        """
        accounting_data = state["accounting_data"]
        
        context = self._build_payroll_context(accounting_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are the Payroll Clerk virtual employee for Sarthi.
Analyze payroll data, return JSON:
{
    "headline": str,  # Max 10 words
    "what_is_true": str,  # 2-3 sentences with ₹ amounts
    "do_this": str,  # Exactly ONE action
    "urgency": "today" | "this_week" | "this_month",
    "rupee_impact": int | null,
    "hitl_risk": "low" | "medium" | "high",
    "is_good_news": bool
}

RULES:
- NO jargon: statutory, compliance, TDS, PF, ESIC (use plain terms)
- Focus on payroll dates and amounts
- do_this: exactly ONE action"""
                },
                {
                    "role": "user",
                    "content": f"Payroll data:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_data = json.loads(response.choices[0].message.content)
        
        state["result"] = FinanceTaskResult(
            task_type="payroll_prep",
            headline=result_data["headline"],
            what_is_true=result_data["what_is_true"],
            do_this=result_data["do_this"],
            urgency=result_data["urgency"],
            rupee_impact=result_data.get("rupee_impact"),
            hitl_risk=HitlRisk(result_data["hitl_risk"]),
            is_good_news=result_data.get("is_good_news", False)
        )
        
        return state

    def _build_cfo_context(self, bank_data: dict, accounting_data: dict) -> str:
        """Build context string for CFO analysis."""
        lines = []
        
        if bank_data:
            lines.append(f"Bank Balance: ₹{bank_data.get('balance', 0):,}")
            lines.append(f"Monthly Inflow: ₹{bank_data.get('monthly_inflow', 0):,}")
            lines.append(f"Monthly Outflow: ₹{bank_data.get('monthly_outflow', 0):,}")
        
        if accounting_data:
            lines.append(f"Monthly Revenue: ₹{accounting_data.get('revenue', 0):,}")
            lines.append(f"Monthly Expenses: ₹{accounting_data.get('expenses', 0):,}")
        
        return "\n".join(lines)

    def _build_bookkeeper_context(self, bank_data: dict) -> str:
        """Build context string for Bookkeeper analysis."""
        lines = []
        
        transactions = bank_data.get("transactions", [])
        uncategorized = [t for t in transactions if not t.get("category")]
        
        lines.append(f"Total Transactions: {len(transactions)}")
        lines.append(f"Uncategorized: {len(uncategorized)}")
        
        if uncategorized:
            lines.append("\nUncategorized Transactions:")
            for t in uncategorized[:5]:  # Show first 5
                lines.append(f"  - ₹{t.get('amount', 0):,}: {t.get('description', 'Unknown')}")
        
        return "\n".join(lines)

    def _build_ar_ap_context(self, accounting_data: dict) -> str:
        """Build context string for AR/AP analysis."""
        lines = []
        
        invoices = accounting_data.get("invoices", [])
        overdue = [i for i in invoices if i.get("status") == "overdue"]
        due_soon = [i for i in invoices if i.get("status") == "pending"]
        
        lines.append(f"Total Invoices: {len(invoices)}")
        lines.append(f"Overdue: {len(overdue)}")
        lines.append(f"Due Soon: {len(due_soon)}")
        
        if overdue:
            lines.append("\nOverdue Invoices:")
            for inv in overdue[:5]:
                lines.append(f"  - #{inv.get('number')}: ₹{inv.get('amount', 0):,} ({inv.get('days_overdue', 0)} days)")
        
        return "\n".join(lines)

    def _build_payroll_context(self, accounting_data: dict) -> str:
        """Build context string for Payroll analysis."""
        lines = []
        
        employees = accounting_data.get("employees", [])
        next_payroll = accounting_data.get("next_payroll_date", "Unknown")
        total_payroll = accounting_data.get("total_payroll", 0)
        
        lines.append(f"Employees: {len(employees)}")
        lines.append(f"Next Payroll Date: {next_payroll}")
        lines.append(f"Total Payroll Amount: ₹{total_payroll:,}")
        
        return "\n".join(lines)

    def create_graph(self) -> StateGraph:
        """
        Create LangGraph workflow for Finance Desk.
        
        Routes to appropriate capability based on task_type:
        - "cfo" → analyze_cfo
        - "bookkeeper" → analyze_bookkeeper
        - "ar_ap" → analyze_ar_ap
        - "payroll" → analyze_payroll
        
        Returns:
            Compiled LangGraph StateGraph
        """
        graph = StateGraph(FinanceDeskState)
        
        # Add nodes for each capability
        graph.add_node("cfo", self.analyze_cfo)
        graph.add_node("bookkeeper", self.analyze_bookkeeper)
        graph.add_node("ar_ap", self.analyze_ar_ap)
        graph.add_node("payroll", self.analyze_payroll)
        
        # Add routing logic
        def route_by_task_type(state: FinanceDeskState) -> str:
            """Route to appropriate capability based on task_type."""
            task_type = state.get("task_type", "cfo")
            
            routing_map = {
                "cfo": "cfo",
                "bookkeeper": "bookkeeper",
                "ar_ap": "ar_ap",
                "ar_reminder": "ar_ap",
                "ap_due": "ar_ap",
                "payroll": "payroll",
                "payroll_prep": "payroll",
                "reconciliation": "bookkeeper",
            }
            
            return routing_map.get(task_type, "cfo")
        
        # Add conditional edges
        graph.set_conditional_entry_point(route_by_task_type)
        
        # All capabilities lead to END
        graph.add_edge("cfo", END)
        graph.add_edge("bookkeeper", END)
        graph.add_edge("ar_ap", END)
        graph.add_edge("payroll", END)
        
        return graph.compile()


# Global instance for reuse
_finance_desk_agent: Optional[FinanceDeskAgent] = None


def get_finance_desk_agent() -> FinanceDeskAgent:
    """
    Get or create the global FinanceDeskAgent instance.
    
    Returns:
        FinanceDeskAgent: Singleton instance
    """
    global _finance_desk_agent
    if _finance_desk_agent is None:
        _finance_desk_agent = FinanceDeskAgent()
    return _finance_desk_agent
