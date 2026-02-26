"""DSPy signatures for LLM evaluation in IterateSwarm OS.

These signatures define the input/output structure for DSPy predictions.
Used in test_llm_evals.py for quality evaluation.
"""

import dspy


class SWERootCauseSignature(dspy.Signature):
    """Given researcher and SRE findings, identify root cause and proposed fix."""
    
    researcher_findings: str = dspy.InputField(
        desc="Findings from Researcher agent (GitHub issues, Sentry errors, prior art)"
    )
    sre_findings: str = dspy.InputField(
        desc="Metrics and errors from SRE agent (error rate, affected users, latency)"
    )
    root_cause: str = dspy.OutputField(
        desc="Specific root cause of the issue (mention component names)"
    )
    proposed_fix: str = dspy.OutputField(
        desc="Concrete code-level fix with specific changes"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score 0.0 to 1.0"
    )


class ReviewDecisionSignature(dspy.Signature):
    """Given a code diff, produce a structured review decision."""
    
    diff: str = dspy.InputField(
        desc="Git diff of the proposed change"
    )
    issues: list[str] = dspy.OutputField(
        desc="List of code quality issues found"
    )
    approved: bool = dspy.OutputField(
        desc="True if diff is safe to merge"
    )
    reasoning: str = dspy.OutputField(
        desc="Clear reasoning for the decision"
    )


class TriageUrgencySignature(dspy.Signature):
    """Classify feedback urgency given production context."""
    
    feedback_text: str = dspy.InputField()
    error_rate: float = dspy.InputField(
        desc="Current production error rate 0.0–1.0"
    )
    affected_users: int = dspy.InputField()
    urgency: str = dspy.OutputField(
        desc="One of: immediate, soon, normal, backlog"
    )
    severity: str = dspy.OutputField(
        desc="One of: critical, high, medium, low"
    )
