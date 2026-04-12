"""Guardian Detector — runs all 16 watchlist patterns against signals."""
from __future__ import annotations
from typing import Any
from src.guardian.watchlist import SEED_STAGE_WATCHLIST, SeedStageBlindspot


class GuardianDetector:
    """Runs all watchlist detection logic against a signal dict.

    Returns list of matched blindspots. Empty list = no anomalies.
    """

    def run(self, signals: dict[str, Any]) -> list[SeedStageBlindspot]:
        matched = []
        for item in SEED_STAGE_WATCHLIST:
            try:
                if item.detection_logic(signals):
                    matched.append(item)
            except Exception:
                # Individual detection failure → skip, don't crash
                continue
        return matched

    def run_by_domain(
        self, signals: dict[str, Any], domain: str
    ) -> list[SeedStageBlindspot]:
        """Run only detections for a specific domain (finance/bi/ops)."""
        return [
            item for item in self.run(signals)
            if item.domain == domain
        ]
