"""
SOP: Weekly Briefing — Monday 9am founder briefing.

Triggered by Temporal cron every Monday 9am IST.
Collects from all desks, scores, ranks, max 5 items.
Always includes at least one positive item if exists.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from src.sops.base import BaseSOP, SOPResult, BANNED_JARGON
from src.sops.registry import register


# Max items in weekly briefing (founder attention limit)
MAX_BRIEFING_ITEMS = 5

# Urgency thresholds
URGENCY_HIGH = 8
URGENCY_MEDIUM = 5
URGENCY_LOW = 1


class WeeklyBriefingSOP(BaseSOP):
    """
    SOP for weekly founder briefing.

    Triggers:
    - Temporal cron (Monday 9am IST)

    Behavior:
    - Collects from all 6 desks (Finance, People, Legal, Intelligence, IT, Admin)
    - Scores and ranks by urgency + founder impact
    - Trims to max 5 items
    - Ensures at least one positive item if exists
    - Applies ToneFilter to every item
    - Sends via Telegram (or queues for HITL)
    """
    sop_name = "SOP_WEEKLY_BRIEFING"

    async def execute(self, payload_ref: str, founder_id: str) -> SOPResult:
        """
        Execute SOP_WEEKLY_BRIEFING.

        Args:
            payload_ref: Reference to cron trigger (not used)
            founder_id: Founder who receives briefing

        Returns:
            SOPResult with briefing items
        """
        # 1. Collect from all desks (parallel)
        all_items = await self._collect_from_all_desks(founder_id)
        
        # 2. Score and rank by urgency + impact
        ranked = self._score_and_rank(all_items)
        
        # 3. Trim to max 5 items
        trimmed = ranked[:MAX_BRIEFING_ITEMS]
        
        # 4. Ensure at least one positive item if exists
        has_positive = any(item.get("is_good_news") for item in trimmed)
        if not has_positive:
            positive = await self._find_positive(founder_id)
            if positive:
                # Replace lowest urgency item with positive
                if len(trimmed) > 0:
                    trimmed[-1] = positive
                else:
                    trimmed.append(positive)
        
        # 5. Apply ToneFilter to every item
        filtered = [self._apply_tone_filter(item) for item in trimmed]
        
        # 6. Compose briefing message
        headline = f"Good morning. Here's your week."
        do_this = self._compose_actions(filtered)
        
        # 7. Log to memory
        self._log_to_memory(
            founder_id=founder_id,
            content=f"Weekly briefing: {len(filtered)} items",
            memory_type="weekly_briefing",
            source="cron",
        )
        
        return SOPResult(
            sop_name=self.sop_name,
            founder_id=founder_id,
            success=True,
            fire_alert=False,  # Informational, not an alert
            hitl_risk="low",
            headline=headline,
            do_this=do_this,
            is_good_news=any(item.get("is_good_news") for item in filtered),
            output={
                "items": filtered,
                "item_count": len(filtered),
            },
        )

    async def _collect_from_all_desks(self, founder_id: str) -> List[Dict[str, Any]]:
        """Collect items from all 6 desks."""
        all_items = []
        
        # Finance Desk (CFO + Bookkeeper)
        finance_items = await self._collect_finance(founder_id)
        all_items.extend(finance_items)
        
        # AR/AP Desk
        ar_ap_items = await self._collect_ar_ap(founder_id)
        all_items.extend(ar_ap_items)
        
        # Compliance Desk
        compliance_items = await self._collect_compliance(founder_id)
        all_items.extend(compliance_items)
        
        # Contracts Desk
        contracts_items = await self._collect_contracts(founder_id)
        all_items.extend(contracts_items)
        
        # HR Desk
        hr_items = await self._collect_hr(founder_id)
        all_items.extend(hr_items)
        
        # IT Desk
        it_items = await self._collect_it(founder_id)
        all_items.extend(it_items)
        
        # Policy/Intelligence Desk
        policy_items = await self._collect_policy(founder_id)
        all_items.extend(policy_items)
        
        return all_items

    async def _collect_finance(self, founder_id: str) -> List[Dict[str, Any]]:
        """Collect finance data from CFO desk."""
        from src.db.forecast import get_runway_days, get_monthly_burn
        
        runway = await get_runway_days(founder_id)
        burn = await get_monthly_burn(founder_id)
        
        items = []
        
        # Runway alert
        if runway < 90:
            items.append({
                "headline": f"Runway: {runway} days ({round(runway/30, 1)} months)",
                "urgency": URGENCY_HIGH if runway < 60 else URGENCY_MEDIUM,
                "hitl_risk": "high" if runway < 60 else "medium",
                "is_good_news": False,
                "do_this": "Review burn rate.",
            })
        
        # Burn spike
        if burn > 200000:  # ₹2L+ monthly burn
            items.append({
                "headline": f"Monthly burn: ₹{burn:,.0f}",
                "urgency": URGENCY_MEDIUM,
                "hitl_risk": "medium",
                "is_good_news": False,
                "do_this": "Review expenses.",
            })
        
        return items

    async def _collect_ar_ap(self, founder_id: str) -> List[Dict[str, Any]]:
        """Collect AR/AP data."""
        from src.db.transactions import get_overdue_invoices
        
        overdue = await get_overdue_invoices(founder_id)
        
        items = []
        
        if overdue:
            total = sum(inv["amount"] for inv in overdue)
            items.append({
                "headline": f"{len(overdue)} invoices overdue (₹{total:,.0f})",
                "urgency": URGENCY_HIGH if total > 100000 else URGENCY_MEDIUM,
                "hitl_risk": "medium",
                "is_good_news": False,
                "do_this": "Send reminders.",
            })
        
        return items

    async def _collect_compliance(self, founder_id: str) -> List[Dict[str, Any]]:
        """Collect compliance deadlines."""
        from src.db.compliance import get_upcoming_deadlines
        
        deadlines = await get_upcoming_deadlines(founder_id, days_ahead=14)
        
        items = []
        
        for deadline in deadlines:
            days_remaining = (deadline["due_date"] - deadline["today"]).days
            items.append({
                "headline": f"{deadline['filing_type']} due in {days_remaining} days",
                "urgency": URGENCY_HIGH if days_remaining <= 7 else URGENCY_MEDIUM,
                "hitl_risk": "high" if days_remaining <= 7 else "medium",
                "is_good_news": False,
                "do_this": "Review filing data.",
            })
        
        return items

    async def _collect_contracts(self, founder_id: str) -> List[Dict[str, Any]]:
        """Collect contract expiry/expiry alerts."""
        from src.db.contracts import get_expiring_contracts
        
        expiring = await get_expiring_contracts(founder_id, days_ahead=30)
        
        items = []
        
        for contract in expiring:
            days_remaining = (contract["expiry_date"] - contract["today"]).days
            items.append({
                "headline": f"Contract '{contract['name']}' expires in {days_remaining} days",
                "urgency": URGENCY_MEDIUM,
                "hitl_risk": "medium",
                "is_good_news": False,
                "do_this": "Review renewal.",
            })
        
        return items

    async def _collect_hr(self, founder_id: str) -> List[Dict[str, Any]]:
        """Collect HR milestones."""
        from src.db.people import get_upcoming_milestones
        
        milestones = await get_upcoming_milestones(founder_id, days_ahead=7)
        
        items = []
        
        for milestone in milestones:
            items.append({
                "headline": f"{milestone['type']}: {milestone['employee_name']}",
                "urgency": URGENCY_LOW,
                "hitl_risk": "low",
                "is_good_news": milestone.get("is_positive", False),
                "do_this": "Add to calendar.",
            })
        
        return items

    async def _collect_it(self, founder_id: str) -> List[Dict[str, Any]]:
        """Collect IT/SaaS alerts."""
        from src.db.saas import get_unused_tools, get_cloud_spend_delta
        
        unused = await get_unused_tools(founder_id, days_unused=60)
        cloud_delta = await get_cloud_spend_delta(founder_id)
        
        items = []
        
        if unused:
            savings = sum(tool["monthly_cost"] for tool in unused)
            items.append({
                "headline": f"{len(unused)} SaaS tools unused (save ₹{savings:,}/mo)",
                "urgency": URGENCY_LOW,
                "hitl_risk": "low",
                "is_good_news": True,  # Saving opportunity
                "do_this": "Review cancellations.",
            })
        
        if cloud_delta and cloud_delta > 0.3:  # > 30% increase
            items.append({
                "headline": f"Cloud spend up {int(cloud_delta * 100)}% this month",
                "urgency": URGENCY_MEDIUM,
                "hitl_risk": "medium",
                "is_good_news": False,
                "do_this": "Review cloud costs.",
            })
        
        return items

    async def _collect_policy(self, founder_id: str) -> List[Dict[str, Any]]:
        """Collect policy/regulatory alerts."""
        from src.db.policy import get_recent_alerts
        
        alerts = await get_recent_alerts(founder_id, days_back=7)
        
        items = []
        
        for alert in alerts:
            items.append({
                "headline": alert["title"],
                "urgency": URGENCY_MEDIUM if alert.get("actionable") else URGENCY_LOW,
                "hitl_risk": "medium" if alert.get("actionable") else "low",
                "is_good_news": alert.get("is_opportunity", False),
                "do_this": alert.get("action", "Review details."),
            })
        
        return items

    def _score_and_rank(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score and rank items by urgency + founder impact."""
        # Sort by urgency (highest first)
        return sorted(items, key=lambda x: x.get("urgency", 0), reverse=True)

    async def _find_positive(self, founder_id: str) -> Optional[Dict[str, Any]]:
        """Find at least one positive item if exists."""
        from src.db.transactions import get_recent_milestones
        
        milestones = await get_recent_milestones(founder_id, days_back=7)
        
        if milestones:
            return {
                "headline": f"Milestone: {milestones[0]['description']} 🎉",
                "urgency": URGENCY_LOW,
                "hitl_risk": "low",
                "is_good_news": True,
                "do_this": "Celebrate!",
            }
        
        return None

    def _apply_tone_filter(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Apply ToneFilter to remove jargon from item."""
        headline = item.get("headline", "")
        do_this = item.get("do_this", "")
        
        # Replace jargon with plain language (case-insensitive)
        headline_lower = headline.lower()
        do_this_lower = do_this.lower()
        
        for term in BANNED_JARGON:
            term_lower = term.lower()
            headline_lower = headline_lower.replace(term_lower, "")
            do_this_lower = do_this_lower.replace(term_lower, "")
        
        # Clean up extra spaces
        item["headline"] = " ".join(headline_lower.split())
        item["do_this"] = " ".join(do_this_lower.split())
        
        return item

    def _compose_actions(self, items: List[Dict[str, Any]]) -> str:
        """Compose do_this from items with actions."""
        actions = [item.get("do_this") for item in items if item.get("do_this")]
        
        if not actions:
            return ""
        
        # Return first action (most urgent)
        return actions[0]

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
register(WeeklyBriefingSOP())
