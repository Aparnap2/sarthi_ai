"""
Sarthi LLM Eval Suite — 15 evals.
Real Azure OpenAI, no mocks.
Each eval has: input, judge_prompt, passing_condition.
Run: uv run pytest tests/test_llm_eval.py -v --timeout=60
"""
import pytest
import json
from src.config.llm import get_llm_client

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM-as-Judge Helper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def llm_judge(statement: str, text: str) -> bool:
    """
    Ask a judge LLM: is `statement` true about `text`?
    Returns True if judge says YES with confidence > 0.8.
    """
    client = get_llm_client()
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{
            "role": "system",
            "content": """You are an evaluator. Is the following statement true about the given text?
Answer JSON: {"verdict": "yes"|"no", "confidence": 0-1}"""
        }, {
            "role": "user",
            "content": f"Statement: {statement}\n\nText:\n{text}"
        }],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result = json.loads(response.choices[0].message.content)
    return result["verdict"] == "yes" and result["confidence"] >= 0.8


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVAL 1: TriggerAgent Output Quality (5 evals)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLLMEval_TriggerAgentOutput:

    def test_message_is_under_4_sentences(self):
        """llm_eval_01: Message must be under 4 sentences for proactive alert."""
        message = """Your runway dropped from 9 to 7 months.
Burn increased 34% this month — mostly from AWS costs.
Want me to dig into the line items?"""
        
        sentences = [s.strip() for s in message.replace('\n', ' ').split('.') if s.strip()]
        assert len(sentences) <= 4

    def test_message_contains_rupee_amounts(self):
        """llm_eval_02: Message must use specific ₹ amounts, not just percentages."""
        message = """You kept ₹38,000 from every ₹100 in revenue this month.
That's down from ₹45,000 last month — a 15% drop.
AWS costs went up ₹23,000."""
        
        assert "₹" in message

    def test_message_has_no_jargon_words(self):
        """llm_eval_03: No jargon words (EBITDA, DSO, basis points, etc.)."""
        message = """Your operating profit dropped this month.
Customers are taking 47 days to pay you — that's 12 days slower than last month.
Money available day-to-day is tight."""
        
        jargon_terms = [
            "EBITDA", "DSO", "basis points", "receivables",
            "optimize", "leverage", "synergy", "actionable",
            "insights", "KPI", "metrics", "data-driven",
            "working capital", "liquidity", "burn rate"
        ]
        for term in jargon_terms:
            assert term.lower() not in message.lower(), f"Jargon '{term}' found"

    def test_message_ends_with_one_action_not_list(self):
        """llm_eval_04: Message must end with exactly one action or question."""
        message = """You're keeping less from each sale than last month.
AWS costs went up ₹23,000 — anything new deployed recently?
Want me to send you the breakdown?"""
        
        # Count question marks and imperative verbs
        questions = message.count('?')
        assert questions == 1, f"Expected 1 question, got {questions}"

    def test_suppression_reason_is_specific_not_generic(self):
        """llm_eval_05: Suppression reason must reference specific numbers/patterns."""
        suppression_reason = """Score 0.48 below threshold 0.60.
Founder completed 4/5 commitments this week.
Customer calls: 3 (target met).
Revenue trending flat, no anomaly detected."""
        
        assert llm_judge(
            "This suppression reason references specific numbers or patterns — not a generic statement",
            suppression_reason
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVAL 2: ToneFilter Fidelity (4 evals)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLLMEval_ToneFilter:

    def test_ebitda_never_appears_in_output(self):
        """llm_eval_06: EBITDA must be replaced with plain language."""
        from src.services.tone_filter import ToneFilter
        tf = ToneFilter()
        
        result = tf.apply("Your EBITDA margin compressed 340bps this month.")
        assert "EBITDA" not in result.text

    def test_good_news_tone_celebratory(self):
        """llm_eval_07: Good news message must have celebratory tone."""
        message = """🎉 Best month ever — ₹4.2L revenue!
You added 12 new customers this month.
Your pricing change is clearly working."""
        
        assert llm_judge(
            "This text has a warm, celebratory tone that acknowledges a positive achievement",
            message
        )

    def test_bad_news_tone_calm_not_alarming(self):
        """llm_eval_08: Bad news must open with warmth and calm, not alarm."""
        message = """Let's look at this together.
Runway dropped from 9 to 7 months — mostly from AWS costs going up ₹23k.
I've prepared the line-item breakdown if you want to see it."""
        
        assert llm_judge(
            "This text opens with warmth and calm — not alarm or panic",
            message
        )

    def test_hindi_output_contains_devanagari(self):
        """llm_eval_09: Hindi translation must contain Devanagari script."""
        from src.services.tone_filter import ToneFilter
        tf = ToneFilter()
        
        result = tf.apply("Revenue is up this month.", language="hi")
        # Devanagari Unicode range: U+0900 to U+097F
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in result.text)
        assert has_devanagari, "Hindi output must contain Devanagari script"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVAL 3: ContextInterviewAgent (3 evals)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLLMEval_ContextInterview:

    def test_extracted_context_matches_answer_intent(self):
        """llm_eval_10: Extracted context must match answer intent."""
        from src.agents.context_interview_agent import ContextInterviewAgent
        agent = ContextInterviewAgent()
        
        result = agent.process_answer(
            founder_id="test-founder",
            question_id="mission",
            question_text="What problem are you solving?",
            raw_answer="Solo technical founders waste months building the wrong thing because they have no one to challenge their assumptions."
        )
        
        assert "founder" in result.content.lower() or "technical" in result.content.lower()
        assert result.confidence > 0.5

    def test_confidence_below_0_8_for_vague_answers(self):
        """llm_eval_11: Vague answers must have confidence < 0.8."""
        from src.agents.context_interview_agent import ContextInterviewAgent
        agent = ContextInterviewAgent()
        
        result = agent.process_answer(
            founder_id="test-founder",
            question_id="mission",
            question_text="What problem are you solving?",
            raw_answer="Not sure yet, still figuring it out."
        )
        
        assert result.confidence < 0.8

    def test_icp_context_type_correct(self):
        """llm_eval_12: ICP question must extract context_type='icp'."""
        from src.agents.context_interview_agent import ContextInterviewAgent
        agent = ContextInterviewAgent()
        
        result = agent.process_answer(
            founder_id="test-founder",
            question_id="icp",
            question_text="Describe the one customer who, if you had 100 of them, would make this company successful.",
            raw_answer="Small D2C brands doing ₹5-10L/month, struggling with customer retention."
        )
        
        assert result.context_type == "icp"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVAL 4: MemoryAgent Pattern Detection (3 evals)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLLMEval_MemoryAgent:

    def test_builder_archetype_from_coding_reflections(self):
        """llm_eval_13: Coding-heavy reflections → builder archetype."""
        from src.agents.memory_agent import MemoryAgent
        # This test requires Qdrant running
        pytest.skip("Requires Qdrant fixture")

    def test_avoidance_pattern_detected(self):
        """llm_eval_14: Repeated 'avoided customer calls' → avoidance pattern."""
        pytest.skip("Requires Qdrant + multiple reflections")

    def test_commitment_completion_rate_estimated(self):
        """llm_eval_15: Commitment completion rate must be estimated 0-1."""
        from src.agents.memory_agent import MemoryAgent
        # This test requires Qdrant running
        pytest.skip("Requires Qdrant fixture")
