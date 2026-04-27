"""Reflector: ACE Reflector for founder response scoring.

Converts founder responses into confidence scores for playbook updates.
PRD Reference: Section 249-257
"""
from dataclasses import dataclass
from enum import Enum


class ResponseType(Enum):
    """Founder response types."""
    ACKNOWLEDGED = "acknowledged"
    ACTED_ON = "acted_on"
    IGNORED = "ignored"
    DISPUTED = "disputed"
    DISMISSED = "dismissed"


# Score weights per PRD Section 252
RESPONSE_SCORES = {
    ResponseType.ACKNOWLEDGED: 1.0,
    ResponseType.ACTED_ON: 1.5,
    ResponseType.IGNORED: -0.5,
    ResponseType.DISPUTED: -1.0,
    ResponseType.DISMISSED: -1.5,
}


@dataclass
class Reflection:
    response_type: ResponseType
    score: float
    domain: str  # "finance" | "bi" | "ops"


class Reflector:
    """ACE Reflector: converts founder response to score."""
    
    def __init__(self):
        pass
    
    def score(self, response: str, domain: str) -> Reflection:
        """Score founder response.
        
        Args:
            response: Founder's response text or action
            domain: Domain (finance/bi/ops)
            
        Returns:
            Reflection with score
        """
        # Determine response type from text
        response_lower = response.lower()
        
        # Check action keywords
        if "dismiss" in response_lower or "ignore" in response_lower:
            return self._build_reflection(ResponseType.DISMISSED, domain)
        
        if "disagree" in response_lower or "wrong" in response_lower:
            return self._build_reflection(ResponseType.DISPUTED, domain)
        
        if "doing" in response_lower or "done" in response_lower:
            return self._build_reflection(ResponseType.ACTED_ON, domain)
        
        if "ok" in response_lower or "thanks" in response_lower:
            return self._build_reflection(ResponseType.ACKNOWLEDGED, domain)
        
        # Default: assumed acknowledged after timeout
        return self._build_reflection(ResponseType.IGNORED, domain)
    
    def _build_reflection(self, response_type: ResponseType, domain: str) -> Reflection:
        return Reflection(
            response_type=response_type,
            score=RESPONSE_SCORES[response_type],
            domain=domain,
        )


def score_founder_response(response: str, domain: str) -> Reflection:
    """Convenience function for scoring."""
    reflector = Reflector()
    return reflector.score(response, domain)