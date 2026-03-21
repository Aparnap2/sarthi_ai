"""
SOP: Revenue Received — Razorpay payment.captured handler.

Triggered when a payment is successfully captured.
Silent for normal payments, fires alert for milestones or concentration risk.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from src.sops.base import BaseSOP, SOPResult, BANNED_JARGON
from src.sops.registry import register


# MRR milestones that trigger celebratory alerts
MRR_MILESTONES = [100_000, 500_000, 1_000_000, 5_000_000]

# Concentration risk threshold (customer > 30% of revenue)
CONCENTRATION_THRESHOLD = 0.30


class RevenueReceivedSOP(BaseSOP):
    """
    SOP for handling revenue received events.

    Triggers:
    - Razorpay payment.captured webhook
    - Stripe charge.succeeded webhook
    - Manual revenue entry

    Behavior:
    - Logs transaction to PostgreSQL
    - Updates 13-week cash flow forecast
    - Checks for MRR milestones
    - Checks for customer concentration risk
    - Fires alert only for milestones or concentration risk
    """
    sop_name = "SOP_REVENUE_RECEIVED"

    async def execute(self, payload_ref: str, founder_id: str) -> SOPResult:
        """
        Execute SOP_REVENUE_RECEIVED.

        Args:
            payload_ref: Reference to raw_events table
            founder_id: Founder who owns this event

        Returns:
            SOPResult with execution outcome
        """
        # 1. Fetch payload from PostgreSQL
        raw = self.fetch_payload(payload_ref)
        
        # 2. Extract payment entity from Razorpay payload
        entity = self._extract_payment_entity(raw)
        amount_inr = entity.get("amount", 0) / 100  # Convert paise to rupees
        currency = entity.get("currency", "INR")
        description = entity.get("description", "Payment received")
        customer_id = entity.get("customer_id", entity.get("contact", ""))
        payment_id = entity.get("id", "unknown")

        # 3. Write transaction to PostgreSQL
        self._write_transaction(
            founder_id=founder_id,
            description=description,
            credit=amount_inr,
            category="Revenue",
            confidence=1.0,  # Auto high-confidence for revenue
            source="razorpay",
            external_id=payment_id,
            raw_event_id=self._extract_raw_event_id(payload_ref),
        )

        # 4. Check for MRR milestones
        milestones = self._check_mrr_milestones(founder_id, amount_inr)

        # 5. Check for customer concentration risk
        concentration = self._check_concentration_risk(
            founder_id=founder_id,
            customer_id=customer_id,
            new_amount=amount_inr,
        )

        # 6. Determine if we should fire an alert
        fire_alert = bool(milestones or concentration)
        is_good_news = bool(milestones)

        # 7. Compose headline (jargon-free)
        headline = ""
        if milestones:
            milestone_str = self._format_milestone(milestones[0])
            headline = f"You just crossed {milestone_str} — your runway just got longer."
        elif concentration:
            pct = int(concentration["pct"] * 100)
            name = concentration.get("name", "this customer")
            headline = f"{name} is now {pct}% of your revenue — worth watching."

        # 8. Log to memory (Qdrant)
        self._log_to_memory(
            founder_id=founder_id,
            content=f"₹{amount_inr:,.0f} received via Razorpay: {description}",
            memory_type="revenue_event",
            source="razorpay",
        )

        return SOPResult(
            sop_name=self.sop_name,
            founder_id=founder_id,
            success=True,
            fire_alert=fire_alert,
            hitl_risk="low",
            headline=headline,
            do_this="Review the details in your dashboard." if fire_alert else "",
            is_good_news=is_good_news,
            output={
                "milestones_hit": milestones,
                "concentration": concentration,
                "amount_inr": amount_inr,
                "currency": currency,
                "payment_id": payment_id,
            },
        )

    def _extract_payment_entity(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Extract payment entity from raw payload."""
        try:
            return raw.get("payload", {}).get("payment", {}).get("entity", {})
        except (AttributeError, KeyError):
            return {}

    def _extract_raw_event_id(self, payload_ref: str) -> str:
        """Extract raw event UUID from payload_ref."""
        if ":" in payload_ref:
            return payload_ref.split(":", 1)[1]
        return payload_ref

    def _write_transaction(
        self,
        founder_id: str,
        description: str,
        credit: float,
        category: str,
        confidence: float,
        source: str,
        external_id: str,
        raw_event_id: Optional[str] = None,
    ) -> None:
        """Write transaction to PostgreSQL."""
        from src.db.transactions import insert_transaction
        
        insert_transaction(
            founder_id=founder_id,
            txn_date=None,  # Use today's date
            description=description,
            debit=0,
            credit=credit,
            category=category,
            category_confidence=confidence,
            source=source,
            external_id=external_id,
            raw_event_id=raw_event_id,
        )

    def _check_mrr_milestones(
        self,
        founder_id: str,
        new_amount: float,
    ) -> List[str]:
        """
        Check if payment crosses any MRR milestones.

        Returns:
            List of milestone strings crossed (empty if none)
        """
        from src.db.transactions import get_current_mrr
        
        current_mrr = get_current_mrr(founder_id)
        new_mrr = current_mrr + new_amount
        
        crossed = []
        for milestone in MRR_MILESTONES:
            if current_mrr < milestone <= new_mrr:
                crossed.append(self._format_milestone(milestone))
        
        return crossed

    def _check_concentration_risk(
        self,
        founder_id: str,
        customer_id: str,
        new_amount: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if customer now represents > 30% of 90-day revenue.

        Returns:
            Dict with concentration info if risk detected, None otherwise
        """
        from src.db.transactions import get_90d_revenue_by_customer
        
        total_90d = get_90d_revenue_by_customer(founder_id, customer_id)
        if total_90d == 0:
            return None
        
        customer_share = (total_90d + new_amount) / max(total_90d, 1)
        
        if customer_share > CONCENTRATION_THRESHOLD:
            return {
                "customer_id": customer_id,
                "name": customer_id or "Unknown customer",
                "pct": customer_share,
                "threshold": CONCENTRATION_THRESHOLD,
            }
        
        return None

    def _format_milestone(self, milestone: int) -> str:
        """Format milestone for display."""
        # Convert to int if string
        if isinstance(milestone, str):
            milestone = int(milestone.replace("₹", "").replace(",", "").replace(".", ""))
        
        if milestone >= 1_000_000:
            return f"₹{milestone / 1_000_000:.1f}L MRR"
        elif milestone >= 100_000:
            return f"₹{milestone / 100_000:.1f}L MRR"
        else:
            return f"₹{milestone:,} MRR"

    def _log_to_memory(
        self,
        founder_id: str,
        content: str,
        memory_type: str,
        source: str,
    ) -> None:
        """Log event to Qdrant memory."""
        from src.memory.qdrant_ops import upsert_memory
        
        upsert_memory(
            founder_id=founder_id,
            content=content,
            memory_type=memory_type,
            source=source,
        )


# Self-register on module import
register(RevenueReceivedSOP())
