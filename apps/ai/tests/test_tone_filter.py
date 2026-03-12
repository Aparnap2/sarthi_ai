"""Tests for ToneFilter."""
import pytest
from unittest.mock import MagicMock, patch
from src.services.tone_filter import ToneFilter, ToneResult

# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def mock_llm_response():
    """Patch OpenAI so tests are free and deterministic."""
    with patch("src.services.tone_filter.get_llm_client") as mock_get:
        instance = MagicMock()
        mock_get.return_value = instance
        instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Rewritten message."))]
        )
        yield instance


@pytest.fixture
def tf(mock_llm_response):
    return ToneFilter()


# ── Jargon replacement (mechanical — no LLM) ──────────────────────


@pytest.mark.parametrize(
    "jargon,should_be_gone",
    [
        ("EBITDA", "EBITDA"),
        ("accounts receivable", "accounts receivable"),
        ("working capital", "working capital"),
        ("leverage", "leverage"),
        ("optimize", "optimize"),
        ("actionable insights", "actionable insights"),
        ("burn rate", "burn rate"),
        ("DSO", "DSO"),
        ("YoY", "YoY"),
        ("bps", "bps"),
    ],
)
def test_jargon_replaced(tf, jargon, should_be_gone):
    cleaned, count = tf._kill_jargon(f"Your {jargon} metric is important.")
    assert should_be_gone.lower() not in cleaned.lower()
    assert count >= 1


def test_replace_jargon_returns_count(tf):
    text, count = tf._kill_jargon("EBITDA and DSO are high.")
    assert count == 2


def test_non_jargon_text_unchanged(tf):
    text = "You made ₹42,000 this month."
    cleaned, count = tf._kill_jargon(text)
    assert cleaned == text
    assert count == 0


# ── LLM rewrite (mocked) ──────────────────────────────────────────


def test_apply_returns_tone_result(tf):
    result = tf.apply("Your EBITDA compressed.")
    assert isinstance(result, ToneResult)
    assert result.text == "Rewritten message."
    assert result.original == "Your EBITDA compressed."


def test_good_news_flag_passed_to_llm(tf, mock_llm_response):
    tf.apply("Profit is up.", is_good_news=True)
    call_args = mock_llm_response.chat.completions.create.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "GOOD NEWS" in user_msg


def test_bad_news_flag_passed_to_llm(tf, mock_llm_response):
    tf.apply("Profit is down.", is_good_news=False)
    call_args = mock_llm_response.chat.completions.create.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "concerning" in user_msg.lower()


def test_owner_name_in_prompt(tf, mock_llm_response):
    tf.apply("Revenue fell.", owner_name="Priya")
    call_args = mock_llm_response.chat.completions.create.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert "Priya" in user_msg


def test_temperature_is_0_25(tf, mock_llm_response):
    tf.apply("Some message.")
    call_args = mock_llm_response.chat.completions.create.call_args
    assert call_args.kwargs["temperature"] == 0.25


# ── Hindi translation ──────────────────────────────────────────────


def test_hindi_calls_second_llm(tf, mock_llm_response):
    tf.apply("Revenue up.", language="hi")
    # Should be called twice: once for rewrite, once for Hindi
    assert mock_llm_response.chat.completions.create.call_count == 2


def test_english_does_not_call_hindi(tf, mock_llm_response):
    tf.apply("Revenue up.", language="en")
    assert mock_llm_response.chat.completions.create.call_count == 1


# ── ToneResult structure ─────────────────────────────────────────


def test_tone_result_has_jargon_count(tf):
    result = tf.apply("Check your EBITDA and DSO carefully.")
    assert result.jargon_replaced == 2


def test_tone_result_language_stored(tf):
    result = tf.apply("Some text.", language="hi")
    assert result.language == "hi"
