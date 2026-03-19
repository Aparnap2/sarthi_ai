"""
Revenue Tracker Agent - Sarthi v1.0.

Monitors:
- MRR milestones (₹1L, ₹5L, ₹10L, ₹50L, ₹1Cr)
- Stale deals (>7 days no contact)
- Revenue concentration risk (>30% from one customer)

Plain English alerts. Celebrates wins.
"""
from __future__ import annotations
from datetime import datetime, timezone
from src.agents.base import BaseAgent, AgentResult

# MRR milestones in INR
MRR_MILESTONES_INR = [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]

# Stale deal threshold in days
STALE_DEAL_DAYS = 7

# Concentration risk threshold (30%)
CONCENTRATION_PCT = 0.30


class RevenueTrackerAgent(BaseAgent):
    """
    Revenue tracking agent for startup growth monitoring.

    Detects:
    - MRR milestone crossings
    - Stale deals in pipeline
    - Revenue concentration risk
    """

    agent_name = "revenue_tracker"

    def run(self, state: dict, event: dict) -> dict:
        """
        Execute revenue tracking logic.

        Args:
            state: Current state with tenant_id, pipeline_deals, last_30d_mrr
            event: Triggering event (PAYMENT_SUCCESS, TIME_TICK_WEEKLY, etc.)

        Returns:
            Agent result as dictionary

        Raises:
            AssertionError: If tone validation fails
        """
        etype = event.get("event_type", "")
        result = None
        if etype == "PAYMENT_SUCCESS":
            result = self._handle_payment(state, event)
        elif etype in ("CRM_DEAL_CREATED", "CRM_DEAL_UPDATED"):
            result = self._update_pipeline(state, event)
        elif etype == "TIME_TICK_WEEKLY":
            result = self._weekly_summary(state, event)
        else:
            result = AgentResult(tenant_id=state["tenant_id"], agent_name=self.agent_name)

        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        if result.fire_telegram or etype == "TIME_TICK_WEEKLY":
            result.qdrant_point_id = self._write_qdrant_memory(
                state["tenant_id"],
                f"Revenue event: {result.headline or etype}",
                "revenue",
            )
        return result.__dict__

    def _handle_payment(self, state: dict, event: dict) -> AgentResult:
        """
        Handle payment success events.

        Args:
            state: Current state with last_30d_mrr, top_customer_pct
            event: Payment event with amount, customer_name

        Returns:
            AgentResult with milestone or concentration alert
        """
        amount = float(event.get("amount", 0))
        customer = event.get("customer_name", "a customer")
        current_mrr = float(state.get("last_30d_mrr", 0))
        new_mrr = current_mrr + amount

        # Check for milestone crossing
        for milestone in MRR_MILESTONES_INR:
            if current_mrr < milestone <= new_mrr:
                headline = self._milestone_message(milestone, customer)
                return AgentResult(
                    tenant_id=state["tenant_id"],
                    agent_name=self.agent_name,
                    fire_telegram=True,
                    urgency="high",
                    is_good_news=True,
                    headline=headline,
                    output_json={"milestone": milestone, "new_mrr": new_mrr},
                )

        # Check for concentration risk
        top_customer_pct = float(state.get("top_customer_pct", 0))
        if top_customer_pct > CONCENTRATION_PCT:
            pct_display = f"{top_customer_pct * 100:.0f}%"
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=True,
                urgency="warn",
                headline=f"{customer} is now {pct_display} of your revenue — worth watching.",
                do_this="Consider pricing or terms diversification at renewal.",
                output_json={"concentration_pct": top_customer_pct},
            )

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"amount": amount, "customer": customer},
        )

    def _weekly_summary(self, state: dict, event: dict) -> AgentResult:
        """
        Generate weekly pipeline summary.

        Args:
            state: Current state with pipeline_deals
            event: Weekly time tick event

        Returns:
            AgentResult with stale deal alerts
        """
        stale = [
            d
            for d in state.get("pipeline_deals", [])
            if self._days_since(d.get("last_contact_at")) > STALE_DEAL_DAYS
            and d.get("stage") not in ("CLOSED_WON", "CLOSED_LOST")
        ]

        if stale:
            deal = stale[0]
            days = self._days_since(deal.get("last_contact_at"))
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=True,
                urgency="warn",
                headline=f"Deal with {deal.get('name', 'a prospect')} idle {days} days.",
                do_this="Send a 2-line check-in today.",
                output_json={"stale_deals": len(stale)},
            )

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"pipeline_healthy": True},
        )

    def _update_pipeline(self, state: dict, event: dict) -> AgentResult:
        """
        Update pipeline state from CRM events.

        Args:
            state: Current state
            event: CRM deal created/updated event

        Returns:
            AgentResult acknowledging update
        """
        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"pipeline_updated": True},
        )

    def _milestone_message(self, milestone: int, customer: str) -> str:
        """
        Generate milestone celebration message.

        Args:
            milestone: MRR milestone amount
            customer: Customer who pushed over milestone

        Returns:
            Celebration message
        """
        labels = {
            100_000: "₹1L",
            500_000: "₹5L",
            1_000_000: "₹10L",
            5_000_000: "₹50L",
            10_000_000: "₹1Cr",
        }
        label = labels.get(milestone, f"₹{milestone:,}")
        return f"You just crossed {label} MRR. {customer} pushed you over."

    def _days_since(self, iso_str: str | None) -> int:
        """
        Calculate days since ISO timestamp.

        Args:
            iso_str: ISO 8601 timestamp string

        Returns:
            Number of days since timestamp
        """
        if not iso_str:
            return 0
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
