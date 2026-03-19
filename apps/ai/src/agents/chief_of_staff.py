"""
Chief of Staff Agent - Sarthi v1.0.

Aggregates:
- Weekly briefing from all agent outputs
- Monthly investor update draft
- Cross-agent signal synthesis

Plain English summaries. Max 5 items. Always includes one positive.
"""
from __future__ import annotations
from src.agents.base import BaseAgent, AgentResult
from src.config.llm import get_llm_client, get_chat_model

# Maximum briefing items
MAX_BRIEFING_ITEMS = 5

# Urgency ranking (lower = more urgent)
URGENCY_RANK = {"critical": 0, "high": 1, "warn": 2, "low": 3}


class ChiefOfStaffAgent(BaseAgent):
    """
    Chief of Staff agent for executive synthesis.

    Aggregates:
    - Weekly briefings from all agents
    - Monthly investor updates
    - Cross-agent signal prioritization
    """

    agent_name = "chief_of_staff"

    def run(self, state: dict, event: dict) -> dict:
        """
        Execute chief of staff logic.

        Args:
            state: Current state with tenant_id, agent_outputs, metrics
            event: Triggering event (TIME_TICK_WEEKLY, TIME_TICK_MONTHLY, etc.)

        Returns:
            Agent result as dictionary

        Raises:
            AssertionError: If tone validation fails
        """
        etype = event.get("event_type", "")
        if etype == "TIME_TICK_WEEKLY":
            result = self._compose_weekly_briefing(state)
        elif etype == "TIME_TICK_MONTHLY":
            result = self._compose_investor_draft(state)
        elif etype == "AGENT_OUTPUT":
            result = self._ingest_agent_output(state, event)
        else:
            result = AgentResult(tenant_id=state["tenant_id"], agent_name=self.agent_name)

        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        result.qdrant_point_id = self._write_qdrant_memory(
            state["tenant_id"],
            f"Briefing: {result.headline}",
            "briefing",
        )
        return result.__dict__

    def _compose_weekly_briefing(self, state: dict) -> AgentResult:
        """
        Compose weekly briefing from agent outputs.

        Args:
            state: Current state with agent_outputs list

        Returns:
            AgentResult with synthesized briefing
        """
        outputs = state.get("agent_outputs", [])

        if not outputs:
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=True,
                urgency="low",
                headline="Quiet week. Everything is running.",
                output_json={"item_count": 0},
            )

        # Sort by urgency and take top MAX_BRIEFING_ITEMS
        sorted_outputs = sorted(
            outputs, key=lambda x: URGENCY_RANK.get(x.get("urgency", "low"), 3)
        )[:MAX_BRIEFING_ITEMS]

        # Ensure at least one positive item
        has_positive = any(o.get("is_good_news") for o in sorted_outputs)
        if not has_positive:
            positive = self._find_positive(state["tenant_id"])
            if positive and len(sorted_outputs) >= MAX_BRIEFING_ITEMS:
                sorted_outputs[-1] = positive
            elif positive:
                sorted_outputs.append(positive)

        # Compose briefing with LLM
        briefing_text = self._compose_with_llm(sorted_outputs)

        # Determine overall urgency
        has_critical = any(o.get("urgency") in ("critical", "high") for o in sorted_outputs)

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=True,
            urgency="high" if has_critical else "low",
            headline=briefing_text,
            output_json={"item_count": len(sorted_outputs), "items": sorted_outputs},
        )

    def _compose_with_llm(self, items: list[dict]) -> str:
        """
        Use LLM to compose briefing from items.

        Args:
            items: List of agent output items

        Returns:
            Formatted briefing text
        """
        client = get_llm_client()
        items_text = "\n".join(
            f"- [{i.get('urgency', 'low').upper()}] {i.get('headline', '')}"
            for i in items
        )

        resp = client.chat.completions.create(
            model=get_chat_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write Monday morning briefings for startup founders. "
                        "Rules: max 5 bullets, plain English, no jargon, no fluff. "
                        "BANNED words: leverage, synergy, optimize, streamline, empower, facilitate, utilize, implement, strategic, tactical, operational, bandwidth, capacity, throughput, latency, overhead, bottleneck, pipeline, funnel, conversion, engagement, retention, cohort, segment, journey, touchpoint, stakeholder, deliverable, milestone, roadmap, backlog, sprint, iteration, agile, devops, infrastructure, architecture, framework, platform, solution, capability, functionality, disrupt, ecosystem, holistic, scalable, robust, seamless, cutting-edge, best-in-class, game-changer, mission-critical, actionable, granular, proactive, reactive, incentivize. "
                        "Each bullet: one sentence + one action in brackets. "
                        "Start with most urgent. End with something positive if present."
                    ),
                },
                {"role": "user", "content": f"This week's signals:\n{items_text}"},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()

    def _compose_investor_draft(self, state: dict) -> AgentResult:
        """
        Compose monthly investor update draft.

        Args:
            state: Current state with revenue, burn, runway metrics

        Returns:
            AgentResult with investor update draft
        """
        revenue = state.get("monthly_revenue", 0)
        burn = state.get("burn_rate", 0)
        runway = state.get("runway_months", 0)
        mrr = state.get("last_30d_mrr", 0)

        draft = (
            f"**Month in Numbers**\n"
            f"Revenue: ₹{revenue:,.0f} | MRR: ₹{mrr:,.0f}\n"
            f"Burn: ₹{burn:,.0f}/month | Runway: {runway:.1f} months\n\n"
            f"**What we shipped**: [fill in]\n"
            f"**What we learned**: [fill in]\n"
            f"**What we need**: [fill in]"
        )

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=True,
            urgency="low",
            headline="Investor update draft ready. [Review] [Send]",
            output_json={
                "draft": draft,
                "revenue": revenue,
                "burn": burn,
                "runway": runway,
            },
        )

    def _find_positive(self, tenant_id: str) -> dict | None:
        """
        Find a positive item to include in briefing.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Positive item dict or None
        """
        # Placeholder - would query DB in production
        return None

    def _ingest_agent_output(self, state: dict, event: dict) -> AgentResult:
        """
        Ingest agent output for later synthesis.

        Args:
            state: Current state
            event: Agent output event

        Returns:
            AgentResult acknowledging ingestion
        """
        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"ingested": True},
        )
