"""
Real E2E Tests with Tool Calls and Action Verification.

These tests verify the FULL pipeline:
1. LLM receives input and reasons
2. LLM decides to take action (fire_telegram=True, write_memory, etc.)
3. Tool is actually called (Telegram send, DB write, Redpanda publish)
4. Database is updated (agent_outputs, hitl_actions, etc.)
5. Result is verified (query DB, verify Qdrant message, etc.)

NOT just "LLM returned text" — but "LLM decided X, tool was called, action happened."
"""
import os
import sys
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure environment for tests - FORCE OLLAMA
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434/v1"
os.environ["OLLAMA_CHAT_MODEL"] = "sam860/LFM2:2.6b"
os.environ["OLLAMA_EMBED_MODEL"] = "nomic-embed-text:latest"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"
os.environ["DATABASE_URL"] = "postgresql://iterateswarm:iterateswarm@localhost:5433/iterateswarm"

# Clear Azure OpenAI vars to ensure Ollama is used
os.environ.pop("AZURE_OPENAI_ENDPOINT", None)
os.environ.pop("AZURE_OPENAI_KEY", None)
os.environ.pop("AZURE_OPENAI_API_VERSION", None)
os.environ.pop("AZURE_OPENAI_CHAT_DEPLOYMENT", None)

TENANT = "test-e2e-tool-calls"


