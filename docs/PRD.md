# Sarthi — Product Requirements Document
## Version 1.0 | Portfolio Build + Future Product

**Last Updated:** March 21, 2026  
**Status:** Ready for implementation

---

## Table of Contents

```
├── 1. Executive Summary
├── 2. Problem Statement
├── 3. Solution Overview
├── 4. Target Users & ICP
├── 5. Agent Specifications
│   ├── 5.1 Finance Agent
│   └── 5.2 BI Agent
├── 6. System Architecture
├── 7. Low-Level Design
├── 8. Workflows & SOP
├── 9. Test Strategy
├── 10. Build Checklist
├── 11. Metrics & KPIs
└── 12. Timeline + Demo Script
```

---

## 1. Executive Summary

**Sarthi** is an ops memory layer for software startup founders. Two agents only: **Finance Monitor** + **BI Agent**. Everything else is cut for speed.

| Differentiator | Detail |
|---|---|
| **2 focused agents** | Finance + BI — scoped, not bloated |
| **Qdrant episodic memory** | Context compounds with every event |
| **Temporal durable workflows** | Survives crashes, restarts, failures |
| **LangGraph ReAct** | Not just automation — actual decisions |
| **Go + Python polyglot** | Right language for each job |
| **Langfuse observability** | Every LLM call traced and scored |
| **DSPy compiled prompts** | Systematic, not hand-tuned |
| **HITL via Telegram** | Human approves escalations, agent learns |

**Portfolio Goal:** Production-grade agentic AI SaaS demonstrating 9+ technologies.  
**Product Goal:** Virtual ops brain for software startups (2–20 people) at ₹9,999/month.

---

## 2. Problem Statement

Every software startup that reaches ₹50L ARR hits the same wall — **context evaporation**. Knowledge lives in the founder's head. When they scale, hire, or burn out, deals fall through, anomalies go unnoticed, and bad decisions compound silently.

**The specific acute pain:**
- "Our AWS bill doubled and I found out 3 weeks later."
- "I don't know our exact runway right now."
- "Why did revenue dip in March? I have no idea."
- "That deal went cold and I forgot to follow up."

**What exists today and why it fails:**

| Tool | Problem |
|---|---|
| Tableau / Looker | Requires a data team, nobody maintains it |
| PagerDuty alerts | Fire without context or memory of the past |
| HubSpot CRM | Manually updated, always stale |
| Excel runway models | Static, disconnected from live data |

**The gap:** No system exists that watches your data continuously, reasons about anomalies with memory of the past, answers natural language questions about your business, and gets smarter with every event — at a price below one junior hire.

---

## 3. Solution Overview

**Core flow:**
```
External Event (payment / expense / NL query)
  → Go Webhook (HMAC validated)
    → Redpanda (event bus)
      → Temporal Workflow (durable)
        → LangGraph Agent (ReAct reasoning)
          → Tools (PostgreSQL + Qdrant + code exec)
            → Output (Telegram alert / chart / answer)
              → Qdrant Memory (written back, compounds)
```

**Two agents, one system:**

| Agent | Watches | Does | Output |
|-------|---------|------|--------|
| **Finance** | Razorpay, bank feed, expenses | Burn/runway tracking, anomaly detection, spend pattern memory | Telegram alerts + weekly digest |
| **BI** | PostgreSQL, Sheets, GA4, Mixpanel | NL → SQL → chart → narrative, proactive insights | Charts + narrative + Telegram |

**Cross-agent trigger:** Finance anomaly detected → BI Agent auto-queries "break down this cost" → combined alert: anomaly + chart + causal context.

**Value delivered:**

| Metric | Before | After |
|---|---|---|
| Anomaly detection | 3 weeks (if ever) | < 5 minutes |
| Runway accuracy | Monthly manual calc | Real-time |
| BI query time | 2–4 hrs (analyst) | < 30 seconds |
| Context on alerts | None | Episodic memory |
| Weekly digest | Manual assembly | Auto-generated |
| Cost | ₹50,000+/month (human) | ₹9,999/month |

