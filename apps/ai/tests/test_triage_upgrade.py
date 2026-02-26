"""Tests for the Triage Agent Upgrade - Urgency Detection."""

import pytest

from src.agents.triage import (
    TriageResult,
    incorporate_sre_data,
    detect_urgency_from_feedback,
)


# ========================
# Test Urgency Field
# ========================


def test_triage_result_has_urgency_field():
    """Test that TriageResult has urgency field."""
    result = TriageResult(
        classification="bug",
        severity="high",
        reasoning="User reported a crash",
        confidence=0.9,
        urgency="soon",
    )

    assert result.urgency == "soon"


def test_triage_urgency_defaults_to_normal():
    """Test that urgency defaults to 'normal'."""
    result = TriageResult(
        classification="bug",
        severity="high",
        reasoning="User reported a crash",
        confidence=0.9,
    )

    assert result.urgency == "normal"


# ========================
# Test SRE Data Incorporation
# ========================


def test_triage_incorporate_sre_critical_sets_immediate():
    """Test that CRITICAL priority sets urgency to immediate."""
    result = TriageResult(
        classification="bug",
        severity="high",
        reasoning="User reported a crash",
        confidence=0.9,
        urgency="normal",
    )

    sre_interrupt = {
        "priority": "CRITICAL",
        "affected_users": 1000,
        "error_rate": 0.5,
    }

    updated = incorporate_sre_data(result, sre_interrupt)

    assert updated.urgency == "immediate"
    assert updated.severity == "critical"


def test_triage_incorporate_sre_high_sets_soon():
    """Test that HIGH priority sets urgency to soon."""
    result = TriageResult(
        classification="bug",
        severity="medium",
        reasoning="User reported an issue",
        confidence=0.8,
        urgency="normal",
    )

    sre_interrupt = {
        "priority": "HIGH",
    }

    updated = incorporate_sre_data(result, sre_interrupt)

    assert updated.urgency == "soon"
    assert updated.severity == "high"


def test_triage_incorporate_sre_medium_upgrades_backlog():
    """Test that MEDIUM priority upgrades backlog to normal."""
    result = TriageResult(
        classification="feature",
        severity="low",
        reasoning="Nice to have",
        confidence=0.7,
        urgency="backlog",
    )

    sre_interrupt = {
        "priority": "MEDIUM",
    }

    updated = incorporate_sre_data(result, sre_interrupt)

    assert updated.urgency == "normal"


def test_triage_incorporate_sre_low_no_change():
    """Test that LOW priority doesn't change urgency."""
    result = TriageResult(
        classification="bug",
        severity="low",
        reasoning="Minor issue",
        confidence=0.6,
        urgency="normal",
    )

    sre_interrupt = {
        "priority": "LOW",
    }

    updated = incorporate_sre_data(result, sre_interrupt)

    assert updated.urgency == "normal"
    assert updated.severity == "low"


# ========================
# Test Urgency Detection from Feedback
# ========================


def test_triage_detect_urgency_outage_keyword():
    """Test detection of outage keywords."""
    text = "Production is down, the entire system is offline!"

    urgency = detect_urgency_from_feedback(text)

    assert urgency == "immediate"


def test_triage_detect_urgency_slow_keyword():
    """Test detection of slow/degraded keywords."""
    text = "The app is very slow and sometimes fails to load"

    urgency = detect_urgency_from_feedback(text)

    assert urgency == "soon"


def test_triage_detect_urgency_backlog_keyword():
    """Test detection of backlog/nice-to-have keywords."""
    text = "This is a nice to have enhancement for the UI"

    urgency = detect_urgency_from_feedback(text)

    assert urgency == "backlog"


def test_triage_detect_urgency_no_keyword_returns_normal():
    """Test that normal text returns normal urgency."""
    text = "Can you add a button to export data?"

    urgency = detect_urgency_from_feedback(text)

    assert urgency == "normal"


def test_triage_detect_urgency_llm_fallback():
    """Test LLM fallback for complex urgency detection."""
    # This test checks that when keywords don't match clearly,
    # the function returns "normal" as the safe fallback
    text = "I noticed something odd in the logs"

    urgency = detect_urgency_from_feedback(text)

    assert urgency == "normal"


# ========================
# Test Severity Escalation
# ========================


def test_triage_severity_escalates_with_sre_critical():
    """Test that severity escalates to critical with CRITICAL SRE."""
    result = TriageResult(
        classification="bug",
        severity="low",
        reasoning="Minor bug found in testing",
        confidence=0.8,
    )

    sre_interrupt = {"priority": "CRITICAL"}

    updated = incorporate_sre_data(result, sre_interrupt)

    assert updated.severity == "critical"


def test_triage_existing_critical_not_downgraded():
    """Test that existing critical severity is not downgraded."""
    result = TriageResult(
        classification="bug",
        severity="critical",
        reasoning="Critical issue",
        confidence=0.95,
        urgency="immediate",
    )

    sre_interrupt = {"priority": "HIGH"}  # High should not downgrade critical

    updated = incorporate_sre_data(result, sre_interrupt)

    # Critical should remain critical
    assert updated.severity == "critical"
    # But urgency should still be updated
    assert updated.urgency == "soon"


# ========================
# Test Backward Compatibility
# ========================


def test_triage_backward_compatible_without_sre_data():
    """Test backward compatibility when no SRE data provided."""
    result = TriageResult(
        classification="bug",
        severity="high",
        reasoning="Something is broken",
        confidence=0.9,
    )

    # Without SRE data, urgency should remain default
    assert result.urgency == "normal"
    assert result.affected_users == 0
    assert result.error_rate == 0.0


def test_triage_sre_data_updates_metrics():
    """Test that SRE data updates affected_users and error_rate."""
    result = TriageResult(
        classification="bug",
        severity="high",
        reasoning="Something is broken",
        confidence=0.9,
    )

    sre_interrupt = {
        "priority": "HIGH",
        "affected_users": 500,
        "error_rate": 0.25,
    }

    updated = incorporate_sre_data(result, sre_interrupt)

    assert updated.affected_users == 500
    assert updated.error_rate == 0.25
