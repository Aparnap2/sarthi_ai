"""Session Layer for Sarthi V3.0.

This module provides session management capabilities including:
- Mission state tracking (finance, BI, ops, cross-functional metrics)
- Session context retrieval (recent messages)
- Relevance gating (keyword-based routing)

PRD Reference: Sections 508-532, 795-798
"""

from src.session.mission_state import (
    MissionState,
    get_mission_state,
    save_mission_state,
)
from src.session.context import get_session_context
from src.session.relevance_gate import RelevanceGate, should_respond

__all__ = [
    "MissionState",
    "get_mission_state",
    "save_mission_state",
    "get_session_context",
    "RelevanceGate",
    "should_respond",
]