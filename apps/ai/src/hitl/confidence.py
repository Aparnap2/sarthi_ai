"""Confidence scoring per alert."""
from __future__ import annotations


def score_confidence(
    pattern_seen_before: bool = False,
    data_quality: float = 0.0,
    metric_volatility: float = 0.0,
    historical_accuracy: float = 0.5,
) -> float:
    """Compute a confidence score in [0.0, 1.0].

    Base confidence is 0.5, adjusted by:
    - +0.15 if pattern was seen before
    - +0.15 * data_quality
    - -0.10 * metric_volatility
    - +0.20 * (historical_accuracy - 0.5)
    """
    base = 0.5
    if pattern_seen_before:
        base += 0.15
    base += data_quality * 0.15
    base -= metric_volatility * 0.1
    base += (historical_accuracy - 0.5) * 0.2
    return max(0.0, min(1.0, base))
