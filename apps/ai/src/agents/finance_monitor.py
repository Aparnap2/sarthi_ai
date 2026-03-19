"""
Finance Monitor Agent - Sarthi v1.0.

Monitors:
- Spend anomalies (2σ threshold)
- Runway warnings (<6 months)
- Runway critical (<3 months)

Plain English alerts. No jargon.
"""
from __future__ import annotations
from src.agents.base import BaseAgent, AgentResult, BANNED_JARGON
from src.config.llm import get_llm_client, get_chat_model


class FinanceMonitorAgent(BaseAgent):
    """
    Finance monitoring agent for startup financial health.

    Detects:
    - Unusual vendor spend (>2 standard deviations)
    - Critical runway (<3 months)
    - Warning runway (<6 months)
    """

    agent_name = "finance_monitor"

    def run(self, state: dict, event: dict) -> dict:
        """
        Execute finance monitoring logic.

        Args:
            state: Current state with tenant_id, vendor_baselines, runway_months
            event: Triggering event (BANK_WEBHOOK, TIME_TICK_DAILY, etc.)

        Returns:
            Agent result as dictionary

        Raises:
            AssertionError: If tone validation fails
        """
        result = self._route(state, event)
        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        if result.fire_telegram:
            result.qdrant_point_id = self._write_qdrant_memory(
                state["tenant_id"],
                f"{result.headline} | urgency={result.urgency}",
                "finance_anomaly",
            )
        return result.__dict__

    def _route(self, state: dict, event: dict) -> AgentResult:
        """
        Route event to appropriate handler.

        Args:
            state: Current state
            event: Triggering event

        Returns:
            AgentResult from handler
        """
        etype = event.get("event_type", "")
        if etype in ("BANK_WEBHOOK", "EXPENSE_RECORDED", "PAYMENT_SUCCESS"):
            return self._handle_transaction(state, event)
        if etype in ("TIME_TICK_DAILY", "TIME_TICK_WEEKLY"):
            return self._handle_runway_check(state, event)
        return AgentResult(tenant_id=state["tenant_id"], agent_name=self.agent_name)

    def _handle_transaction(self, state: dict, event: dict) -> AgentResult:
        """
        Handle transaction events (bank webhooks, expenses).

        Args:
            state: Current state with vendor_baselines
            event: Transaction event with vendor, amount, description

        Returns:
            AgentResult with anomaly detection result
        """
        vendor = event.get("vendor", "Unknown vendor")
        amount = float(event.get("amount", 0))
        desc = event.get("description", "")
        tenant_id = state.get("tenant_id")
        baseline = state.get("vendor_baselines", {}).get(vendor)

        if not baseline:
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                output_json={"vendor": vendor, "amount": amount},
            )

        avg = float(baseline["avg"])
        stddev = float(baseline["stddev"])
        z_score = (amount - avg) / stddev if stddev > 0 else 0

        if z_score < 2.0:
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=False,
                output_json={
                    "vendor": vendor,
                    "amount": amount,
                    "z_score": round(z_score, 2),
                },
            )

        multiple = round(amount / avg, 1)
        headline = self._explain_anomaly(vendor, amount, avg, multiple, desc, tenant_id)

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=True,
            urgency="high",
            headline=headline,
            do_this="Check your AWS console → Cost Explorer → last 7 days.",
            output_json={
                "vendor": vendor,
                "amount": amount,
                "avg": avg,
                "z_score": round(z_score, 2),
                "multiple": multiple,
            },
        )

    def _handle_runway_check(self, state: dict, event: dict) -> AgentResult:
        """
        Handle runway check events (daily/weekly ticks).

        Args:
            state: Current state with runway_months
            event: Time tick event

        Returns:
            AgentResult with runway assessment
        """
        runway = float(state.get("runway_months", 99))
        if runway < 3:
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=True,
                urgency="critical",
                headline=f"Runway at {runway:.1f} months — less than 90 days. Needs attention now.",
                do_this="Review your biggest 3 expense lines and decide what to cut or defer.",
            )
        if runway < 6:
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=True,
                urgency="warn",
                headline=f"Runway at {runway:.1f} months. Healthy now, worth watching.",
                do_this="No action needed this week. Check again next month.",
            )
        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"runway_months": runway},
        )

    def _query_past_invoices(
        self,
        tenant_id: str,
        vendor: str,
        min_amount: float = 0,
    ) -> list[dict]:
        """
        Query ZincSearch for past invoices from this vendor.

        Uses vectorless BM25 + metadata filter search to retrieve
        exact historical invoice records.

        Args:
            tenant_id: Tenant identifier for multi-tenant isolation
            vendor: Vendor name to search for
            min_amount: Minimum amount threshold for filtering

        Returns:
            List of structured invoice records from ZincSearch
        """
        from apps.ai.src.search.zincsearch_client import ZincSearchClient

        zinc = ZincSearchClient()
        return zinc.search_by_vendor(
            index="sarthi-invoices",
            tenant_id=tenant_id,
            vendor=vendor,
            min_amount=min_amount,
        )

    def _explain_anomaly(
        self,
        vendor: str,
        amount: float,
        avg: float,
        multiple: float,
        desc: str,
        tenant_id: str,
    ) -> str:
        """
        Generate plain English explanation for spend anomaly with memory citation.

        Args:
            vendor: Vendor name
            amount: Transaction amount
            avg: Historical average
            multiple: How many times the average
            desc: Transaction description
            tenant_id: Tenant identifier for memory lookup

        Returns:
            Single-line alert message (max 20 words) that cites memory if available
        """
        # 1. Pull past invoices from ZincSearch (vectorless — exact filter)
        past_invoices = self._query_past_invoices(
            tenant_id, vendor, min_amount=avg * 1.5
        )

        # 2. Build memory context string from ZincSearch results
        if past_invoices:
            last = past_invoices[-1]
            memory_context = (
                f"Past high bill: ₹{last.get('amount'):,.0f} "
                f"on {last.get('doc_date', 'unknown date')}. "
                f"Category: {last.get('category', 'unknown')}."
            )
        else:
            memory_context = "First time seeing a high bill from this vendor."

        # 3. Call LLM with memory context
        client = get_llm_client()
        resp = client.chat.completions.create(
            model=get_chat_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write single-line financial alerts for startup founders.\n"
                        "Output ONLY the headline. No explanations. No reasoning.\n"
                        "Rules:\n"
                        "- Plain English. No jargon. Max 20 words.\n"
                        "- If historical context is available, reference it.\n"
                        "  Example: 'AWS 2.3× usual — last spike was a training run, no campaign running now.'\n"
                        "- If no history: state 'First time seeing this spike.'\n"
                        "- NEVER fabricate history. Only cite what memory provides."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Vendor: {vendor}\n"
                        f"This bill: ₹{amount:,.0f}\n"
                        f"Usual: ₹{avg:,.0f} ({multiple}×)\n"
                        f"Description: {desc}\n\n"
                        f"{memory_context}\n\n"
                        "Write ONLY the headline (max 20 words):"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=50,
        )
        # qwen3 outputs reasoning in 'reasoning' field, final answer in 'content'
        message = resp.choices[0].message
        content = message.content or ""
        reasoning = getattr(message, "reasoning", "")

        # If we have content, use it; otherwise try to extract from reasoning
        if content.strip():
            return content.strip()

        # Try to extract headline from reasoning (look for quoted text or final statement)
        if reasoning:
            # Look for patterns like "Headline: ..." or quoted text
            import re

            # Try to find quoted headline
            match = re.search(r'"([^"]+)"', reasoning)
            if match:
                return match.group(1).strip()
            # Try to find headline after colon
            match = re.search(r"headline:\s*(.+?)(?:\n|$)", reasoning, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]
            # Fall back to last sentence
            sentences = reasoning.split(".")
            if sentences:
                return sentences[-1].strip()[:100]

        return "AWS bill spike detected"  # Fallback headline

    def _query_qdrant_memory(self, tenant_id: str, vendor: str) -> list[dict]:
        """
        Pull past anomaly memory for this vendor from Qdrant.

        Args:
            tenant_id: Tenant identifier
            vendor: Vendor name to search for

        Returns:
            List of memory records (max 3) with content and metadata
        """
        from src.memory.qdrant_ops import query_memory

        results = query_memory(
            tenant_id=tenant_id,
            query_text=f"{vendor} spend spike anomaly",
            memory_types=["finance_anomaly"],
            top_k=3,
            min_score=0.7,
        )

        # Return list of dicts with content field
        return [
            {"content": r["content"], "score": r.get("score", 0)} for r in results
        ]
