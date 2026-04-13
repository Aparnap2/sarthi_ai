"""HITL tests — pure Python, zero infra."""
import pytest
from src.hitl.manager import HITLManager
from src.hitl.confidence import score_confidence


class TestHITLRouting:
    def test_tier1_auto_send(self):
        m = HITLManager()
        assert m.route("info", 0.90) == "auto"

    def test_tier2_review_warning(self):
        m = HITLManager()
        assert m.route("warning", 0.70) == "review"

    def test_tier2_review_low_confidence(self):
        m = HITLManager()
        assert m.route("info", 0.70) == "review"

    def test_tier3_approve_critical_low_confidence(self):
        m = HITLManager()
        assert m.route("critical", 0.50) == "approve"

    def test_tier3_always_approve_for_investor_update(self):
        m = HITLManager()
        assert m.route("info", 0.99, is_investor_update=True) == "approve"

    def test_default_review_for_edge_cases(self):
        m = HITLManager()
        # critical but high conf → review
        assert m.route("critical", 0.90) == "review"


class TestConfidenceScoring:
    def test_base_confidence(self):
        assert score_confidence() == 0.5

    def test_seen_before_increases(self):
        assert score_confidence(pattern_seen_before=True) > 0.5

    def test_high_data_quality_increases(self):
        assert score_confidence(data_quality=1.0) > 0.5

    def test_high_volatility_decreases(self):
        assert score_confidence(metric_volatility=1.0) < 0.5

    def test_confidence_bounded_0_to_1(self):
        assert (
            0.0
            <= score_confidence(data_quality=0, metric_volatility=1.0, historical_accuracy=0)
            <= 1.0
        )
        assert (
            0.0
            <= score_confidence(
                data_quality=1.0, pattern_seen_before=True, historical_accuracy=1.0
            )
            <= 1.0
        )