---

## 4. Target Users & ICP

**Primary ICP:**
- **Who:** Software startup founder
- **Stage:** Seed to Series A (₹50L – ₹10Cr ARR)
- **Size:** 2–20 employees
- **Type:** B2B SaaS, B2C app, D2C, marketplace
- **Pain:** No dedicated analyst or finance ops person
- **Budget:** Already spending ₹15k–₹50k/month on equivalent human work

| Persona | Core Pain |
|---|---|
| Solo founder | Wears all hats, no time for analysis |
| Technical CTO | Has data but no pipeline to insights |
| D2C operator | Revenue lumpy, expenses hard to track |
| B2B SaaS CEO | Needs investor-ready metrics instantly |

---

## 5. Agent Specifications

### 5.1 Finance Agent

**Purpose:** Continuously monitors financial events. Detects anomalies. Tracks burn and runway. Remembers context. Alerts with explanation.

**Input event types:**

| Event | Source |
|---|---|
| `PAYMENT_SUCCESS` | Razorpay webhook |
| `PAYMENT_REFUND` | Razorpay webhook |
| `SUBSCRIPTION_CREATED` | Razorpay webhook |
| `SUBSCRIPTION_CANCELED` | Razorpay webhook |
| `EXPENSE_RECORDED` | Bank webhook / manual |
| `BANK_TRANSACTION` | Bank feed webhook |
| `TIME_TICK_DAILY` | Temporal cron 9 AM IST |
| `TIME_TICK_WEEKLY` | Temporal cron Mon 9 AM |

**LangGraph State:**
```python
class FinanceState(TypedDict):
    tenant_id:            str
    event:                dict
    monthly_revenue:      float
    monthly_expense:      float
    burn_rate:            float
    runway_months:        float
    vendor_baselines:     dict  # vendor → 90d avg
    anomaly_detected:     bool
    anomaly_score:        float  # 0.0 – 1.0
    anomaly_explanation:  str
    past_context:         list  # from Qdrant
    action:               str   # ALERT | DIGEST | SKIP
    output_message:       str
```

**LangGraph Nodes (ReAct loop):**

```
1. INGEST_EVENT       → Validate schema, normalize, classify
2. UPDATE_SNAPSHOT    → Query PostgreSQL: revenue, expense, burn, runway
3. LOAD_VENDOR_BASELINE → IF expense: query 90d avg for this vendor
4. DETECT_ANOMALY     → Score-based rules (spike, first-time, runway)
5. QUERY_MEMORY       → Qdrant: "similar anomaly for {vendor}"
6. REASON_AND_EXPLAIN → LLM (DSPy): 1–3 sentence explanation
7. DECIDE_ACTION      → ALERT (>0.7) | DIGEST (weekly) | SKIP
8. WRITE_MEMORY       → Qdrant: event + explanation + outcome
9. EMIT_OUTPUT        → Telegram alert or weekly digest
```

**HITL Flow:**
```
Founder taps [Investigate]
  → Temporal signal fires
    → BI Agent triggered: "Break down {vendor} costs"
      → Chart + breakdown returned to Telegram

Founder taps [Dismiss]
  → Qdrant updated: "founder dismissed — not anomalous"
  → Future anomaly_score threshold raised for this vendor
```

---

### 5.2 BI Agent

**Purpose:** Answers natural language questions about business data. Proactively surfaces insights on a schedule. Executes SQL and Python safely. Remembers past queries and answers.

**Inputs:**

| Input | Trigger |
|---|---|
| `NL_QUERY` | Telegram message / API call |
| `TIME_TICK_WEEKLY` | Monday proactive insight |
| `FINANCE_ANOMALY` | Cross-agent trigger from Finance |

**LangGraph State:**
```python
class BIState(TypedDict):
    tenant_id:      str
    query:          str  # natural language
    query_type:     str  # ADHOC | SCHEDULED | TRIGGERED
    data_sources:   list
    generated_sql:  str
    sql_result:     dict
    generated_code: str  # Plotly Python
    chart_path:     str  # PNG path
    past_queries:   list  # from Qdrant
    narrative:      str
    output_message: str
```

