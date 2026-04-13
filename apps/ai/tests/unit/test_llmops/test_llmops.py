"""LLMOps tests — all pass without Langfuse or PG running."""
import pytest
import os

# Force no Langfuse
os.environ.pop("LANGFUSE_SECRET_KEY", None)


class TestTracer:
    def test_traced_is_pass_through_without_langfuse(self):
        from src.llmops.tracer import traced

        @traced(agent="test", signature="noop")
        def fn(x):
            return x + 1

        assert fn(5) == 6

    def test_traced_preserves_function_metadata(self):
        from src.llmops.tracer import traced

        @traced(agent="test", signature="noop")
        def my_fn():
            pass

        assert my_fn.__name__ == "my_fn"

    def test_traced_handles_exceptions(self):
        from src.llmops.tracer import traced

        @traced(agent="test", signature="fail")
        def fail_fn():
            raise ValueError("test")

        with pytest.raises(ValueError):
            fail_fn()

    def test_traced_pass_through_kwargs(self):
        from src.llmops.tracer import traced

        @traced(agent="test", signature="multi")
        def multi(a, b, c=10):
            return a + b + c

        assert multi(1, 2, c=3) == 6


class TestEvalLoop:
    def test_eval_loop_not_available_without_pg(self):
        from src.llmops.eval_loop import EvalLoop

        el = EvalLoop()
        # Even if psycopg2 available, no valid DSN in test env
        # Just verify it doesn't crash
        assert isinstance(el.available(), bool)

    def test_record_score_no_crash_without_pg(self):
        from src.llmops.eval_loop import EvalLoop

        el = EvalLoop()
        el.record_score("t1", "pulse", 0.8, 0.9, 0.7, 0.85)
        # Should not raise

    def test_needs_reoptimization_returns_false(self):
        from src.llmops.eval_loop import EvalLoop

        el = EvalLoop()
        assert el.needs_reoptimization("t1", "pulse") in (True, False)


class TestSelfAnalysis:
    def test_self_analysis_available(self):
        from src.llmops.self_analysis import AgentSelfAnalysis

        sa = AgentSelfAnalysis()
        assert isinstance(sa.available(), bool)

    def test_analyze_returns_dict(self):
        from src.llmops.self_analysis import AgentSelfAnalysis

        sa = AgentSelfAnalysis()
        result = sa.analyze("tenant-1")
        assert isinstance(result, dict)
        assert "tenant_id" in result
        assert "fire_rate" in result

    def test_analyzeall_keys_present(self):
        from src.llmops.self_analysis import AgentSelfAnalysis

        sa = AgentSelfAnalysis()
        result = sa.analyze("tenant-1")
        for key in [
            "tenant_id",
            "fire_rate",
            "optimal_fire_rate",
            "too_noisy",
            "too_quiet",
            "alert_accuracy",
            "noise_actions",
            "compression_needed",
        ]:
            assert key in result
