"""Security tests for Python type safety and validation."""

import pytest
from pydantic import ValidationError, BaseModel
from typing import Literal


# Mock models for testing (replace with actual imports)
from pydantic import Field, field_validator


class TriageResult(BaseModel):
    """Mock triage result for testing."""

    type: Literal["bug", "feature", "question"]
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)

    model_config = {"extra": "forbid"}

    @field_validator("reasoning")
    @classmethod
    def reasoning_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("reasoning must not be empty")
        return v


class TestTriageResultValidation:
    """Test Pydantic validation of LLM outputs."""

    def test_valid_triage_result(self):
        """Valid result passes through."""
        result = TriageResult(
            type="bug", severity="high", confidence=0.93, reasoning="User reports crash — clearly a bug."
        )
        assert result.type == "bug"
        assert 0.0 <= result.confidence <= 1.0
        assert result.reasoning is not None

    def test_invalid_type_rejected(self):
        """LLM hallucination: returns unknown type."""
        with pytest.raises(ValidationError) as exc:
            TriageResult(
                type="critical_emergency",  # not in enum
                severity="high",
                confidence=0.9,
                reasoning="test",
            )
        assert "type" in str(exc.value)

    def test_confidence_out_of_range(self):
        """Confidence must be 0.0–1.0."""
        with pytest.raises(ValidationError):
            TriageResult(
                type="bug",
                severity="high",
                confidence=95.0,  # LLM mistake
                reasoning="test",
            )

    def test_empty_reasoning_rejected(self):
        """Reasoning must not be empty."""
        with pytest.raises(ValidationError):
            TriageResult(
                type="bug",
                severity="high",
                confidence=0.9,
                reasoning="",  # empty
            )

    def test_severity_enum_enforced(self):
        """Severity must be from allowed set."""
        for valid in ["low", "medium", "high", "critical"]:
            r = TriageResult(type="bug", severity=valid, confidence=0.8, reasoning="ok")
            assert r.severity == valid

        with pytest.raises(ValidationError):
            TriageResult(type="bug", severity="catastrophic", confidence=0.8, reasoning="ok")


class TestInputValidation:
    """Test input validation for activities and agents."""

    def test_empty_text_rejected(self):
        """Empty text should be rejected."""
        # Mock input validation - would use actual input model
        text = ""
        assert len(text.strip()) == 0
        # In actual implementation, this would raise ValidationError
        pytest.skip("Requires actual input model with validation")

    def test_text_too_long(self):
        """Text > 10000 chars should be rejected."""
        # Would test in actual implementation
        pytest.skip("Requires actual input model")


class TestProtoMapping:
    """Test proto field mapping type safety."""

    def test_severity_mapping_exhaustive(self):
        """Every valid severity maps to non-UNSPECIFIED."""
        # Would test actual SeverityMapper
        pytest.skip("Requires actual proto mapping code")

    def test_unknown_severity_fallback(self):
        """Unknown severity defaults gracefully."""
        # LLM might hallucinate "extreme" or "urgent"
        pytest.skip("Requires actual proto mapping code")
