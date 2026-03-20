# Sarthi v1.0 — Implementation TODO List
## 2-Agent Focused Build (Finance + BI)

**Version:** 1.0  
**Date:** March 21, 2026  
**Status:** Phase 0 COMPLETE ✅

---

## Phase 0 ✅ — Baseline Verification (COMPLETE)

**Target:** Confirm existing infrastructure and codebase

### Completed Tasks

- [x] Verify Docker containers running (postgres, qdrant, redpanda, temporal, ollama)
- [x] Check Ollama models: `docker exec ollama ollama list`
- [x] Verify existing codebase structure (apps/core, apps/ai)
- [x] Confirm existing tests pass (255+ baseline)
- [x] Create `feature/sarthi-v1` branch from v4.2.0-alpha

**Exit Criteria:** ✅ MET

---

## Phase 1 🔲 — Infrastructure Setup

**Target:** Docker containers, database migrations, Qdrant collections

### Tasks

#### 1A: Database Migration 003

- [ ] Create `infra/migrations/003_sarthi_stripped.sql`
  - [ ] `bi_queries` table (BI query history)
  - [ ] Add `avg_30d`, `avg_90d`, `transaction_count` to `vendor_baselines`
  - [ ] Add `langfuse_trace`, `anomaly_score` to `agent_outputs`
  - [ ] Indexes: `idx_bi_queries_tenant`, `idx_transactions_vendor`
- [ ] Apply migration: `psql "$DATABASE_URL" -f infra/migrations/003_sarthi_stripped.sql`
- [ ] Create Go test: `apps/core/internal/db/migration_003_test.go`
- [ ] Run tests: `go test ./internal/db -run TestMigration003 -v`

**Exit Criteria:**
- Migration applied successfully
- All new tables/columns exist
- 2+ tests passing

#### 1B: Qdrant Collections

- [ ] Create `scripts/setup_qdrant_collections.py`
  - [ ] `finance_memory` collection (768-dim, nomic-embed-text)
  - [ ] `bi_memory` collection (768-dim)
- [ ] Run script: `uv run python scripts/setup_qdrant_collections.py`
- [ ] Verify collections: `curl http://localhost:6333/collections`

**Exit Criteria:**
- Both collections created
- Vector size = 768 (nomic-embed-text)

#### 1C: Redpanda Topics

- [ ] Create topics via Docker:
  ```bash
  docker exec sarthi-redpanda rpk topic create \
    sarthi.events.raw \
    sarthi.queries.raw \
    sarthi.agent.outputs \
    sarthi.dlq \
    --partitions 3 --replicas 1
  ```
- [ ] Verify topics: `docker exec sarthi-redpanda rpk topic list`

**Exit Criteria:**
- 4 topics created
- 3 partitions each

---

## Phase 2 🔲 — Finance Agent (LangGraph)

**Target:** 9-node ReAct graph, 14 unit tests passing

### Tasks

#### 2A: State Definition

- [ ] Create `apps/ai/src/agents/finance/state.py`
  - [ ] `FinanceState` TypedDict
  - [ ] All required fields: tenant_id, event, revenue, expense, burn, runway, etc.

#### 2B: DSPy Prompts

- [ ] Create `apps/ai/src/agents/finance/prompts.py`
  - [ ] `AnomalyExplainer` signature (input: event, vendor, amount, avg, score, past_context, runway)
  - [ ] `FinanceDigestWriter` signature (input: MRR, burn, runway, WoW%, top expenses)
  - [ ] Configure DSPy with Ollama: `dspy.LM(model="openai/qwen3:0.6b", api_base="http://localhost:11434/v1")`

#### 2C: Node Functions

- [ ] Create `apps/ai/src/agents/finance/nodes.py`
  - [ ] `node_ingest_event` — validate schema
  - [ ] `node_update_snapshot` — query PostgreSQL for burn/runway
  - [ ] `node_load_vendor_baseline` — load 90d avg
  - [ ] `node_detect_anomaly` — score-based rules
  - [ ] `node_query_memory` — Qdrant semantic search
  - [ ] `node_reason_and_explain` — DSPy ChainOfThought
  - [ ] `node_decide_action` — ALERT | DIGEST | SKIP
  - [ ] `node_write_memory` — Qdrant upsert
  - [ ] `node_emit_output` — format Telegram message
  - [ ] `route_after_decide` — conditional edge function

#### 2D: LangGraph Graph

