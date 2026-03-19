"""
People Coordinator Agent - Sarthi v1.0.

Manages:
- New hire onboarding checklists (by role)
- Offboarding revocation lists
- Checklist completion tracking
- Daily nag for incomplete items

Plain English alerts. Actionable checklists.
"""
from __future__ import annotations
from src.agents.base import BaseAgent, AgentResult

# Onboarding checklists by role function
CHECKLISTS_BY_ROLE = {
    "eng": ["slack", "notion", "github", "gworkspace", "linear"],
    "ops": ["slack", "notion", "gworkspace"],
    "sales": ["slack", "notion", "gworkspace", "crm"],
    "design": ["slack", "notion", "gworkspace", "figma"],
    "default": ["slack", "notion", "gworkspace"],
}

# Offboarding revocation lists by role function
REVOKE_LIST_BY_ROLE = {
    "eng": ["github", "linear", "notion", "slack", "gworkspace", "aws"],
    "ops": ["notion", "slack", "gworkspace"],
    "sales": ["crm", "notion", "slack", "gworkspace"],
    "default": ["slack", "notion", "gworkspace"],
}


class PeopleCoordinatorAgent(BaseAgent):
    """
    People coordination agent for employee lifecycle management.

    Manages:
    - New hire onboarding checklists
    - Offboarding access revocation
    - Checklist completion tracking
    """

    agent_name = "people_coordinator"

    def run(self, state: dict, event: dict) -> dict:
        """
        Execute people coordination logic.

        Args:
            state: Current state with tenant_id, checklist, etc.
            event: Triggering event (EMPLOYEE_CREATED, TIME_TICK_D1, etc.)

        Returns:
            Agent result as dictionary

        Raises:
            AssertionError: If tone validation fails
        """
        etype = event.get("event_type", "")
        if etype == "EMPLOYEE_CREATED":
            result = self._on_hire(state, event)
        elif etype == "EMPLOYEE_TERMINATED":
            result = self._on_offboard(state, event)
        elif etype == "CHECKLIST_ITEM_CONFIRMED":
            result = self._on_confirmed(state, event)
        elif etype in ("TIME_TICK_D1", "TIME_TICK_D3"):
            result = self._nag_loop(state, event)
        else:
            result = AgentResult(tenant_id=state["tenant_id"], agent_name=self.agent_name)

        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        return result.__dict__

    def _on_hire(self, state: dict, event: dict) -> AgentResult:
        """
        Handle new hire event.

        Args:
            state: Current state
            event: Employee created event with name, role_function

        Returns:
            AgentResult with onboarding checklist
        """
        name = event.get("name", "New hire")
        role = event.get("role_function", "default").lower()
        items = CHECKLISTS_BY_ROLE.get(role, CHECKLISTS_BY_ROLE["default"])
        checklist = {item: False for item in items}
        items_str = ", ".join(f"[{i.upper()}]" for i in items)

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=True,
            urgency="low",
            is_good_news=True,
            headline=f"{name} joins. Provision: {items_str}",
            do_this="Tap each item when done. Sarthi tracks what's missing.",
            output_json={"checklist": checklist, "role": role},
        )

    def _on_offboard(self, state: dict, event: dict) -> AgentResult:
        """
        Handle employee termination event.

        Args:
            state: Current state
            event: Employee terminated event with name, role_function

        Returns:
            AgentResult with revocation list
        """
        name = event.get("name", "Employee")
        role = event.get("role_function", "default").lower()
        items = REVOKE_LIST_BY_ROLE.get(role, REVOKE_LIST_BY_ROLE["default"])
        items_str = ", ".join(items)

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=True,
            urgency="high",
            headline=f"Offboard {name} today. Revoke: {items_str}.",
            do_this="Confirm each revocation. Reply 'done' when complete.",
            output_json={"revoke_list": items},
        )

    def _nag_loop(self, state: dict, event: dict) -> AgentResult:
        """
        Handle daily nag for incomplete checklist items.

        Args:
            state: Current state with checklist, employee_name
            event: Time tick event

        Returns:
            AgentResult with pending items alert
        """
        checklist = state.get("checklist", {})
        pending = [k for k, v in checklist.items() if not v]
        name = state.get("employee_name", "new hire")

        if not pending:
            return AgentResult(
                tenant_id=state["tenant_id"],
                agent_name=self.agent_name,
                fire_telegram=False,
                output_json={"checklist_complete": True},
            )

        items_str = ", ".join(pending)
        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=True,
            urgency="warn",
            headline=f"{name}'s setup still missing: {items_str}.",
            do_this=f"Complete {pending[0]} first — takes 2 minutes.",
            output_json={"pending_items": pending},
        )

    def _on_confirmed(self, state: dict, event: dict) -> AgentResult:
        """
        Handle checklist item confirmation.

        Args:
            state: Current state with checklist
            event: Item confirmed event with item name

        Returns:
            AgentResult with updated checklist
        """
        item = event.get("item", "")
        checklist = state.get("checklist", {})
        if item in checklist:
            checklist[item] = True

        return AgentResult(
            tenant_id=state["tenant_id"],
            agent_name=self.agent_name,
            fire_telegram=False,
            output_json={"checklist": checklist},
        )