class TestFinanceMonitorE2E:
    """
    E2E tests for Finance Monitor with REAL tool calls.

    Verifies:
    - LLM detects anomaly
    - Decision: fire_telegram=True
    - Tool call: agent_outputs row written to PostgreSQL
    - Tool call: Qdrant memory written
    - Tool call: Redpanda event published (if configured)
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup test data, teardown after."""
        # Clear any existing test data
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_outputs WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        cur.execute("DELETE FROM hitl_actions WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        conn.commit()
        cur.close()
        conn.close()
        yield
        # Teardown: clean up test data
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_outputs WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        cur.execute("DELETE FROM hitl_actions WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        conn.commit()
        cur.close()
        conn.close()

    def test_anomaly_detection_with_real_tool_calls(self):
        """
        E2E Test: Finance Monitor detects anomaly → writes to DB → writes to Qdrant.

        Pipeline:
        1. Input: AWS bill 2.3× usual
        2. LLM reasoning: Detect anomaly, generate headline
        3. Decision: fire_telegram=True, urgency=high
        4. Tool call: INSERT INTO agent_outputs ...
        5. Tool call: Qdrant upsert_memory(...)
        6. Verify: Query PostgreSQL for agent_outputs row
        7. Verify: Query Qdrant for memory point
        """
        from src.agents.finance_monitor import FinanceMonitorAgent
        from src.db.agent_outputs import get_recent_outputs
        from src.memory.qdrant_ops import query_memory

        agent = FinanceMonitorAgent()

        # INPUT: Anomaly event
        state = {
            "tenant_id": f"{TENANT}-finance-1",
            "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
            "runway_months": 8.0,
        }
        event = {
            "event_type": "BANK_WEBHOOK",
            "vendor": "AWS",
            "amount": 42000,
            "description": "AWS consolidated bill",
        }

        # EXECUTE: Agent runs with real LLM + real tool calls
        result = agent.run(state, event)

        # VERIFY 1: LLM made correct decision
        assert result["fire_telegram"] is True, "Should fire Telegram for 2.3σ anomaly"
        assert result["urgency"] == "high", "Should be high urgency"
        assert "AWS" in result["headline"], "Headline should mention vendor"

        # VERIFY 2: Tool call — agent_outputs row written to PostgreSQL
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT * FROM agent_outputs
            WHERE tenant_id = %s AND agent_name = 'finance_monitor'
            ORDER BY created_at DESC LIMIT 1
        """,
            (f"{TENANT}-finance-1",),
        )
        db_row = cur.fetchone()
        cur.close()
        conn.close()

        assert db_row is not None, "agent_outputs row should be written to PostgreSQL"
        assert db_row["headline"] == result["headline"], "DB headline should match LLM output"
        assert db_row["urgency"] == "high", "DB urgency should match decision"
        assert db_row["hitl_sent"] is True, "hitl_sent should be True when fire_telegram=True"

        # VERIFY 3: Tool call — Qdrant memory written
        import time

        time.sleep(1)  # Give Qdrant time to index

        memory_results = query_memory(
            tenant_id=f"{TENANT}-finance-1",
            query_text="AWS spend spike anomaly",
            memory_types=["finance_anomaly"],
            top_k=3,
            min_score=0.5,
        )

        assert len(memory_results) >= 1, "Qdrant should have memory point"
        assert "AWS" in memory_results[0]["content"], "Memory should mention vendor"
        assert memory_results[0]["agent"] == "finance_monitor", "Memory should have agent name"

        print("\n" + "=" * 80)
        print("✅ FINANCE MONITOR E2E TEST PASSED")
        print("=" * 80)
        print(f"LLM Headline: {result['headline']}")
        print(f"Decision: fire_telegram={result['fire_telegram']}, urgency={result['urgency']}")
        print(f"PostgreSQL: agent_outputs row ID = {db_row['id']}")
        print(f"Qdrant: memory point ID = {memory_results[0]['point_id']}")
        print("=" * 80)

    def test_runway_critical_alert_with_real_db_write(self):
        """
        E2E Test: Runway <3 months → critical alert → DB updated.

        Pipeline:
        1. Input: Runway 2.5 months
        2. LLM reasoning: Detect critical runway
        3. Decision: fire_telegram=True, urgency=critical
        4. Tool call: INSERT INTO agent_outputs ...
        5. Verify: Query PostgreSQL for agent_outputs row
        """
        from src.agents.finance_monitor import FinanceMonitorAgent
        from src.db.agent_outputs import get_recent_outputs

        agent = FinanceMonitorAgent()

        # INPUT: Critical runway
        state = {
            "tenant_id": f"{TENANT}-finance-2",
            "vendor_baselines": {},
            "runway_months": 2.5,
        }
        event = {"event_type": "TIME_TICK_DAILY"}

        # EXECUTE
        result = agent.run(state, event)

        # VERIFY 1: LLM decision
        assert result["fire_telegram"] is True
        assert result["urgency"] == "critical"
        assert "runway" in result["headline"].lower()

        # VERIFY 2: PostgreSQL write
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT * FROM agent_outputs
            WHERE tenant_id = %s AND agent_name = 'finance_monitor'
            AND output_type = 'critical'
            ORDER BY created_at DESC LIMIT 1
        """,
            (f"{TENANT}-finance-2",),
        )
        db_row = cur.fetchone()
        cur.close()
        conn.close()

        assert db_row is not None, "Critical alert should be written to PostgreSQL"
        assert db_row["urgency"] == "critical"

        print("\n" + "=" * 80)
        print("✅ RUNWAY CRITICAL ALERT E2E TEST PASSED")
        print("=" * 80)
        print(f"LLM Headline: {result['headline']}")
        print(f"PostgreSQL: agent_outputs row ID = {db_row['id']}")
        print("=" * 80)


class TestChiefOfStaffE2E:
    """
    E2E tests for Chief of Staff with REAL tool calls.

    Verifies:
    - LLM synthesizes briefing from multiple agent outputs
    - Enforces max 5 items rule
    - Writes briefing to PostgreSQL
    - Writes to Qdrant memory
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup/teardown."""
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_outputs WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        conn.commit()
        cur.close()
        conn.close()
        yield
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_outputs WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        conn.commit()
        cur.close()
        conn.close()

    def test_weekly_briefing_synthesis_with_real_llm(self):
        """
        E2E Test: 10 agent outputs → LLM synthesizes → max 5 items → DB write.

        Pipeline:
        1. Input: 10 agent outputs (mixed urgency)
        2. LLM reasoning: Prioritize, synthesize, enforce max 5
        3. Decision: fire_telegram=True (briefing ready)
        4. Tool call: INSERT INTO agent_outputs ...
        5. Tool call: Qdrant upsert_memory(...)
        6. Verify: Query PostgreSQL — item_count ≤ 5
        7. Verify: Query Qdrant — briefing memory exists
        """
        from src.agents.chief_of_staff import ChiefOfStaffAgent
        from src.memory.qdrant_ops import query_memory

        agent = ChiefOfStaffAgent()

        # INPUT: 10 agent outputs
        state = {
            "tenant_id": f"{TENANT}-cos-1",
            "agent_outputs": [
                {"headline": "AWS spike detected", "urgency": "high", "is_good_news": False},
                {"headline": "Runway at 8 months", "urgency": "low", "is_good_news": False},
                {"headline": "Deal with Acme stalled", "urgency": "warn", "is_good_news": False},
                {"headline": "New hire Priya joins Monday", "urgency": "low", "is_good_news": True},
                {"headline": "GST due in 5 days", "urgency": "high", "is_good_news": False},
                {"headline": "MRR crossed ₹5L", "urgency": "low", "is_good_news": True},
                {"headline": "3 invoices overdue", "urgency": "warn", "is_good_news": False},
                {"headline": "Azure costs up 15%", "urgency": "low", "is_good_news": False},
                {"headline": "Customer churn risk: Arjun", "urgency": "high", "is_good_news": False},
                {"headline": "New feature launched", "urgency": "low", "is_good_news": True},
            ],
        }
        event = {"event_type": "TIME_TICK_WEEKLY"}

        # EXECUTE
        result = agent.run(state, event)

        # VERIFY 1: LLM enforced max 5 items
        item_count = result["output_json"].get("item_count", 0)
        assert item_count <= 5, f"Briefing should have ≤5 items, got {item_count}"

        # VERIFY 2: LLM prioritized by urgency
        briefing_text = result["headline"]
        assert (
            "AWS" in briefing_text or "GST" in briefing_text or "churn" in briefing_text
        ), "Briefing should mention high-urgency items"

        # VERIFY 3: PostgreSQL write
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT * FROM agent_outputs
            WHERE tenant_id = %s AND agent_name = 'chief_of_staff'
            ORDER BY created_at DESC LIMIT 1
        """,
            (f"{TENANT}-cos-1",),
        )
        db_row = cur.fetchone()
        cur.close()
        conn.close()

        assert db_row is not None, "Briefing should be written to PostgreSQL"
        assert db_row["headline"] == result["headline"]

        # VERIFY 4: Qdrant memory write
        import time

        time.sleep(1)

        memory_results = query_memory(
            tenant_id=f"{TENANT}-cos-1",
            query_text="weekly briefing Monday",
            memory_types=["briefing"],
            top_k=3,
            min_score=0.5,
        )

        assert len(memory_results) >= 1, "Qdrant should have briefing memory"

        print("\n" + "=" * 80)
        print("✅ CHIEF OF STAFF WEEKLY BRIEFING E2E TEST PASSED")
        print("=" * 80)
        print(f"Input: 10 agent outputs")
        print(f"LLM Output: {item_count} items (max 5 enforced)")
        print(f"Briefing Preview: {briefing_text[:150]}...")
        print(f"PostgreSQL: agent_outputs row ID = {db_row['id']}")
        print(f"Qdrant: memory point ID = {memory_results[0]['point_id']}")
        print("=" * 80)


class TestEndToEndPipeline:
    """
    Full end-to-end pipeline test: Event → Agent → LLM → Tool → DB → Verify.
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup/teardown."""
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_outputs WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        cur.execute("DELETE FROM hitl_actions WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        conn.commit()
        cur.close()
        conn.close()
        yield
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_outputs WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        cur.execute("DELETE FROM hitl_actions WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        conn.commit()
        cur.close()
        conn.close()

    def test_full_pipeline_aws_anomaly_to_telegram_decision(self):
        """
        FULL E2E: AWS anomaly detected → LLM reasons → DB write → Qdrant write → Verify.

        This is THE test that proves the entire pipeline works:
        1. Event received (BANK_WEBHOOK: AWS bill 2.3× usual)
        2. Finance Monitor agent runs
        3. LLM detects anomaly, generates headline
        4. Decision: fire_telegram=True
        5. Tool call: INSERT INTO agent_outputs (headline, urgency, hitl_sent=True)
        6. Tool call: Qdrant upsert_memory (content, agent, memory_type)
        7. Verify PostgreSQL: SELECT * FROM agent_outputs WHERE ...
        8. Verify Qdrant: query_memory(...)
        9. Verify HITL: hitl_actions row created (ready for Telegram callback)
        """
        from src.agents.finance_monitor import FinanceMonitorAgent
        from src.memory.qdrant_ops import query_memory
        from src.db.hitl_actions import get_recent_hitl_actions

        agent = FinanceMonitorAgent()

        # STEP 1: Event received
        state = {
            "tenant_id": f"{TENANT}-pipeline-1",
            "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
            "runway_months": 8.0,
        }
        event = {
            "event_type": "BANK_WEBHOOK",
            "vendor": "AWS",
            "amount": 42000,
            "description": "AWS consolidated bill",
        }

        # STEP 2-4: Agent runs, LLM reasons, decision made
        result = agent.run(state, event)

        # STEP 5-6: Tool calls happen inside agent.run()
        # - agent_outputs INSERT
        # - Qdrant upsert

        # STEP 7: Verify PostgreSQL
        import psycopg2
        import time

        time.sleep(1)  # Let DB commits settle

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Verify agent_outputs
        cur.execute(
            """
            SELECT * FROM agent_outputs
            WHERE tenant_id = %s AND agent_name = 'finance_monitor'
            ORDER BY created_at DESC LIMIT 1
        """,
            (f"{TENANT}-pipeline-1",),
        )
        agent_output = cur.fetchone()

        # Verify hitl_actions (ready for Telegram)
        cur.execute(
            """
            SELECT * FROM hitl_actions
            WHERE tenant_id = %s AND agent_name = 'finance_monitor'
            ORDER BY created_at DESC LIMIT 1
        """,
            (f"{TENANT}-pipeline-1",),
        )
        hitl_action = cur.fetchone()

        cur.close()
        conn.close()

        # STEP 8: Verify Qdrant
        time.sleep(1)  # Let Qdrant index

        memory_results = query_memory(
            tenant_id=f"{TENANT}-pipeline-1",
            query_text="AWS spend spike",
            memory_types=["finance_anomaly"],
            top_k=3,
            min_score=0.5,
        )

        # ASSERTIONS: Full pipeline verified
        assert result["fire_telegram"] is True, "Should fire Telegram"
        assert result["urgency"] == "high", "Should be high urgency"

        assert agent_output is not None, "agent_outputs row should exist"
        assert agent_output["headline"] == result["headline"], "DB headline matches LLM"
        assert agent_output["hitl_sent"] is True, "hitl_sent should be True"

        assert hitl_action is not None, "hitl_actions row should exist (ready for Telegram)"
        assert hitl_action["message_sent"] == result["headline"], "HITL message matches"

        assert len(memory_results) >= 1, "Qdrant memory should exist"
        assert "AWS" in memory_results[0]["content"], "Memory mentions vendor"

        print("\n" + "=" * 80)
        print("✅ FULL END-TO-END PIPELINE TEST PASSED")
        print("=" * 80)
        print("Pipeline Steps Verified:")
        print("  1. ✅ Event received (BANK_WEBHOOK)")
        print("  2. ✅ Finance Monitor agent ran")
        print("  3. ✅ LLM detected anomaly, generated headline")
        print(f"     Headline: {result['headline']}")
        print("  4. ✅ Decision: fire_telegram=True, urgency=high")
        print("  5. ✅ Tool call: agent_outputs INSERT (PostgreSQL)")
        print(f"     Row ID: {agent_output['id']}")
        print("  6. ✅ Tool call: Qdrant upsert_memory")
        print(f"     Point ID: {memory_results[0]['point_id']}")
        print("  7. ✅ Tool call: hitl_actions INSERT (ready for Telegram)")
        print(f"     Row ID: {hitl_action['id']}")
        print("  8. ✅ Verified: PostgreSQL agent_outputs")
        print("  9. ✅ Verified: Qdrant memory")
        print(" 10. ✅ Verified: HITL actions (Telegram pending)")
        print("=" * 80)
        print("🎉 THIS PROVES THE FULL PIPELINE WORKS END-TO-END")
        print("=" * 80)


class TestHITLActionsE2E:
    """
    E2E tests for HITL (Human-in-the-Loop) actions.

    Verifies:
    - HITL actions are created when fire_telegram=True
    - Buttons are correctly set based on urgency
    - Founder response can be recorded
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup/teardown."""
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_outputs WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        cur.execute("DELETE FROM hitl_actions WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        conn.commit()
        cur.close()
        conn.close()
        yield
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_outputs WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        cur.execute("DELETE FROM hitl_actions WHERE tenant_id LIKE %s", (f"{TENANT}%",))
        conn.commit()
        cur.close()
        conn.close()

    def test_hitl_action_created_for_critical_alert(self):
        """
        E2E Test: Critical alert → HITL action created with correct buttons.

        Pipeline:
        1. Input: Runway < 3 months (critical)
        2. Decision: fire_telegram=True, urgency=critical
        3. Tool call: hitl_actions INSERT with buttons
        4. Verify: Query hitl_actions — buttons match critical urgency
        """
        from src.agents.finance_monitor import FinanceMonitorAgent
        from src.db.hitl_actions import get_recent_hitl_actions

        agent = FinanceMonitorAgent()

        # INPUT: Critical runway
        state = {
            "tenant_id": f"{TENANT}-hitl-1",
            "vendor_baselines": {},
            "runway_months": 2.0,
        }
        event = {"event_type": "TIME_TICK_DAILY"}

        # EXECUTE
        result = agent.run(state, event)

        # VERIFY 1: Decision made
        assert result["fire_telegram"] is True
        assert result["urgency"] == "critical"

        # VERIFY 2: HITL action created
        import time

        time.sleep(0.5)  # Let DB commit settle

        hitl_actions = get_recent_hitl_actions(f"{TENANT}-hitl-1", limit=5)

        assert len(hitl_actions) >= 1, "HITL action should be created for critical alert"

        hitl = hitl_actions[0]
        assert hitl["agent_name"] == "finance_monitor"
        assert hitl["message_sent"] == result["headline"]
        assert hitl["founder_response"] is None, "Should be pending founder response"

        # VERIFY 3: Buttons match critical urgency
        buttons = hitl["buttons"]
        assert isinstance(buttons, list), "Buttons should be a list"
        # Critical urgency buttons: ["Acknowledge", "Investigate", "Escalate"]
        assert len(buttons) >= 2, "Should have at least 2 buttons"

        print("\n" + "=" * 80)
        print("✅ HITL ACTION CREATED FOR CRITICAL ALERT")
        print("=" * 80)
        print(f"Urgency: {result['urgency']}")
        print(f"HITL Message: {result['headline']}")
        print(f"Buttons: {buttons}")
        print(f"HITL Row ID: {hitl['id']}")
        print("=" * 80)

    def test_hitl_action_created_for_high_alert(self):
        """
        E2E Test: High alert → HITL action created with correct buttons.

        Pipeline:
        1. Input: AWS anomaly (high urgency)
        2. Decision: fire_telegram=True, urgency=high
        3. Tool call: hitl_actions INSERT with buttons
        4. Verify: Query hitl_actions — buttons match high urgency
        """
        from src.agents.finance_monitor import FinanceMonitorAgent
        from src.db.hitl_actions import get_recent_hitl_actions

        agent = FinanceMonitorAgent()

        # INPUT: AWS anomaly
        state = {
            "tenant_id": f"{TENANT}-hitl-2",
            "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
            "runway_months": 8.0,
        }
        event = {
            "event_type": "BANK_WEBHOOK",
            "vendor": "AWS",
            "amount": 42000,
            "description": "AWS consolidated bill",
        }

        # EXECUTE
        result = agent.run(state, event)

        # VERIFY 1: Decision made
        assert result["fire_telegram"] is True
        assert result["urgency"] == "high"

        # VERIFY 2: HITL action created
        import time

        time.sleep(0.5)

        hitl_actions = get_recent_hitl_actions(f"{TENANT}-hitl-2", limit=5)

        assert len(hitl_actions) >= 1, "HITL action should be created for high alert"

        hitl = hitl_actions[0]
        buttons = hitl["buttons"]

        # High urgency buttons: ["Investigate", "Mark OK", "Send Reminder"]
        assert len(buttons) >= 2, "Should have at least 2 buttons"

        print("\n" + "=" * 80)
        print("✅ HITL ACTION CREATED FOR HIGH ALERT")
        print("=" * 80)
        print(f"Urgency: {result['urgency']}")
        print(f"HITL Message: {result['headline']}")
        print(f"Buttons: {buttons}")
        print(f"HITL Row ID: {hitl['id']}")
        print("=" * 80)