- [ ] Create `apps/ai/src/agents/finance/graph.py`
  - [ ] Build `StateGraph(FinanceState)`
  - [ ] Add all 9 nodes
  - [ ] Set entry point
  - [ ] Add edges
  - [ ] Compile graph

#### 2E: Unit Tests

- [ ] Create `apps/ai/tests/unit/test_finance_nodes.py`
  - [ ] `test_ingest_event_normalizes_razorpay_payload`
  - [ ] `test_ingest_event_rejects_missing_fields`
  - [ ] `test_detect_anomaly_scores_2x_spend`
  - [ ] `test_detect_anomaly_scores_first_vendor`
  - [ ] `test_detect_anomaly_skips_normal_transaction`
  - [ ] `test_detect_anomaly_flags_low_runway`
  - [ ] `test_decide_action_alerts_on_high_score`
  - [ ] `test_decide_action_digests_on_weekly_tick`
  - [ ] `test_decide_action_skips_on_low_score`
  - [ ] `test_update_snapshot_calculates_burn` (mocked PostgreSQL)
  - [ ] `test_update_snapshot_calculates_runway` (mocked PostgreSQL)
  - [ ] `test_load_vendor_baseline_returns_90d_avg`
  - [ ] `test_write_memory_payload_has_required_fields`
  - [ ] `test_reason_and_explain_returns_non_empty_string`

**Exit Criteria:**
- Graph compiles without errors
- 14/14 unit tests PASS
- No banned jargon in output strings

---

## Phase 3 🔲 — BI Agent (LangGraph)

**Target:** 9-node ReAct graph, 10 unit tests passing

### Tasks

#### 3A: State Definition

- [ ] Create `apps/ai/src/agents/bi/state.py`
  - [ ] `BIState` TypedDict
  - [ ] All fields: tenant_id, query, query_type, generated_sql, sql_result, chart_path, narrative, etc.

#### 3B: DSPy Prompts

- [ ] Create `apps/ai/src/agents/bi/prompts.py`
  - [ ] `TextToSQL` signature (input: question, schema, sample_rows, time_hint)
  - [ ] `NarrativeWriter` signature (input: question, sql_result, past_answer)
  - [ ] `PlotlyCodeGen` signature (input: chart_type, data_json, title, chart_path)

#### 3C: Node Functions

- [ ] Create `apps/ai/src/agents/bi/nodes.py`
  - [ ] `node_understand_query` — classify + check Qdrant cache
  - [ ] `node_generate_sql` — DSPy TextToSQL + sanitize
  - [ ] `node_execute_sql` — PostgreSQL execution + retry logic
  - [ ] `node_decide_visualization` — choose chart type
  - [ ] `node_generate_chart` — Plotly code gen + sandboxed exec
  - [ ] `node_generate_narrative` — DSPy NarrativeWriter
  - [ ] `node_write_bi_memory` — Qdrant + PostgreSQL write
  - [ ] `node_emit_bi_output` — format Telegram message

#### 3D: LangGraph Graph

- [ ] Create `apps/ai/src/agents/bi/graph.py`
  - [ ] Build `StateGraph(BIState)`
  - [ ] Add all 8 nodes
  - [ ] Set entry point
  - [ ] Add edges
  - [ ] Compile graph

#### 3E: Unit Tests

- [ ] Create `apps/ai/tests/unit/test_bi_nodes.py`
  - [ ] `test_understand_query_classifies_revenue_query`
  - [ ] `test_understand_query_classifies_trend_query`
  - [ ] `test_generate_sql_sanitize_rejects_insert`
  - [ ] `test_generate_sql_sanitize_rejects_drop`
  - [ ] `test_generate_sql_allows_select`
  - [ ] `test_decide_viz_line_for_trend`
  - [ ] `test_decide_viz_bar_for_breakdown`
  - [ ] `test_decide_viz_none_for_empty_result`
  - [ ] `test_execute_sql_returns_rows` (mocked)
  - [ ] `test_execute_sql_retries_on_syntax_error`

**Exit Criteria:**
- Graph compiles without errors
- 10/10 unit tests PASS
- SQL sanitizer rejects INSERT/UPDATE/DELETE/DROP

---

## Phase 4 🔲 — Temporal Workflows (Go)

**Target:** FinanceWorkflow + BIWorkflow with HITL signals

### Tasks

#### 4A: Finance Workflow

- [ ] Create `apps/core/internal/workflow/finance_workflow.go`
  - [ ] `FinanceWorkflowInput` struct
  - [ ] `AgentOutput` struct
  - [ ] `FinanceWorkflow` function
  - [ ] Activity options with retry policy
  - [ ] Execute `RunFinanceAgentActivity`
  - [ ] Send Telegram with HITL buttons if anomaly
  - [ ] HITL signal handler: `FinanceHITLWorkflow`

