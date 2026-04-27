"""Router: Co-founder message routing.

Routes messages to Employee Agents based on relevance gate and MissionState.
PRD Reference: Section 220-224, Option C authority.
"""
from dataclasses import dataclass
from typing import Optional

from src.session.mission_state import MissionState
from src.session.relevance_gate import relevance_gate
from src.schemas.guardian import AlertDecision


@dataclass
class RouteDecision:
    destination: str  # "finance" | "bi" | "ops" | "none"
    reason: str
    should_escalate: bool


class Router:
    """Co-founder router for message dispatch."""
    
    def __init__(self):
        pass
    
    def route(
        self,
        message: str,
        mission_state: Optional[MissionState] = None,
    ) -> RouteDecision:
        """Route message to appropriate employee agent.
        
        Args:
            message: User message text
            mission_state: Current MissionState
            
        Returns:
            RouteDecision with destination and reason
        """
        # Step 1: Run relevance gate (pure Python)
        relevant_domains = relevance_gate(message, mission_state)
        
        if not relevant_domains:
            return RouteDecision(
                destination="none",
                reason="No domain keywords triggered",
                should_escalate=False,
            )
        
        # Step 2: Check for escalation criteria
        should_escalate = self._should_escalate(message, mission_state)
        
        if should_escalate:
            return RouteDecision(
                destination="escalate",
                reason="Critical signal or low confidence - requires founder decision",
                should_escalate=True,
            )
        
        # Step 3: Primary domain routing (deterministic)
        primary = relevant_domains[0]
        
        return RouteDecision(
            destination=primary,
            reason=f"Keyword match: {primary}",
            should_escalate=False,
        )
    
    def _should_escalate(
        self,
        message: str,
        mission_state: Optional[MissionState],
    ) -> bool:
        """Determine if message requires escalation.
        
        Per PRD Option C:
        - Critical signals
        - Confidence < 0.60
        - Investor update drafts (always requires approval)
        """
        if mission_state is None:
            return False
        
        # Check for critical signals
        if mission_state.burn_alert:
            if mission_state.burn_severity == "critical":
                return True
        
        # Check for investor-related keywords
        investor_keywords = ["investor", "update", "brief", "quarterly", "fundraising"]
        message_lower = message.lower()
        for kw in investor_keywords:
            if kw in message_lower:
                return True
        
        return False


def route_message(
    message: str,
    mission_state: Optional[MissionState] = None,
) -> RouteDecision:
    """Convenience function for routing."""
    router = Router()
    return router.route(message, mission_state)