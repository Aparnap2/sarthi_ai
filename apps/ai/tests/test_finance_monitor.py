"""Tests for Finance Monitor Agent."""
import pytest
from unittest.mock import patch, MagicMock
from src.agents.finance_monitor import FinanceMonitorAgent
from src.agents.base import BANNED_JARGON

TENANT = "test-tenant-finance"


class TestFinanceMonitor:
    """Test suite for FinanceMonitorAgent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = FinanceMonitorAgent()

    def test_spend_anomaly_2sigma_fires(self):
        """Test that spend >2σ triggers alert."""
        with patch.object(self.agent, '_explain_anomaly', return_value="AWS bill ₹42,000 — 2.3× usual. High."):
            state = {
                "tenant_id": TENANT,
                "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
                "runway_months": 8.0,
            }
            event = {
                "event_type": "BANK_WEBHOOK",
                "vendor": "AWS",
                "amount": 42000,
                "description": "AWS consolidated bill",
            }
            result = self.agent.run(state, event)
            assert result["fire_telegram"] is True
            assert "AWS" in result["headline"]
            assert result["urgency"] == "high"

    def test_spend_within_1sigma_silent(self):
        """Test that spend <2σ does not trigger alert."""
        state = {
            "tenant_id": TENANT,
            "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
            "runway_months": 8.0,
        }
        event = {
            "event_type": "BANK_WEBHOOK",
            "vendor": "AWS",
            "amount": 19500,
            "description": "AWS consolidated bill",
        }
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is False

    def test_runway_critical_fires(self):
        """Test that runway <3 months triggers critical alert."""
        state = {"tenant_id": TENANT, "vendor_baselines": {}, "runway_months": 2.5}
        event = {"event_type": "TIME_TICK_DAILY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert result["urgency"] == "critical"
        assert "runway" in result["headline"].lower()

    def test_runway_warning_fires(self):
        """Test that runway 3-6 months triggers warning alert."""
        state = {"tenant_id": TENANT, "vendor_baselines": {}, "runway_months": 5.0}
        event = {"event_type": "TIME_TICK_DAILY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert result["urgency"] == "warn"

    def test_runway_healthy_silent(self):
        """Test that runway >6 months does not trigger alert."""
        state = {"tenant_id": TENANT, "vendor_baselines": {}, "runway_months": 12.0}
        event = {"event_type": "TIME_TICK_DAILY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is False

    def test_no_jargon_in_headline(self):
        """Test that output contains no banned jargon."""
        with patch.object(self.agent, '_explain_anomaly', return_value="AWS bill ₹42,000 — 2.3× usual. High."):
            state = {
                "tenant_id": TENANT,
                "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
                "runway_months": 8.0,
            }
            event = {
                "event_type": "BANK_WEBHOOK",
                "vendor": "AWS",
                "amount": 42000,
                "description": "AWS bill",
            }
            result = self.agent.run(state, event)
            for term in BANNED_JARGON:
                assert term.lower() not in result.get("headline", "").lower()

    def test_anomaly_cites_past_context(self):
        """Finance Monitor must reference prior history when available."""
        from src.memory.qdrant_ops import upsert_memory, query_memory
        
        # Mock query_memory to return a past AWS spike
        mock_memory = [
            {
                "content": "AWS spike March 2026 — training run for ML model.",
                "score": 0.85,
            }
        ]
        
        # Mock LLM response that cites the memory
        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message.content = "AWS 2.3× usual — last spike was March 2026 training run."
        
        with patch.object(self.agent, '_query_qdrant_memory', return_value=mock_memory):
            with patch('src.agents.finance_monitor.get_llm_client') as mock_get_client:
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_llm_response
                
                state = {
                    "tenant_id": TENANT,
                    "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
                    "runway_months": 8.0,
                }
                event = {
                    "event_type": "BANK_WEBHOOK",
                    "vendor": "AWS",
                    "amount": 42000,
                    "description": "AWS consolidated",
                }
                result = self.agent.run(state, event)
                
                # Headline must mention history, not just the number
                headline_lower = result["headline"].lower()
                assert any(word in headline_lower 
                           for word in ["last", "previous", "march", 
                                       "training", "first time", "before", "history"]), \
                    f"Headline should cite memory: {result['headline']}"
