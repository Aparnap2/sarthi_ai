"""
Customer Success Agent - Sarthi v1.0.

Monitors:
- New user signup (D0 welcome)
- Day 1, D3, D7 onboarding messages
- Churn risk (inactive users)
- Support ticket escalation

Plain English alerts. Personal touch.
"""
from __future__ import annotations
from src.agents.base import BaseAgent, AgentResult
from src.config.llm import get_llm_client, get_chat_model

# Churn risk threshold (70%)
CHURN_RISK_THRESHOLD = 0.7

# Ticket count for escalation
ESCALATION_TICKET_COUNT = 3


class CSAgent(BaseAgent):
    """
    Customer Success agent for user onboarding and retention.

    Monitors:
    - New signup welcome
    - Onboarding milestones (D1, D3, D7)
    - Churn risk (inactive users)
    - Support ticket escalation
    """

    agent_name = "cs_agent"

    def run(self, state: dict, event: dict) -> dict:
        """
        Execute customer success logic.

        Args:
            state: Current state with tenant_id, onboarding_stage, etc.
            event: Triggering event (USER_SIGNED_UP, TIME_TICK_D1, etc.)

        Returns:
            Agent result as dictionary

        Raises:
            AssertionError: If tone validation fails
        """
        etype = event.get("event_type", "")
        result = None
        if etype == "USER_SIGNED_UP":
            result = self._on_signup(state, event)
        elif etype in ("TIME_TICK_D1", "TIME_TICK_D3", "TIME_TICK_D7"):
            result = self._on_time_tick(state, event)
        elif etype == "SUPPORT_TICKET_CREATED":
            result = self._on_support_ticket(state, event)
        elif etype == "USER_LOGGED_IN":
            result = self._on_login(state, event)
        else:
            result = AgentResult(tenant_id=state["tenant_id"], agent_name=self.agent_name)

        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        return result.__dict__

    def _on_signup(self, state: dict, event: dict) -> AgentResult:
        """
        Handle new user signup.

        Args:
            state: Current state
            event: Signup event with customer_name, customer_id

        Returns:
            AgentResult with welcome message
        """
        customer_name = event.get("customer_name", "there")
        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=True,
            urgency="low",
            is_good_news=True,
            headline=f"New signup: {customer_name}. D1 message queued.",
            output_json={"customer_id": event.get("customer_id")},
        )

    def _on_time_tick(self, state: dict, event: dict) -> AgentResult:
        """
        Handle onboarding time tick events (D1, D3, D7).

        Args:
            state: Current state with days_since_last_login, onboarding_stage
            event: Time tick event

        Returns:
            AgentResult with onboarding message or churn risk alert
        """
        last_seen_days = int(state.get("days_since_last_login", 0))
        stage = state.get("onboarding_stage", "WELCOME")
        customer_name = state.get("customer_name", "a user")

        # Calculate churn risk score
        risk_score = min(1.0, last_seen_days / 14.0)

        if risk_score >= CHURN_RISK_THRESHOLD:
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=True,
                urgency="high",
                headline=f"{customer_name} hasn't logged in for {last_seen_days} days. At risk of leaving.",
                do_this=f"Send {customer_name} a personal note today — not a template.",
                output_json={"risk_score": risk_score, "last_seen_days": last_seen_days},
            )

        if stage != "DONE":
            day_label = event.get("event_type", "").replace("TIME_TICK_", "Day ")
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=True,
                urgency="low",
                headline=f"{day_label} message for {customer_name}.",
                output_json={"stage": stage, "risk_score": risk_score},
            )

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"risk_score": risk_score},
        )

    def _on_support_ticket(self, state: dict, event: dict) -> AgentResult:
        """
        Handle support ticket creation.

        Args:
            state: Current state with tickets_last_48h, customer_name
            event: Ticket event with body

        Returns:
            AgentResult with draft reply or escalation alert
        """
        ticket_text = event.get("body", "")
        recent_ticket_count = int(state.get("tickets_last_48h", 1))

        if recent_ticket_count >= ESCALATION_TICKET_COUNT:
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=True,
                urgency="high",
                headline=f"{state.get('customer_name', 'A user')} filed {recent_ticket_count} tickets in 48h.",
                do_this="Jump on a call. This user is frustrated.",
                output_json={"ticket_count": recent_ticket_count},
            )

        draft = self._draft_reply(ticket_text)
        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"ticket_draft": draft},
        )

    def _on_login(self, state: dict, event: dict) -> AgentResult:
        """
        Handle user login event.

        Args:
            state: Current state
            event: Login event

        Returns:
            AgentResult acknowledging login
        """
        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"event": "login_recorded"},
        )

    def _draft_reply(self, ticket_text: str) -> str:
        """
        Generate draft reply for support ticket.

        Args:
            ticket_text: Ticket body text

        Returns:
            Draft reply text
        """
        client = get_llm_client()
        resp = client.chat.completions.create(
            model=get_chat_model(),
            messages=[
                {
                    "role": "system",
                    "content": "Draft a concise, helpful reply to this support ticket. Max 3 sentences. Friendly but direct.",
                },
                {"role": "user", "content": ticket_text},
            ],
            temperature=0.3,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()