#### 4B: BI Workflow

- [ ] Create `apps/core/internal/workflow/bi_workflow.go`
  - [ ] `BIWorkflowInput` struct
  - [ ] `BIOutput` struct
  - [ ] `BIWorkflow` function
  - [ ] Execute `RunBIAgentActivity`
  - [ ] Send Telegram with chart (if generated)
  - [ ] Proactive weekly insight function

#### 4C: Workflow Tests

- [ ] Create `apps/core/internal/workflow/finance_workflow_test.go`
  - [ ] `TestFinanceWorkflow_CompletesSuccessfully`
  - [ ] `TestFinanceWorkflow_SendsTelegramOnAlert`
  - [ ] `TestFinanceWorkflow_SkipsOnLowScore`
- [ ] Create `apps/core/internal/workflow/bi_workflow_test.go`
  - [ ] `TestBIWorkflow_CompletesSuccessfully`
  - [ ] `TestBIWorkflow_SendsChart`
  - [ ] `TestBIWorkflow_CachesIdenticalQuery`

**Exit Criteria:**
- Both workflows compile
- 6+ Go tests PASS
- HITL signal handler registered

---

## Phase 5 🔲 — Python Temporal Worker

**Target:** Activity worker running LangGraph agents

### Tasks

#### 5A: Worker Setup

- [ ] Create `apps/ai/src/worker.py`
  - [ ] Temporal client connection
  - [ ] Task queue: `AI_TASK_QUEUE`
  - [ ] Register activities

#### 5B: Activities

- [ ] Create `apps/ai/src/activities/run_finance_agent.py`
  - [ ] `@activity.defn(name="RunFinanceAgentActivity")`
  - [ ] Deserialize input
  - [ ] Invoke `finance_graph.invoke(initial_state)`
  - [ ] Return `AgentOutput` dict
- [ ] Create `apps/ai/src/activities/run_bi_agent.py`
  - [ ] `@activity.defn(name="RunBIAgentActivity")`
  - [ ] Invoke `bi_graph.invoke(initial_state)`
  - [ ] Return `BIOutput` dict
- [ ] Create `apps/ai/src/activities/upsert_qdrant.py`
  - [ ] `@activity.defn(name="UpsertQdrantActivity")`
  - [ ] Call `upsert_memory()`
- [ ] Create `apps/ai/src/activities/execute_code.py`
  - [ ] `@activity.defn(name="ExecuteCodeActivity")`
  - [ ] Sandboxed subprocess execution
  - [ ] Timeout: 30 seconds

#### 5C: Services

- [ ] Create `apps/ai/src/services/langfuse_client.py`
  - [ ] `get_langfuse()` singleton
  - [ ] No-op fallback if unconfigured
- [ ] Create `apps/ai/src/services/postgres_client.py`
  - [ ] `get_postgres_conn()` context manager
  - [ ] Read-only connection for BI agent

**Exit Criteria:**
- Worker starts successfully
- All 4 activities registered
- Can invoke activities via Temporal UI

---

## Phase 6 🔲 — Integration + Cross-Agent

**Target:** Finance anomaly → BI query trigger

### Tasks

#### 6A: Cross-Agent Trigger

- [ ] Update `apps/ai/src/agents/finance/nodes.py`
  - [ ] In `node_decide_action`: if ALERT, set `trigger_bi_query=True`
  - [ ] In `node_emit_output`: include BI query suggestion
- [ ] Update `apps/core/internal/workflow/finance_workflow.go`
  - [ ] After FinanceWorkflow completes, check `trigger_bi_query`
  - [ ] If true: spawn child BIWorkflow with vendor breakdown query

#### 6B: HITL Callbacks

- [ ] Create `apps/core/internal/api/hitl.go`
  - [ ] `POST /internal/hitl/investigate`
  - [ ] `POST /internal/hitl/dismiss`
  - [ ] Signal Temporal workflow with trace_id
- [ ] Update Qdrant memory on dismiss
  - [ ] Add `founder_dismissed: true` to memory payload
  - [ ] Raise future anomaly threshold for this vendor

#### 6C: Memory Compounding Tests

- [ ] Create `apps/ai/tests/e2e/test_memory_compounds.py`
  - [ ] `test_qdrant_memory_compounds` — second anomaly returns past_context
  - [ ] `test_dismissed_anomaly_raises_threshold` — future score lower