**LangGraph Nodes (ReAct loop):**

```
1. UNDERSTAND_QUERY    → Classify: aggregation/trend/breakdown
2. SELECT_DATASOURCE   → Revenue → payments, Users → users table
3. GENERATE_SQL        → LLM (DSPy): NL → SQL
4. EXECUTE_SQL         → PostgreSQL (read-only), retry on error
5. DECIDE_VISUALIZATION → line/bar/pie/text based on query type
6. GENERATE_CODE       → Plotly Python in sandboxed subprocess
7. GENERATE_NARRATIVE  → LLM (DSPy): 2–4 sentence plain English
8. WRITE_MEMORY        → Qdrant: query + SQL + narrative
9. EMIT_OUTPUT         → Telegram with chart + narrative
```

**Proactive Monday Queries (auto-run weekly):**
1. "How did revenue change this week vs last week?"
2. "What are the top 3 expense categories this month?"
3. "Which user cohort has the lowest 7-day retention?"

---

## 6. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   EXTERNAL TRIGGERS                          │
│  Razorpay ──┐                                               │
│  Bank Feed ─┼──→ Go Fiber API ──→ Redpanda ──→ Temporal    │
│  Telegram  ─┘  (HMAC Validated)  (Event Bus)  (Workflows)  │
└─────────────────────────────────────────────────────────────┘
                                              │
                       ┌──────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 PYTHON AI WORKER                             │
│                                                             │
│  Temporal Activity: RunLangGraphAgent(agent, event)         │
│               │                                             │
│      ┌────────┴────────┐                                   │
│      ▼                 ▼                                   │
│  FinanceAgent      BIAgent                                  │
│  (LangGraph)       (LangGraph)                              │
│      │                 │                                   │
│  PostgreSQL         PostgreSQL                              │
│  Qdrant             Qdrant                                  │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  OUTPUT LAYER                                │
│  Telegram ← alerts, charts, digests, HITL buttons          │
│  Langfuse  ← all LLM traces, scores, costs                 │
│  htmx UI   ← admin dashboard (Week 5, optional)            │
└─────────────────────────────────────────────────────────────┘
```

**Tech Stack:**

| Layer | Technology | Why |
|---|---|---|
| API Gateway | Go + Fiber | High concurrency, low latency |
| Event Bus | Redpanda | Kafka-compatible, persistent |
| Workflow Engine | Temporal | Durable execution, HITL signals |
| Agent Framework | LangGraph (Python) | ReAct graphs, state machines |
| LLM | Ollama (qwen3:0.6b) | Local, no API keys, fast |
| Prompt Compiler | DSPy | Systematic, not hand-tuned |
| Memory | Qdrant | Semantic + episodic search |
| Primary DB | PostgreSQL + sqlc | Type-safe queries |
| Observability | Langfuse | LLM trace + eval scoring |
| Notifications | Telegram Bot API | Zero-friction HITL |
| Charts | Plotly Python | Code-executed, shareable PNG |
| Deploy | Docker Compose | Local dev + Hetzner |

**Polyglot split:**

| Language | Owns |
|---|---|
| Go | Webhook ingestion, Redpanda producer, Temporal workflow definitions, Telegram activity, htmx dashboard |
| Python | Temporal activity worker, LangGraph graphs, Qdrant read/write, SQL execution, chart generation, DSPy, Langfuse |

---

## 7. Low-Level Design

### 7.1 Repo Structure

```
sarthi/
├── apps/
│   ├── core/                      # Go Modular Monolith
│   │   ├── cmd/
│   │   │   ├── server/            # HTTP server entrypoint
│   │   │   └── worker/            # Temporal Go worker
│   │   ├── internal/
│   │   │   ├── api/               # Webhook handlers
│   │   │   ├── config/            # Config management
│   │   │   ├── db/                # sqlc generated queries
│   │   │   ├── redpanda/          # franz-go producer
│   │   │   ├── temporal/          # Temporal SDK wrapper
│   │   │   ├── telegram/          # Bot send activity
│   │   │   └── workflow/          # Workflow definitions
│   │   ├── web/templates/         # htmx admin dashboard
│   │   ├── go.mod
│   │   └── Dockerfile
│   │
│   └── ai/                        # Python AI Worker
│       ├── src/
│       │   ├── worker.py          # Temporal activity worker
│       │   ├── agents/
│       │   │   ├── finance/
│       │   │   │   ├── graph.py   # LangGraph definition
│       │   │   │   ├── nodes.py   # All node functions
│       │   │   │   ├── state.py   # FinanceState TypedDict
│       │   │   │   └── prompts.py # DSPy signatures
│       │   │   └── bi/
│       │   │       ├── graph.py
│       │   │       ├── nodes.py
│       │   │       ├── state.py
│       │   │       └── prompts.py
│       │   ├── activities/
│       │   │   ├── run_finance_agent.py
│       │   │   ├── run_bi_agent.py
│       │   │   ├── query_postgres.py
│       │   │   ├── upsert_qdrant.py
│       │   │   └── execute_code.py
│       │   └── services/
│       │       ├── qdrant_client.py
│       │       ├── postgres_client.py
│       │       └── langfuse_client.py
│       ├── tests/
│       │   ├── unit/
│       │   ├── e2e/
│       │   └── evals/
│       ├── pyproject.toml
│       └── Dockerfile
│
├── infra/
│   ├── docker-compose.yml         # Local dev stack
│   ├── docker-compose.prod.yml    # Hetzner production
│   └── migrations/                # SQL migrations
│
├── scripts/
│   ├── simulate_payment.sh        # Fake Razorpay event
│   ├── simulate_query.sh          # Fake BI query
│   ├── smoke_test.sh              # Post-deploy check
│   └── seed_data.sql              # Demo data
│
└── docs/
    ├── prd.md
    ├── adr/
    └── demo_script.md
