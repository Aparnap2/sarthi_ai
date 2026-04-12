"""HITL Manager — 3-tier human-in-the-loop routing.

Tier 1 — AUTO: severity=info, confidence>0.85, seen before
Tier 2 — SLACK REVIEW: severity=warning, confidence 0.60-0.85, or new pattern
Tier 3 — HUMAN OVERRIDE: severity=critical, confidence<0.60, or investor update
"""
from __future__ import annotations


class HITLManager:
    def route(self, severity: str, confidence: float,
              is_new_pattern: bool = False,
              is_investor_update: bool = False) -> str:
        if is_investor_update:
            return "approve"
        if severity == "critical" and confidence < 0.60:
            return "approve"
        if severity == "warning" or (0.60 <= confidence < 0.85):
            return "review"
        if severity == "info" and confidence > 0.85:
            return "auto"
        return "review"
