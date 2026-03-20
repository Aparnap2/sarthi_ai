# Sarthi.ai — Ops Memory Layer for Software Startups

<div align="center">

**Two Agents. Nine Technologies. Production-Grade Agentic AI.**

[![Tests](https://img.shields.io/badge/tests-40%2B%20unit%20|%208%2B%20E2E-brightgreen)](./docs/PRD.md)
[![Agents](https://img.shields.io/badge/agents-2%20(Finance+%2B%20BI)-blue)](./docs/PRD.md)
[![Stack](https://img.shields.io/badge/stack-Go%20|%20Python%20|%20Temporal%20|%20LangGraph-purple)](./docs/PRD.md)
[![Version](https://img.shields.io/badge/version-v1.0.0--alpha-orange)](./docs/PRD.md)

[Architecture](#architecture) • [Agents](#two-agents) • [PRD](./docs/PRD.md) • [Demo](#3-minute-demo)

</div>

---

## The Problem

Every software startup that reaches ₹50L ARR hits the same wall — **context evaporation**.

| Pain | Before Sarthi |
|------|---------------|
| Anomaly detection | 3 weeks (if ever) |
| Runway accuracy | Monthly manual calc |
| BI query time | 2–4 hrs (analyst) |
| Context on alerts | None |
| Weekly digest | Manual assembly |

**The gap:** No system watches your data continuously, reasons about anomalies with memory of the past, answers natural language questions, and gets smarter with every event.

---

## The Solution

**Sarthi** is an ops memory layer with two focused agents:

```
┌──────────────────────────────────────────────────────────────┐
│  FINANCE AGENT                                                │
│  Watches: Razorpay, bank feed, expenses                       │
│  Does:    Burn/runway, anomaly detection, spend memory       │
│  Output:  Telegram alerts + weekly digest                    │
├──────────────────────────────────────────────────────────────┤
│  BI AGENT                                                     │
│  Watches: PostgreSQL, Sheets, GA4, Mixpanel                  │
│  Does:    NL → SQL → chart → narrative, proactive insights   │
│  Output:  Charts + narrative + Telegram digest               │
└──────────────────────────────────────────────────────────────┘
```

**Value delivered:**
- Anomaly detection: < 5 minutes (was 3 weeks)
- Runway accuracy: Real-time (was monthly)
- BI query time: < 30 seconds (was 2–4 hrs)
- Cost: ₹9,999/month (was ₹50,000+ for human)

---

## Architecture

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
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

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

---

## Two Agents

### Finance Agent

**Purpose:** Continuously monitors financial events. Detects anomalies. Tracks burn and runway. Remembers context. Alerts with explanation.

**LangGraph Nodes (9-node ReAct loop):**
```
1. INGEST_EVENT       → Validate, normalize, classify
2. UPDATE_SNAPSHOT    → Query PostgreSQL: revenue, expense, burn, runway
3. LOAD_VENDOR_BASELINE → IF expense: query 90d avg for vendor
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
  → BI Agent triggered: "Break down {vendor} costs"
    → Chart + breakdown → Telegram

Founder taps [Dismiss]
  → Qdrant: "dismissed — not anomalous"
  → Future threshold raised for this vendor
```

---

### BI Agent

**Purpose:** Answers natural language questions. Proactively surfaces insights. Executes SQL safely. Remembers past queries.

**LangGraph Nodes (9-node ReAct loop):**
```
1. UNDERSTAND_QUERY    → Classify: aggregation/trend/breakdown
2. SELECT_DATASOURCE   → Revenue → payments, Users → users
3. GENERATE_SQL        → LLM (DSPy): NL → SQL
4. EXECUTE_SQL         → PostgreSQL (read-only), retry on error
5. DECIDE_VISUALIZATION → line/bar/pie/text based on type
6. GENERATE_CODE       → Plotly Python in sandbox
7. GENERATE_NARRATIVE  → LLM (DSPy): 2–4 sentence plain English
8. WRITE_MEMORY        → Qdrant: query + SQL + narrative
9. EMIT_OUTPUT         → Telegram with chart + narrative
```

**Proactive Monday Queries:**
1. "How did revenue change this week vs last week?"
2. "What are the top 3 expense categories this month?"
3. "Which user cohort has the lowest 7-day retention?"

---

## Quick Start

### Prerequisites

```bash
# Docker installed
docker --version

# Ollama installed and running
ollama list
# Should show: qwen3:0.6b, nomic-embed-text, ibm/granite-docling
```

### Start Infrastructure

```bash
# Clone repo
git clone https://github.com/Aparnap2/IterateSwarm.git
cd iterate_swarm

# Start Docker containers (one at a time)
docker run -d --name sarthi-postgres \
  -e POSTGRES_USER=sarthi -e POSTGRES_PASSWORD=sarthi \
  -e POSTGRES_DB=sarthi -p 5432:5432 \
  postgres:15-alpine

docker run -d --name sarthi-qdrant \
  -p 6333:6333 \
  qdrant/qdrant:latest

docker run -d --name sarthi-redpanda \
  -p 19092:19092 \
  redpandadata/redpanda:latest-fips \
  redpanda start --overprovisioned

# Temporal (requires PostgreSQL first)
docker run -d --name sarthi-temporal \
  -e DB=postgresql \
  -e POSTGRES_USER=sarthi \
  -e POSTGRES_PWD=sarthi \
  -e POSTGRES_SEEDS=host.docker.internal \
  -p 7233:7233 -p 8089:8089 \
  temporalio/server:latest

# Wait for all to start
sleep 30

# Verify
docker ps
```

### Run Tests

```bash
# Full test suite
bash scripts/test_sarthi_v2.sh

# Finance agent tests only
cd apps/ai
uv run pytest tests/unit/test_finance_nodes.py -v

# BI agent tests only
uv run pytest tests/unit/test_bi_nodes.py -v

# E2E tests (requires all containers running)
uv run pytest tests/e2e/ -v --timeout=120
```

### Simulate Events

```bash
# Simulate Razorpay payment (2.3x AWS spike)
TENANT_ID=test-tenant-001 bash scripts/simulate_payment.sh

# Simulate BI query
TENANT_ID=test-tenant-001 QUERY="What was MRR last month?" \
  bash scripts/simulate_query.sh

# Smoke test
bash scripts/smoke_test.sh
```

---

## 3-Minute Demo

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

## Test Results

| Category | Tests | Target | Status |
|----------|-------|--------|--------|
| Finance Unit | 14 | 14+ | 🔲 Pending |
| BI Unit | 10 | 10+ | 🔲 Pending |
| Go Webhooks | 5 | 5+ | 🔲 Pending |
| E2E Flows | 8 | 8+ | 🔲 Pending |
| LLM Evals | 3 | 3 | 🔲 Pending |

**Run all tests:**
```bash
bash scripts/test_sarthi_v2.sh
```

---

## Project Status

**Current Phase:** Week 1 — Finance Agent Implementation

| Week | Dates | Deliverable | Status |
|------|-------|-------------|--------|
| 1 | Mar 21–27 | Finance Agent end-to-end | 🔲 In Progress |
| 2 | Mar 28–Apr 3 | BI Agent end-to-end | 🔲 Pending |
| 3 | Apr 4–10 | Cross-agent + memory | 🔲 Pending |
| 4 | Apr 11–17 | Production deploy | 🔲 Pending |
| 5 | Apr 18–24 | htmx dashboard (optional) | 🔲 Pending |

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [PRD](./docs/PRD.md) | Complete product requirements, agent specs |
| [Architecture](./docs/ARCHITECTURE.md) | System design, data flow |
| [Testing](./docs/TESTING_ARCHITECTURE.md) | Testing strategy, 40+ unit + 8+ E2E |
| [Vectorless RAG](./docs/VECTORLESS_RAG_ZINCSEARCH.md) | ZincSearch + Docling + LangExtract |
| [ZincSearch Integration](./docs/ZINCSEARCH_INTEGRATION_COMPLETE.md) | Document retrieval pipeline |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Write tests first (RED → GREEN → REFACTOR)
4. Run invariant checks before commit
5. Open a PR

**Invariant Checks (run before every commit):**
```bash
# I-1: No raw JSON marshal in workflow/
grep -rn "json.Marshal\|json.Unmarshal" apps/core/internal/workflow/ \
  | grep -v "_test.go" | grep -v "// safe:" && exit 1

# I-2: No direct AzureOpenAI() outside config/llm.py
grep -rn "AzureOpenAI(" apps/ai/src/ | grep -v "config/llm.py" && exit 1

# I-3: All existing tests still pass
cd apps/core && go test ./... -timeout=60s -q && cd -
cd apps/ai && uv run pytest tests/ -x -q --timeout=90 && cd -

# I-4: No banned jargon in agent output
grep -rn "leverage\|synergy\|utilize\|streamline" \
  apps/ai/src/agents/ | grep -v "# allowed:" && exit 1
```

---

## License

MIT License — see [LICENSE](LICENSE) file.

---

**Built with:** Go 1.24 • Python 3.11 • Temporal • Redpanda • PostgreSQL • Qdrant • Ollama • LangGraph • DSPy • Langfuse

**Status:** 🔲 v1.0.0-alpha — In Development