```

---

### 7.2 Database Schema

```sql
-- Tenants
CREATE TABLE tenants (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- All financial transactions (normalized)
CREATE TABLE transactions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID REFERENCES tenants(id),
  vendor      TEXT,
  amount      NUMERIC(12,2) NOT NULL,
  currency    TEXT DEFAULT 'INR',
  type        TEXT,        -- REVENUE | EXPENSE | REFUND
  source      TEXT,        -- razorpay | bank | manual
  raw_payload JSONB,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Vendor spend baselines (rolling 90-day)
CREATE TABLE vendor_baselines (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID REFERENCES tenants(id),
  vendor            TEXT NOT NULL,
  avg_30d           NUMERIC(12,2),
  avg_90d           NUMERIC(12,2),
  transaction_count INT,
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(tenant_id, vendor)
);

-- Agent output audit log
CREATE TABLE agent_outputs (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID REFERENCES tenants(id),
  agent          TEXT,    -- finance | bi
  trigger_type   TEXT,
  input_payload  JSONB,
  output_message TEXT,
  anomaly_score  FLOAT,
  action_taken   TEXT,    -- ALERT | DIGEST | SKIP
  langfuse_trace TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- BI query history
CREATE TABLE bi_queries (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID REFERENCES tenants(id),
  query_text    TEXT NOT NULL,
  generated_sql TEXT,
  row_count     INT,
  chart_path    TEXT,
  narrative     TEXT,
  qdrant_id     TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 7.3 API Endpoints

```
WEBHOOKS (Go — HMAC validated):
  POST  /webhooks/razorpay          Razorpay payment events
  POST  /webhooks/bank              Bank transaction feed
  POST  /webhooks/telegram          Incoming Telegram messages
  POST  /webhooks/manual-expense    Manual expense entry

INTERNAL (HITL signals → Temporal):
  POST  /internal/hitl/investigate  Founder tapped Investigate
  POST  /internal/hitl/dismiss      Founder tapped Dismiss
  POST  /internal/query             Direct BI query (API/UI)

ADMIN (Go + htmx):
  GET   /                           Dashboard home
  GET   /finance                    Finance agent status
  GET   /bi                         BI query history
  GET   /memory                     Qdrant memory browser

HEALTH:
  GET   /health                     Infra health check
  GET   /metrics                    Prometheus metrics
```

---

### 7.4 Qdrant Collections

**`finance_memory`**
- Vector: 1536-dim (nomic-embed-text via Ollama)
- Payload: `tenant_id`, `event_type`, `vendor`, `amount`, `anomaly_score`, `explanation`, `action_taken`, `date`
- Use: "what happened last time this vendor spiked?"

**`bi_memory`**
- Vector: 1536-dim
- Payload: `tenant_id`, `query_text`, `sql`, `narrative`, `metric`, `date`
- Use: "has this been asked before?" → return cached + diff

---

## 8. Workflows & SOP

### Workflow 1 — Finance Anomaly (end-to-end)

```
Razorpay fires webhook
  → Go validates HMAC → FAIL: 401 stop | PASS: continue
  → Normalize to InternalEvent{tenant_id, type, payload}
  → Publish to Redpanda: sarthi.events.raw
  → Temporal FinanceWorkflow starts
    → RunLangGraphFinanceAgent(event)
      → 9-node ReAct loop executes
    → SendTelegram(output_message)
      → IF ALERT: [Investigate][Dismiss] buttons
    → UpsertQdrant(memory_payload)
    → LogToPostgres(agent_output)
  → Founder receives alert < 5 minutes

  IF [Investigate] tapped:
    → /internal/hitl/investigate → Temporal signal
    → BIWorkflow: "Break down {vendor} costs 30d"
    → Chart + narrative → Telegram < 30 seconds

  IF [Dismiss] tapped:
    → Qdrant updated: "dismissed — not anomalous"
    → Future score threshold raised for vendor
```

### Workflow 2 — BI Adhoc Query

```
Founder: "What was our MRR last month by plan?"
  → Telegram webhook → Redpanda: sarthi.queries.raw
  → Temporal BIWorkflow starts
    → RunLangGraphBIAgent(query)
      → 9-node ReAct loop executes
    → SendTelegramWithChart(chart_png, narrative)
    → UpsertQdrant(bi_memory_payload)
  → Founder receives chart + narrative < 30 seconds
```

### Workflow 3 — Monday Weekly Digest

```
Temporal cron fires: Monday 9 AM IST
  ├── FinanceWorkflow (TIME_TICK_WEEKLY)
  │     → MRR, burn, runway WoW comparison
  │     → Draft finance digest
  └── BIWorkflow (TIME_TICK_WEEKLY)
        → Run 3 proactive queries
        → Bundle into Monday briefing
  → Combined Telegram message by 9:05 AM
```

---

## 9. Test Strategy

### Unit Tests (40+ target)

**Finance Agent nodes (14 tests):**
```
test_ingest_event_normalizes_razorpay_payload
test_ingest_event_rejects_unknown_event_type
test_update_snapshot_calculates_burn_correctly
test_update_snapshot_calculates_runway_correctly
test_load_vendor_baseline_returns_90d_avg
test_detect_anomaly_scores_2x_spend_correctly
test_detect_anomaly_scores_first_vendor_spike
test_detect_anomaly_skips_normal_transaction
test_detect_anomaly_flags_low_runway
test_reason_and_explain_returns_non_empty_string
test_decide_action_alerts_on_high_score
test_decide_action_digests_on_weekly_tick
test_decide_action_skips_on_low_score
test_write_memory_payload_has_required_fields
```

**BI Agent nodes (10 tests):**
```
test_understand_query_classifies_revenue_query
test_understand_query_classifies_trend_query
test_generate_sql_produces_valid_sql
test_generate_sql_handles_time_range_filter
test_execute_sql_returns_rows
test_execute_sql_retries_on_syntax_error
test_decide_visualization_line_for_timeseries
test_decide_visualization_bar_for_categorical
test_generate_narrative_references_data_values
test_write_memory_deduplicates_same_query
```

**Go webhook handlers (5+ tests):**
```
TestRazorpayWebhook_ValidHMAC_Returns200
TestRazorpayWebhook_InvalidHMAC_Returns401
TestRazorpayWebhook_PublishesToRedpanda
TestBankWebhook_NormalizesPayload
TestHealthEndpoint_Returns200
```

### E2E Tests (8+ target, real services — no mocks)

```
test_finance_anomaly_full_flow
  1. Seed 90 days baseline spend
  2. POST /webhooks/razorpay (2.3x vendor spike)
  3. Assert: Redpanda consumed, Temporal COMPLETED,
     anomaly_detected=True, Telegram sent,
     Qdrant doc written, PostgreSQL row created
  4. POST /internal/hitl/investigate
  5. Assert: BIWorkflow triggered, chart created,
     Telegram receives chart

test_bi_adhoc_query_full_flow
  1. Seed 6 months transactions
  2. Telegram: "What was MRR last month?"
  3. Assert: BIWorkflow COMPLETED, SQL valid,
     result > 0 rows, narrative has number,
     Qdrant written, second identical query cached

test_weekly_digest_full_flow
  1. Seed 4 weeks data
  2. Manual Temporal cron trigger
  3. Assert: digest + 3 proactive queries executed,
     combined Telegram sent with MRR/burn/runway

test_qdrant_memory_compounds
  1. Trigger AWS anomaly → dismiss
  2. Trigger same anomaly again
  3. Assert: past_context has "dismissed" entry,
     anomaly_score lower than first time

test_infra_health
  Temporal CONNECTED | Redpanda CONNECTED
  PostgreSQL CONNECTED | Qdrant CONNECTED
  Langfuse traces appearing
```

### LLM Evals (DSPy + Langfuse)

| Eval | Dataset | Metric | Target |
|---|---|---|---|
| Anomaly explanation quality | 20 scripted scenarios + gold narratives | Correctness, no hallucination, < 60 words | > 80% |
| Text-to-SQL accuracy | 15 NL queries + gold SQL | SQL valid, correct row count, column match | > 85% |
| BI narrative quality | 10 SQL results + gold narratives | Data grounded, no hallucination, actionable | > 75% |

All evals logged to Langfuse with input, output, expected, score, model, tokens, latency, and DSPy compile before/after comparison.

---

## 10. Build Checklist

### Week 1 — Finance Agent
- [ ] `docker-compose.yml` with Temporal, Redpanda, PostgreSQL, Qdrant
- [ ] Go Fiber: `POST /webhooks/razorpay` with HMAC validation
- [ ] Redpanda topic: `sarthi.events.raw`
- [ ] Temporal `FinanceWorkflow` skeleton
- [ ] Python worker: `RunLangGraphFinanceAgent` activity
- [ ] LangGraph `FinanceAgent`: all 9 nodes
- [ ] PostgreSQL migrations: 4 tables
- [ ] Qdrant: `finance_memory` collection created
- [ ] Telegram: anomaly alert with `[Investigate][Dismiss]`
- [ ] Langfuse: trace appearing per agent run
- [ ] `simulate_payment.sh` triggers full flow
- [ ] 14 finance node unit tests passing
- [ ] `test_finance_anomaly_full_flow` E2E passing

### Week 2 — BI Agent
- [ ] Redpanda topic: `sarthi.queries.raw`
- [ ] Telegram webhook routes NL query to `BIWorkflow`
- [ ] Temporal `BIWorkflow` skeleton
- [ ] Python worker: `RunLangGraphBIAgent` activity
- [ ] LangGraph `BIAgent`: all 9 nodes
- [ ] Read-only PostgreSQL connection for SQL execution
- [ ] Plotly chart generation in sandboxed subprocess
- [ ] Qdrant: `bi_memory` collection created
- [ ] `simulate_query.sh` triggers full flow
- [ ] 10 BI node unit tests passing
- [ ] `test_bi_adhoc_query_full_flow` E2E passing

### Week 3 — Integration + Memory
- [ ] Finance anomaly → triggers BI agent (cross-agent)
- [ ] `[Investigate]` → BIWorkflow with vendor query
- [ ] `[Dismiss]` → Qdrant memory updated
- [ ] `test_qdrant_memory_compounds` passing
- [ ] Monday weekly digest cron working
- [ ] `test_weekly_digest_full_flow` passing
- [ ] DSPy: compile finance + BI prompts
- [ ] LLM evals: all 3 eval sets running in Langfuse

### Week 4 — Production Polish
- [ ] `docker-compose.prod.yml` for Hetzner deploy
- [ ] Go tests: 5+ webhook handler tests passing
- [ ] Python tests: 40+ unit + 8 E2E passing
- [ ] `smoke_test.sh` all checks green
- [ ] `README.md`: architecture + demo flow + test results
- [ ] Langfuse dashboard screenshot for portfolio
- [ ] 3-minute demo video recorded
- [ ] GitHub: public repo, proper `.gitignore`
- [ ] LinkedIn post drafted

### Week 5 (Optional) — htmx Dashboard
- [ ] Go templates: finance + BI + memory pages
- [ ] SSE: live agent output feed
- [ ] Screenshot for portfolio README

---

## 11. Metrics & KPIs

**Portfolio metrics (what gets you hired):**

| Metric | Target |
|---|---|
| Unit tests passing | 40+ |
| E2E tests passing | 8+ (real services, no mocks) |
| LLM eval sets | 3 (with before/after DSPy scores) |
| Technologies demonstrated | 9 |
| Demo duration | < 3 minutes, no setup |
| Deploy | Live on Hetzner, real URL |
| Observability | Langfuse dashboard with real traces |

**Technical metrics:**

| Metric | Target |
|---|---|
| Finance alert latency | < 5 min from webhook to Telegram |
| BI query latency | < 30 seconds from query to chart |
| SQL accuracy (eval set) | > 85% |
| Anomaly precision (eval set) | > 80% |
| Memory recall | > 70% relevant context returned |

---

## 12. Timeline

| Week | Dates | Deliverable |
|---|---|---|
| 1 | Mar 21–27 | Finance Agent end-to-end |
| 2 | Mar 28–Apr 3 | BI Agent end-to-end |
| 3 | Apr 4–10 | Cross-agent integration + memory |
| 4 | Apr 11–17 | Production deploy + portfolio polish |
| 5 | Apr 18–24 | htmx dashboard (optional) |
| 6 | Apr 25+ | User interviews → productization decision |

---

## Appendix: 3-Minute Demo Script

```
[0:00] "Sarthi is a multi-agent agentic AI system — the
        ops memory brain for software startups."

[0:20] Run: ./scripts/simulate_payment.sh
       "Just fired a fake Razorpay webhook —
        AWS bill 2.3x higher than the 90-day baseline."

[0:35] Open Temporal UI → FinanceWorkflow RUNNING
       "Temporal ensures this survives any crash.
        Durable execution — not a cron job."

[0:50] "LangGraph ReAct loop: Ingest → Load baseline
        → Detect anomaly → Query Qdrant → Reason → Alert"

[1:10] Show Qdrant returning memory:
       "Similar AWS spike. October 2025.
        Cause: undeleted staging environment."
       "It didn't just detect it — it remembered."

[1:30] Show Telegram alert:
       "AWS bill 2.3x usual. First spike since October.
        Check recent deployments. [Investigate][Dismiss]"

[1:50] Tap [Investigate]
       "Temporal receives the signal. BI Agent activates.
        Generates SQL, executes it, builds a chart."
       Show chart arriving in Telegram (< 30 seconds)

[2:20] Open Langfuse:
       "Every LLM call traced: input, output, tokens,
        latency, score. Production observability."

[2:45] "Two agents. Nine technologies.
        Temporal durable workflows. LangGraph ReAct.
        Qdrant episodic memory. Deployed. Tested.
        Observable. This is Sarthi."

[3:00] END
```

---

**Document Version:** 1.0  
**Last Updated:** March 21, 2026  
**Status:** Ready for implementation
