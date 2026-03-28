"""
DSPy signatures for the AnomalyAgent.

Uses Ollama qwen3:0.6b via the OpenAI-compatible endpoint.
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
    api_key="ollama",
    temperature=0.2,
    max_tokens=512,
    cache=False,
)
dspy.configure(lm=_lm)


# ── Signature 1: AnomalyExplainer (reused from PulseAgent) ───────

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


# ── Signature 2: AnomalyActionGenerator ──────────────────────────

class AnomalyActionGenerator(dspy.Signature):
    """
    You are Sarthi. Given an anomaly explanation, generate ONE concrete
    action for the founder to take. Not advice. An action.
    """
    explanation:      str = dspy.InputField(desc="Explanation of the anomaly")
    metric_name:      str = dspy.InputField(desc="Name of the anomalous metric")
    current_value:    str = dspy.InputField(desc="Current metric value")

    action_item:      str = dspy.OutputField(
                          desc="One concrete action starting with a verb, max 15 words")


# ── Instantiated predictors ──────────────────────────────────────
anomaly_explainer       = dspy.Predict(AnomalyExplainer)
anomaly_action_generator = dspy.Predict(AnomalyActionGenerator)