**Exit Criteria:**
- Finance anomaly triggers BI query
- HITL buttons work (Investigate/Dismiss)
- Memory compounding verified

---

## Phase 7 🔲 — E2E Tests

**Target:** 8+ E2E tests with real services (no mocks)

### Tasks

#### 7A: Finance E2E

- [ ] Create `apps/ai/tests/e2e/test_finance_e2e.py`
  - [ ] `test_infra_health` — all containers reachable
  - [ ] `test_finance_anomaly_detection` — full flow, anomaly detected
  - [ ] `test_qdrant_memory_written_after_alert` — memory exists
  - [ ] `test_memory_compounds_on_second_anomaly` — past_context populated

#### 7B: BI E2E

- [ ] Create `apps/ai/tests/e2e/test_bi_e2e.py`
  - [ ] `test_bi_adhoc_query_full_flow` — NL → SQL → narrative → Qdrant
  - [ ] `test_same_query_returns_cached_memory` — second query uses cache
  - [ ] `test_bi_query_written_to_postgres` — bi_queries row exists

#### 7C: Weekly Digest E2E

- [ ] Create `apps/ai/tests/e2e/test_weekly_digest.py`
  - [ ] `test_weekly_digest_full_flow` — cron trigger → combined digest

**Exit Criteria:**
- 8+ E2E tests PASS
- No mocks for PostgreSQL, Qdrant, Ollama
- All tests run in <10 minutes

---

## Phase 8 🔲 — LLM Evals (DSPy + Langfuse)

**Target:** 3 eval sets with >80% accuracy

### Tasks

#### 8A: Anomaly Explanation Eval

- [ ] Create `apps/ai/tests/evals/test_anomaly_explanation.py`
  - [ ] 20 scripted scenarios + gold narratives
  - [ ] Metrics: correctness, no hallucination, <60 words
  - [ ] Target: >80% pass rate
- [ ] Log to Langfuse with before/after DSPy compile

#### 8B: Text-to-SQL Eval

- [ ] Create `apps/ai/tests/evals/test_text_to_sql.py`
  - [ ] 15 NL queries + gold SQL
  - [ ] Metrics: SQL valid, correct row count, column match
  - [ ] Target: >85% pass rate

#### 8C: BI Narrative Eval

- [ ] Create `apps/ai/tests/evals/test_bi_narrative.py`
  - [ ] 10 SQL results + gold narratives
  - [ ] Metrics: data grounded, no hallucination, actionable
  - [ ] Target: >75% pass rate

**Exit Criteria:**
- All 3 eval sets running
- Scores logged to Langfuse
- DSPy compile improves scores

---

## Phase 9 🔲 — Production Polish

**Target:** Deploy-ready, portfolio-ready

### Tasks

#### 9A: Docker Compose Production

- [ ] Create `infra/docker-compose.prod.yml`
  - [ ] Hetzner-optimized config
  - [ ] Resource limits
  - [ ] Health checks
  - [ ] Persistent volumes

#### 9B: Smoke Test Script

- [ ] Create `scripts/smoke_test.sh`
  - [ ] `GET /health` → 200
  - [ ] PostgreSQL connection
  - [ ] Qdrant collections exist
  - [ ] Ollama models available
  - [ ] Simulate payment → full flow
  - [ ] Langfuse trace visible

#### 9C: Documentation

- [ ] Update `README.md` with:
  - [ ] Architecture diagram
  - [ ] Quick start guide
  - [ ] Test results
  - [ ] Demo script
- [ ] Create `docs/DEMO_SCRIPT.md` with 3-minute walkthrough
- [ ] Screenshot Langfuse dashboard

#### 9D: Go Tests

- [ ] Ensure 5+ webhook handler tests passing
- [ ] Run invariant checks before commit

**Exit Criteria:**
- `smoke_test.sh` all green
- README complete with test results
- Langfuse dashboard screenshot ready

---

## Phase 10 🔲 — htmx Dashboard (Optional)

**Target:** Admin UI for monitoring

### Tasks

#### 10A: Go Templates

- [ ] Create `apps/core/web/templates/dashboard.html`
  - [ ] Finance agent status
  - [ ] BI query history
  - [ ] Qdrant memory browser
- [ ] Create `apps/core/internal/api/dashboard.go`
  - [ ] `GET /` — dashboard home
  - [ ] `GET /finance` — finance status
  - [ ] `GET /bi` — BI history
  - [ ] `GET /memory` — memory browser

#### 10B: SSE Live Feed

