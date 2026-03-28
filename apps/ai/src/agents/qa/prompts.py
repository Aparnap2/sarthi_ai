"""
DSPy signatures for the QAAgent.

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
    max_tokens=256,
    cache=False,
)
dspy.configure(lm=_lm)


# ── The 20 canonical founder questions ───────────────────────────

FOUNDER_QUESTIONS = {
    "mrr":             "What is our current MRR?",
    "arr":             "What is our ARR?",
    "mrr_growth":      "How did MRR grow this month?",
    "burn":            "What is our monthly burn?",
    "runway":          "How many months of runway do we have?",
    "balance":         "What is our bank balance?",
    "customers":       "How many paying customers do we have?",
    "new_customers":   "How many new customers did we add this month?",
    "churn":           "What is our churn rate?",
    "churned":         "How many customers churned this month?",
    "top_customers":   "Who are our top customers by revenue?",
    "cac":             "What is our CAC?",
    "ltv":             "What is our LTV?",
    "active_users":    "How many active users did we have last month?",
    "revenue_growth":  "What is our revenue growth rate?",
    "biggest_expense": "What is our biggest expense?",
    "vendor_costs":    "How much are we spending on AWS / infra?",
    "last_week":       "What happened to revenue last week?",
    "vs_last_month":   "How does this month compare to last month?",
    "investor_update": "Can you draft my investor update?",
}


# ── Signature: FounderQA ─────────────────────────────────────────

class FounderQA(dspy.Signature):
    """
    Answer a SaaS founder's business question directly.
    Use the data provided. Be specific — use numbers.
    1-2 sentences max. No preamble. No buzzwords.
    If the answer isn't in the data, say 'I don't have that data yet.
    Connect your Stripe/bank account to get this.'
    """
    question:   str = dspy.InputField(desc="Founder's question")
    data:       str = dspy.InputField(desc="Current business metrics as JSON")
    past_answer:str = dspy.InputField(
                      desc="Previous answer to this question from memory, or 'First time asked.'")

    answer:     str = dspy.OutputField(
                      desc="Direct 1-2 sentence answer with numbers. End with one follow-up if relevant.")


# ── Instantiated predictor ──────────────────────────────────────
founder_qa = dspy.Predict(FounderQA)
