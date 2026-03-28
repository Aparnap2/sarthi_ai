"""
DSPy signatures for the PulseAgent.

Uses Ollama qwen3:0.6b via the OpenAI-compatible endpoint.
dspy.LM is configured once at module level; callers just
instantiate the predictors.

Signatures:
  PulseSummarizer    — main narrative + action item
  AnomalyExplainer   — explains a detected anomaly in plain English
"""
from __future__ import annotations
import os
import dspy

# ── Configure DSPy LM (Ollama, OpenAI-compat endpoint) ───────────
_OLLAMA_BASE  = os.getenv("OLLAMA_BASE_URL",   "http://localhost:11434/v1")
_CHAT_MODEL   = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:0.6b")

_lm = dspy.LM(
    model=f"openai/{_CHAT_MODEL}",
    api_base=_OLLAMA_BASE,
    api_key="ollama",          # Ollama ignores the key value
    temperature=0.2,
    max_tokens=512,
    cache=False,               # no caching — metrics must be live
)
dspy.configure(lm=_lm)


# ── Signature 1: PulseSummarizer ─────────────────────────────────

class PulseSummarizer(dspy.Signature):
    """
    You are Sarthi, a brutally honest co-founder AI for solo technical
    founders. Given the current financial metrics and historical context,
    write a plain-English business pulse summary.

    Rules:
    - narrative: exactly 3 sentences. Sentence 1 = what's true now.
      Sentence 2 = trend vs last period. Sentence 3 = biggest risk.
    - action_item: exactly ONE concrete action. Not advice. An action.
      Start with a verb. Max 15 words.
    - Never use "leverage", "synergy", or "ecosystem".
    - Write like a trusted co-founder, not a consultant.
    """
    # Inputs
    mrr:              str = dspy.InputField(desc="Current MRR with currency")
    arr:              str = dspy.InputField(desc="Current ARR with currency")
    runway:           str = dspy.InputField(desc="Runway in months")
    burn:             str = dspy.InputField(desc="30-day burn amount")
    customers:        str = dspy.InputField(
                          desc="Active, new, churned customer counts")
    mrr_growth:       str = dspy.InputField(
                          desc="MRR % change vs previous snapshot")
    quick_ratio:      str = dspy.InputField(
                          desc="Quick ratio (new+expansion)/(churn+contraction)")
    active_users:     str = dspy.InputField(desc="Active users in last 30 days")
    historical:       str = dspy.InputField(
                          desc="Context from previous snapshots (may be empty)")
    anomalies:        str = dspy.InputField(
                          desc="Detected anomalies this period (may be 'none')")

    # Outputs
    narrative:        str = dspy.OutputField(
                          desc="3-sentence plain-English business pulse")
    action_item:      str = dspy.OutputField(
                          desc="One concrete action starting with a verb")


# ── Signature 2: AnomalyExplainer ────────────────────────────────

class AnomalyExplainer(dspy.Signature):
    """
    You are Sarthi. A metric has moved unexpectedly.
    Explain what it means to the founder in plain English.
    Be specific: reference the numbers. Suggest one thing to check first.
    """
    metric_name:      str = dspy.InputField(desc="Name of the anomalous metric")
    current_value:    str = dspy.InputField(desc="Current metric value")
    baseline_value:   str = dspy.InputField(desc="Expected / baseline value")
    deviation_pct:    str = dspy.InputField(desc="% deviation from baseline")
    historical:       str = dspy.InputField(
                          desc="Relevant historical context for this metric")

    explanation:      str = dspy.OutputField(
                          desc="Plain-English explanation of what changed and why it matters")
    check_first:      str = dspy.OutputField(
                          desc="The single most important thing to investigate first")


# ── Instantiated predictors (importable by nodes.py) ─────────────
pulse_summarizer  = dspy.Predict(PulseSummarizer)
anomaly_explainer = dspy.Predict(AnomalyExplainer)
