"""Relevance Gate for Sarthi V3.0 Session Layer.

This module provides keyword-based routing to determine which domain
agents should respond to user queries.

PRD Reference: Sections 226-237

Architecture:
- Pure Python keyword matching (NO LLM)
- Domain keywords mapped to Finance, Ops, BI
- Agent responds ONLY if:
  1. keyword_hit OR
  2. (active_alert AND question)
"""

import logging
import re
from typing import List, Optional, Set

from src.session.mission_state import MissionState

logger = logging.getLogger(__name__)

# Domain keyword mappings per PRD Section 226-237
DOMAIN_KEYWORDS = {
    "finance": [
        "burn",
        "runway",
        "revenue",
        "mrr",
        "budget",
        "cost",
        "raise",
        "invest",
        "expense",
        "profit",
        "loss",
        "cash",
        "financial",
        "finance",
        "funding",
        "valuation",
        "cap table",
        "dilution",
    ],
    "ops": [
        "support",
        "ticket",
        "bug",
        "error",
        "churn",
        "usage",
        "feature",
        "feedback",
        "issue",
        "problem",
        "complaint",
        "downtime",
        "performance",
        "latency",
        "scaling",
        "deployment",
    ],
    "bi": [
        "metric",
        "dau",
        "mau",
        "retention",
        "cohort",
        "growth",
        "data",
        "dashboard",
        "analytics",
        "report",
        "insight",
        "trend",
        "benchmark",
        "kpi",
        "conversion",
        "engagement",
    ],
}

# Keywords that indicate a question
QUESTION_INDICATORS = {
    "what",
    "how",
    "why",
    "when",
    "where",
    "who",
    "which",
    "can",
    "could",
    "should",
    "would",
    "will",
    "do",
    "does",
    "is",
    "are",
    "was",
    "were",
    "tell",
    "show",
    "explain",
    "help",
}


class RelevanceGate:
    """Relevance Gate for determining agent responsiveness.

    This class implements the keyword-based routing logic from PRD Section 226-237.
    """

    def __init__(self, tenant_id: str):
        """Initialize the relevance gate for a tenant.

        Args:
            tenant_id: The tenant identifier
        """
        self.tenant_id = tenant_id
        self._mission_state = None

    @property
    def mission_state(self) -> Optional[dict]:
        """Lazy-load mission state."""
        if self._mission_state is None:
            state = get_mission_state(self.tenant_id)
            self._mission_state = state.to_dict() if state else {}
        return self._mission_state

    def _normalize_text(self, text: str) -> str:
        """Normalize text for keyword matching.

        Args:
            text: Input text

        Returns:
            Lowercase text with punctuation removed
        """
        return re.sub(r"[^\w\s]", " ", text.lower())

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract keywords from text.

        Args:
            text: Input text

        Returns:
            Set of lowercase keywords
        """
        normalized = self._normalize_text(text)
        return set(normalized.split())

    def _is_question(self, text: str) -> bool:
        """Determine if the text is a question.

        Args:
            text: Input text

        Returns:
            True if the text appears to be a question
        """
        normalized = self._normalize_text(text)
        words = normalized.split()

        # Check for question indicators at the start
        if words and words[0] in QUESTION_INDICATORS:
            return True

        # Check for question mark
        if "?" in text:
            return True

        return False

    def match_domains(self, text: str) -> List[str]:
        """Match text against domain keywords.

        Args:
            text: User input text

        Returns:
            List of matching domain names (finance, ops, bi)
        """
        keywords = self._extract_keywords(text)
        matched_domains = []

        for domain, domain_keywords in DOMAIN_KEYWORDS.items():
            # Check if any keyword is in the text
            for keyword in domain_keywords:
                if keyword in keywords:
                    matched_domains.append(domain)
                    break

        logger.debug(
            f"Matched domains for tenant {self.tenant_id}: {matched_domains}"
        )
        return matched_domains

    def has_active_alerts(self) -> bool:
        """Check if there are active alerts for the tenant.

        Returns:
            True if there are active alerts
        """
        alerts = self.mission_state.get("active_alerts", [])
        return bool(alerts and len(alerts) > 0)
    
    def has_active_alerts_with_state(self, mission_state) -> bool:
        """Check if mission_state has active alerts."""
        if not mission_state:
            return False
        return bool(mission_state.active_alerts and len(mission_state.active_alerts) > 0)

    def should_respond(self, text: str) -> bool:
        """Determine if the agent should respond to the input.

        Per PRD Section 226-237:
        - Agent responds if keyword_hit OR
        - Agent responds if (active_alert AND question)

        Args:
            text: User input text

        Returns:
            True if the agent should respond
        """
        # Check keyword match
        matched_domains = self.match_domains(text)
        keyword_hit = len(matched_domains) > 0

        # Check active alert + question condition
        is_question = self._is_question(text)
        active_alerts = self.has_active_alerts()
        alert_trigger = active_alerts and is_question

        should_respond = keyword_hit or alert_trigger

        logger.info(
            f"Relevance gate decision for tenant {self.tenant_id}: "
            f"keyword_hit={keyword_hit}, domains={matched_domains}, "
            f"alert_trigger={alert_trigger}, is_question={is_question}, "
            f"active_alerts={active_alerts}, should_respond={should_respond}"
        )

        return should_respond


def should_respond(tenant_id: str, text: str) -> bool:
    """Convenience function to check if agent should respond.

    Args:
        tenant_id: The tenant identifier
        text: User input text

    Returns:
        True if the agent should respond
    """
    gate = RelevanceGate(tenant_id)
    return gate.should_respond(text)


def get_relevant_domains(tenant_id: str, text: str) -> List[str]:
    """Get relevant domains for the input text.

    Args:
        tenant_id: The tenant identifier
        text: User input text

    Returns:
        List of relevant domain names
    """
    gate = RelevanceGate(tenant_id)
    return gate.match_domains(text)


def relevance_gate(text: str, mission_state=None) -> List[str]:
    """Convenience function for relevance gate.
    
    Per PRD Section 226-237:
    - Agent responds ONLY if keyword_hit OR
    - Agent responds if (active_alert AND question)
    
    Args:
        text: User input text
        mission_state: Optional MissionState for active alert check
        
    Returns:
        List of relevant domain names
    """
    if not text:
        return []
    
    # Create a gate for matching
    tenant_id = mission_state.tenant_id if mission_state else "default"
    gate = RelevanceGate(tenant_id)
    
    # Match domains
    domains = gate.match_domains(text)
    
    # Check active alerts condition if mission provided
    if mission_state and not domains:
        # Check if there's a question + active alert
        if gate._is_question(text) and gate.has_active_alerts_with_state(mission_state):
            # Return domain based on active alerts
            if mission_state.burn_alert:
                return ["finance"]
            if mission_state.error_spike:
                return ["ops"]
            if mission_state.churn_rate and mission_state.churn_rate > 0.03:
                return ["bi"]
    
    return domains