- [ ] Add Server-Sent Events endpoint
- [ ] Stream live agent outputs
- [ ] Auto-refresh every 5 seconds

**Exit Criteria:**
- Dashboard accessible at `localhost:8080`
- Live feed working
- Screenshot for portfolio

---

## Invariant Checks (Run Before EVERY Commit)

```bash
# I-1: No raw JSON marshal in workflow/
grep -rn "json.Marshal\|json.Unmarshal" apps/core/internal/workflow/ \
  | grep -v "_test.go" | grep -v "// safe:" \
  && echo "FAIL I-1" && exit 1 || true

# I-2: No direct AzureOpenAI() outside config/llm.py
grep -rn "AzureOpenAI(" apps/ai/src/ | grep -v "config/llm.py" \
  && echo "FAIL I-2" && exit 1 || true

# I-3: All existing tests still pass
cd apps/core && go test ./... -timeout=60s -q && cd -
cd apps/ai && uv run pytest tests/ -x -q --timeout=90 && cd -

# I-4: No banned jargon in agent output strings
grep -rn "leverage\|synergy\|utilize\|streamline\|paradigm" \
  apps/ai/src/agents/ | grep -v "# allowed:" \
  && echo "FAIL I-4" && exit 1 || true

echo "✓ All invariants pass"
```

---

## Test Count Summary

| Phase | Target | Cumulative | Status |
|-------|--------|------------|--------|
| Phase 0 | Baseline | 255 | ✅ COMPLETE |
| Phase 1 | 2 tests | 257 | 🔲 Pending |
| Phase 2 | 14 tests | 271 | 🔲 Pending |
| Phase 3 | 10 tests | 281 | 🔲 Pending |
| Phase 4 | 6 tests | 287 | 🔲 Pending |
| Phase 5 | 0 tests | 287 | 🔲 Pending |
| Phase 6 | 2 tests | 289 | 🔲 Pending |
| Phase 7 | 8 tests | 297 | 🔲 Pending |
| Phase 8 | 3 evals | 300 | 🔲 Pending |
| Phase 9 | 5 tests | 305 | 🔲 Pending |
| Phase 10 | 0 tests | 305 | 🔲 Optional |

**Target:** 300+ tests passing for v1.0.0-alpha

---

## Definition of Done (v1.0.0-alpha)

```
WEEK 1 — Finance Agent:
  ✅ Migration 003 applied
  ✅ Qdrant: finance_memory collection
  ✅ LangGraph finance graph: 9 nodes compiling
  ✅ Finance unit tests: 14 passing
  ✅ E2E: anomaly detected, Qdrant written, memory compounds
  ✅ DSPy AnomalyExplainer wired to Ollama

WEEK 2 — BI Agent:
  ✅ LangGraph BI graph: 9 nodes compiling
  ✅ SQL sanitizer rejects INSERT/DROP
  ✅ BI unit tests: 10 passing
  ✅ E2E: NL → SQL → result → narrative → Qdrant cached
  ✅ Second identical query hits Qdrant cache

WEEK 3 — Integration:
  ✅ Finance anomaly → triggers BI agent (cross-agent)
  ✅ HITL: [Investigate] → BIWorkflow with vendor query
  ✅ HITL: [Dismiss] → Qdrant memory updated
  ✅ Monday weekly digest cron working
  ✅ DSPy: compile finance + BI prompts
  ✅ LLM evals: all 3 eval sets running in Langfuse

WEEK 4 — Production:
  ✅ docker-compose.prod.yml for Hetzner
  ✅ Go tests: 5+ webhook handler tests passing
  ✅ Python tests: 40+ unit + 8 E2E passing
  ✅ smoke_test.sh all green
  ✅ README.md: architecture + demo flow + test results
  ✅ Langfuse dashboard screenshot for portfolio
  ✅ 3-minute demo video recorded

BLOCKED IF:
  ✗ Any E2E uses a mock for PostgreSQL, Qdrant, or Ollama
  ✗ SQL generator produces INSERT/UPDATE/DELETE
  ✗ Agent output contains banned jargon
  ✗ AzureOpenAI() called anywhere outside config/llm.py
  ✗ Any new Docker image pulled
```

---

## Current Status

**Phase:** 0 (COMPLETE ✅)

**Next:** Phase 1 — Infrastructure Setup

**Target:** Migration 003, Qdrant collections, Redpanda topics

---

**Document Version:** 1.0  
**Last Updated:** March 21, 2026  
**Status:** Phase 0 COMPLETE — Ready for Phase 1
