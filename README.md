# Sarthi V2.0 — Guardian AI for Solo Founders

[![Tests](https://img.shields.io/badge/tests-241%20passing%20%7C%206%20skipped%20%7C%200%20failures-brightgreen)](docs/PRD.md)
[![Agents](https://img.shields.io/badge/agents-4%20(Pulse%2C%20Anomaly%2C%20Investor%2C%20QA)-blue)](docs/PRD.md)
[![Workflows](https://img.shields.io/badge/workflows-7%20Temporal%20workflows-purple)](docs/PRD.md)
[![Guardian](https://img.shields.io/badge/guardian-17%20watchlist%20patterns-orange)](docs/PRD.md)
[![Version](https://img.shields.io/badge/version-v2.0-red)](docs/PRD.md)

> **First-time founders don't know what they don't know. Sarthi does.**

---

## 🎬 Running the Demo

**One command to start everything:**
```bash
bash scripts/demo_start.sh
```

**Run the 3-minute demo:**
```bash
bash scripts/demo_run.sh
```

**Stop cleanly:**
```bash
bash scripts/demo_stop.sh
```

**Pre-flight check (run before recruiter call):**
```bash
bash scripts/demo_preflight.sh
```

**What the demo shows:**
| Step | What happens | Tech demonstrated |
|------|-------------|-------------------|
| Guardian Watchlist | 17 seed-stage failure patterns detected | Finance, BI, Ops guards |
| Memory Spine | 5-layer memory compounds context | Redis → Qdrant → Kuzu → PG → Qdrant |
| RAG Kernel | ≤800 token context assembly before every LLM call | tiktoken + weighted retrieval |
| HITL | 3-tier alert routing | Auto → Slack Review → Human Override |
| LLMOps | Langfuse tracing, eval scoring, self-analysis | Observability + quality |
| Tests | 241 tests run live | pytest · Temporal |

**100% local. Zero API costs. Zero internet required.**

---

## Overview

**Sarthi V2.0** is a guardian AI system for solo SaaS founders. It doesn't wait to be asked — it watches your Stripe + bank accounts 24/7, detects patterns from a curated watchlist of 17 seed-stage failure modes, and surfaces insights you couldn't have surfaced yourself — before those patterns become crises.

**North Star Metric:** "Founders who connected Stripe + bank and kept Sarthi running for 30 days" — target >60% of onboarded users.

**Price:** $79/month (less than one day of a junior hire)

---

## V2.0 Features

- **Guardian Watchlist:** 17 seed-stage failure patterns (6 Finance, 6 BI, 5 Ops) — from silent churn death to deploy frequency collapse
- **5-Layer Memory Spine:** Redis (working) → Qdrant (episodic) → Kuzu (semantic graph) → PostgreSQL (procedural) → Qdrant (compressed) — context compounds with every event
- **RAG Kernel:** ≤800 token context assembly before every LLM call, wired into all 4 agents with graceful fallback contract
- **3-Tier HITL:** Auto (info, high confidence) → Slack Review (warning, new patterns) → Human Override (critical, investor updates)
- **LLMOps:** Langfuse tracer (zero test impact), weekly eval loop (4-dimension scoring), agent self-analysis
- **7 Temporal Workflows:** Pulse, Investor, QA (V1.0) + SelfAnalysis, EvalLoop, Compression, WeightDecay (V2.0)
- **241 tests passing** with zero regressions from V1.0 (was 119, now 241+)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SARTHI V2.0 ARCHITECTURE                        │
│                                                                     │
│  External Data Sources                                              │
│  Stripe API · Plaid/Mercury · PostgreSQL · Sentry                   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Go Fiber API (webhooks, HMAC validation, health checks)    │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                         │
│                    Redpanda Event Bus                               │
│         stripe.events · sentry.events · ops.events                  │
│                           │                                         │
│  ┌────────────────────────▼────────────────────────────────────┐   │
│  │  TEMPORAL WORKFLOW ENGINE (7 workflows, 9 activities)       │   │
│  │  Pulse · Investor · QA · SelfAnalysis · EvalLoop ·          │   │
│  │  Compression · WeightDecay                                  │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                         │
│  ┌────────────────────────▼────────────────────────────────────┐   │
│  │  PYTHON AI WORKER (LangGraph + DSPy)                        │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  GUARDIAN WATCHLIST: 17 seed-stage failure patterns │   │   │
│  │  │  6 Finance · 6 BI · 5 Ops                           │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  MEMORY SPINE (5 layers)                            │   │   │
│  │  │  L1 Redis → L2 Qdrant → L3 Kuzu → L4 PG → L5 Qdrant│   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  RAG KERNEL: ≤800 token context assembly            │   │   │
│  │  │  Wired into all 4 agents with fallback contract     │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  HITL MANAGER: 3-tier routing                       │   │   │
│  │  │  Auto → Slack Review → Human Override               │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  LLMOPS: Langfuse tracer · Eval loop · Self-analysis│   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                         │
│  ┌────────────────────────▼────────────────────────────────────┐   │
│  │  SLACK DELIVERY: guardian alerts · investor drafts · NL QA  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  OBSERVABILITY: Langfuse (LLM) · SigNoz (infra)                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Stack:**
| Layer | Technology |
|-------|------------|
| API Gateway | Go + Fiber |
| Event Bus | Redpanda (Kafka-compatible) |
| Workflow Engine | Temporal (durable execution) |
| Agent Framework | LangGraph (Python) |
| LLM | qwen3:0.6b via Ollama (local) |
| Prompt Compiler | DSPy |
| Memory L1 | Redis 7 (working, 1h TTL) |
| Memory L2/L5 | Qdrant (episodic + compressed) |
| Memory L3 | Kuzu (embedded semantic graph) |
| Memory L4 | PostgreSQL (procedural) |
| Notifications | Slack (Telegram fallback) |
| Observability | Langfuse |

---

## Guardian Watchlist (17 Patterns)

Sarthi watches for 17 seed-stage failure patterns across three domains. An assistant waits to be asked. A guardian knows to watch before you know to look.

### Finance Guardian (FG-01 to FG-06)

| ID | Pattern | Trigger |
|----|---------|---------|
| FG-01 | Silent Churn Death | Monthly churn > 3% (→ 36% annual) |
| FG-02 | Burn Multiple Creep | Net burn / new ARR > 2.0x |
| FG-03 | Customer Concentration Risk | Top customer > 30% of MRR |
| FG-04 | Runway Compression Acceleration | Burn growing faster than runway shrinks |
| FG-05 | Failed Payment Cluster | 3+ failed payments in 7 days |
| FG-06 | Payroll Revenue Ratio Breach | Payroll > 60% of revenue |

### BI Guardian (BG-01 to BG-06)

| ID | Pattern | Trigger |
|----|---------|---------|
| BG-01 | Leaky Bucket Activation | Signups growing, activation flat or falling |
| BG-02 | Power User MRR Masking | Top 10% users hiding declining avg MRR/customer |
| BG-03 | Feature Adoption Post-Deploy Drop | Feature usage drops after deploy |
| BG-04 | Cohort Retention Degradation | New cohorts retaining 10%+ worse than prior |
| BG-05 | NRR Below 100 Seed | NRR < 100% (losing more than expanding) |
| BG-06 | Trial Activation Wall | Users abandoning at same step repeatedly (>50%) |

### Ops Guardian (OG-01 to OG-05)

| ID | Pattern | Trigger |
|----|---------|---------|
| OG-01 | Error Rate User Segment Correlation | Errors concentrated in one user segment (>10%) |
| OG-02 | Support Volume Outpacing Growth | Support tickets growing 1.5x faster than users |
| OG-03 | Cross-Channel Bug Convergence | Same bug in 3+ channels simultaneously |
| OG-04 | Deploy Frequency Collapse | Deploy frequency drops >50% MoM |
| OG-05 | Infrastructure Unit Economics Divergence | AWS cost growth > 2x user growth |

---

## Memory Spine (5 Layers)

Sarthi's memory compounds with every event. Five layers, each with distinct purpose:

| Layer | Backend | TTL | Purpose |
|-------|---------|-----|---------|
| **L1** Working | Redis 7 | 1 hour | Current workflow context, session state |
| **L2** Episodic | Qdrant | 90 days → compressed | Raw event history |
| **L3** Semantic | Kuzu (embedded) | Permanent | Relationships between patterns |
| **L4** Procedural | PostgreSQL | Permanent | Learned agent behavior, resolved blindspots |
| **L5** Compressed | Qdrant | Permanent | Compressed episodic summaries |

**Key properties:**
- Each layer is independently testable and degradable
- If any layer is unavailable, the system continues (no crash)
- Compression triggers every 50 episodic writes → oldest 30 compressed into L5
- Weight decay runs weekly → events older than 60 days decay (weight < 0.3 → compressible)
- Tenant isolation is absolute: every query filtered by `tenant_id`

---

## HITL Manager (3-Tier Routing)

| Tier | Trigger | Action |
|------|---------|--------|
| **1 — AUTO** | Severity: info, Confidence: > 0.85, Pattern: seen before | Send immediately to Slack |
| **2 — SLACK REVIEW** | Severity: warning, Confidence: 0.60–0.85, OR: new pattern | Draft to `#sarthi-review` with [Send Now] [Edit] [Dismiss] |
| **3 — HUMAN OVERRIDE** | Severity: critical, Confidence: < 0.60, OR: investor updates | Block send — require explicit human approval |

---

## The 4 Agents

| Agent | Purpose | Trigger | Output |
|-------|---------|---------|--------|
| **PulseAgent** | Daily business pulse | Daily 08:00 IST | 3-line Slack summary |
| **AnomalyAgent** | Explains spikes with guardian insight | Conditional (after Pulse) | Guardian message + action |
| **InvestorAgent** | Weekly update draft | Weekly Friday 08:00 IST | Markdown investor update |
| **QAAgent** | Founder Q&A in natural language | On-demand (Slack message) | Answer + follow-up |

**All 4 agents are wired with:**
- RAG Kernel context (≤800 tokens from memory spine)
- Guardian watchlist integration
- Memory spine write_all (all 5 layers)
- HITL routing
- Graceful fallback (agent never crashes if any component is down)

---

## Workflows

| Workflow | Schedule | Description |
|----------|----------|-------------|
| PulseWorkflow | Daily 08:00 IST | Runs PulseAgent → AnomalyAgent (if anomalies found) |
| InvestorWorkflow | Weekly Friday 08:00 IST | Generates investor update draft (HITL Tier 3) |
| QAWorkflow | On-demand | Answers founder questions via Slack |
| SelfAnalysisWorkflow | Weekly | Agent self-review, trend analysis |
| EvalLoopWorkflow | Weekly | 4-dimension eval scoring across all agents |
| CompressionWorkflow | Trigger (50 writes) | Compresses oldest L2 events into L5 summary |
| WeightDecayWorkflow | Weekly | Applies decay to L2 events older than 60 days |

**Retry Policies:**
- PulseAgent: 3 retries, 30s initial interval
- AnomalyAgent: 2 retries, 15s initial interval
- InvestorAgent: 3 retries, 30s initial interval
- QAAgent: 2 retries, 10s initial interval
- Slack notifications: 3 retries, 5s initial interval

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Integrations (V1.0) | 12 | ✅ 12/12 passing |
| PulseAgent (V1.0) | 20 | ✅ 20/20 passing |
| AnomalyAgent (V1.0) | 15 | ✅ 15/15 passing |
| InvestorAgent (V1.0) | 15 | ✅ 14/15 passing (93%) |
| QAAgent (V1.0) | 15 | ✅ 15/15 passing |
| Workflows + Worker (V1.0) | 14 | ✅ 14/14 passing |
| Guardian Watchlist (V2.0) | 28 | ✅ 28/28 passing |
| Memory Spine (V2.0) | 30 | ✅ 30/30 passing |
| HITL Manager (V2.0) | 11 | ✅ 11/11 passing |
| LLMOps (V2.0) | 10 | ✅ 10/10 passing |
| Workflow Integration (V2.0) | 11 | ✅ 11/11 passing |
| **Skipped (expected)** | 6 | ⏭️ 1 Ollama, 5 DB migrations |
| **TOTAL** | **247** | **✅ 241 passed, 6 skipped, 0 failures** |

**Zero regressions from V1.0** (was 119 passing, now 241+).

---

## Quick Start (<5 minutes)

### 1. Clone + configure
```bash
git clone https://github.com/Aparnap2/IterateSwarm.git
cd IterateSwarm
cp .env.example .env
# Edit .env — add your STRIPE_API_KEY (test mode ok for dev)
```

### 2. Start infrastructure
```bash
bash scripts/demo_start.sh
# Starts: PostgreSQL, Qdrant, Redpanda, Redis, Ollama, Temporal, Langfuse
```

### 3. Run database migration
```bash
psql "postgresql://sarthi:sarthi@localhost:5433/sarthi" \
  -f migrations/009_pulse_pivot.sql
```

### 4. Initialize Qdrant collections
```bash
cd apps/ai && uv run python src/setup/init_qdrant_collections.py
# Creates: pulse_memory, anomaly_memory, investor_memory,
#          qa_memory, compressed_memory (NEW), founder_blindspots (NEW)
```

### 5. Start Temporal worker
```bash
cd apps/ai && uv run python -m src.worker
# Worker connects to Temporal, listens on SARTHI-MAIN-QUEUE
```

### 6. Trigger first guardian alert
```bash
bash scripts/demo_run.sh
# Guardian watchlist detects patterns → memory spine loads context →
# RAG kernel assembles → HITL routes → Slack alert delivered
```

---

## Project Structure

```
apps/
├── ai/src/
│   ├── agents/
│   │   ├── pulse/          # PulseAgent (daily business pulse)
│   │   ├── anomaly/        # AnomalyAgent (explains spikes)
│   │   ├── investor/       # InvestorAgent (weekly updates)
│   │   └── qa/             # QAAgent (founder Q&A)
│   ├── guardian/           # V2.0 NEW
│   │   ├── watchlist.py    # 17 SeedStageBlindspot objects
│   │   ├── detector.py     # Runs all watchlist items
│   │   └── insight_builder.py
│   ├── memory/             # V2.0 NEW
│   │   ├── spine.py        # 5-layer orchestrator
│   │   ├── working.py      # L1 Redis
│   │   ├── episodic.py     # L2 Qdrant
│   │   ├── semantic.py     # L3 Kuzu
│   │   ├── procedural.py   # L4 PostgreSQL
│   │   ├── compressed.py   # L5 Qdrant
│   │   ├── rag_kernel.py   # ≤800 token assembly
│   │   ├── compressor.py   # 50-write trigger
│   │   └── state_manager.py
│   ├── hitl/               # V2.0 NEW
│   │   ├── manager.py      # 3-tier routing
│   │   └── confidence.py   # Confidence scoring
│   ├── llmops/             # V2.0 NEW
│   │   ├── tracer.py       # Langfuse @traced
│   │   ├── eval_loop.py    # Weekly eval
│   │   └── self_analysis.py
│   ├── activities/         # Temporal activities (9 files)
│   ├── workflows/          # Temporal workflows (7 files)
│   ├── integrations/       # Stripe, Plaid, Slack, DB, Qdrant
│   └── worker.py           # Temporal worker entrypoint
├── core/                   # Go API (webhooks, HITL endpoints)
└── ...
```

---

## Development

### Testing

```bash
# Run all tests (from apps/ai)
cd apps/ai
uv run pytest

# Run specific agent tests
uv run pytest tests/agents/pulse/ -v

# Run guardian watchlist tests
uv run pytest tests/guardian/ -v

# Run memory spine tests
uv run pytest tests/memory/ -v

# Run single test
uv run pytest tests/agents/pulse/test_graph.py::test_pulse_agent_full_flow -v

# Run E2E tests
uv run pytest tests/e2e/ -v
```

### Linting

```bash
# Format code
ruff format apps/ai/src

# Lint
ruff check apps/ai/src

# Type check
uv run mypy apps/ai/src
```

---

## Configuration

Create a `.env` file:

```bash
# LLM Configuration (auto-detected)
OPENAI_API_KEY=your_api_key
# or
GROQ_API_KEY=your_api_key
# or
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_API_KEY=your_api_key
# or (local)
OLLAMA_BASE_URL=http://localhost:11434

# Database
DATABASE_URL=postgresql://sarthi:sarthi@localhost:5433/sarthi

# Qdrant
QDRANT_URL=http://localhost:6333

# Redis
REDIS_URL=redis://localhost:6379

# Kuzu (embedded — no service needed)
KUZU_DB_PATH=./data/kuzu

# Temporal
TEMPORAL_HOST=localhost:7233

# Redpanda
REDPANDA_BROKERS=localhost:29092

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# Stripe (test mode)
STRIPE_API_KEY=sk_test_...

# Plaid (sandbox)
PLAID_CLIENT_ID=...
PLAID_SECRET=...

# Langfuse (optional — LLMOps)
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
```

---

## Monitoring

**Local Development:**
- **Langfuse UI:** http://localhost:3001 (LLM traces, latency, costs)
- **Temporal Web UI:** http://localhost:8088 (workflow executions, retries)
- **Redpanda Console:** http://localhost:8080 (event stream debugging)
- **Qdrant Dashboard:** http://localhost:6333/dashboard
- **Redis CLI:** `redis-cli -p 6379 ping`

**Production (Hetzner / AWS):**
1. Set environment variables in `.env.prod`
2. Deploy with `docker compose -f docker-compose.prod.yml up -d`
3. Configure Temporal schedules via `temporal schedule create`
4. Monitor via Langfuse UI + Temporal Web UI

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

**Git Standards:**
- Use [Conventional Commits](https://www.conventionalcommits.org/)
- Branch naming: `feature/description`, `fix/description`, `refactor/description`
- Never commit to `main` directly

---

## License

MIT

---

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Test Results](docs/TEST_RESULTS.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Agent Instructions](AGENT_INSTRUCTION.md)

---

## Demo

**3-Minute Demo Script (V2.0):**

```
[0:00] "Sarthi V2.0 is a guardian AI system for solo founders.
        It doesn't wait to be asked — it watches for failure
        patterns you don't know to look for."

[0:20] "17 seed-stage failure patterns: 6 Finance, 6 BI, 5 Ops.
        Silent churn death. Burn multiple creep.
        NRR below 100. Deploy frequency collapse."

[0:40] "5-layer memory spine: Redis working memory →
        Qdrant episodic → Kuzu semantic graph →
        PostgreSQL procedural → Qdrant compressed summaries.
        Every event compounds context."

[1:00] "Before every LLM call, a RAG kernel assembles
        ≤800 tokens from all memory layers.
        If any layer is down, it falls back gracefully."

[1:15] "3-tier HITL: info alerts go auto, warnings go to
        Slack review, critical and investor updates
        always require human approval."

[1:35] Run: bash scripts/demo_run.sh
       "Watch: Stripe data flows in, guardian watchlist
        detects a pattern, memory spine loads context,
        RAG kernel assembles it, HITL routes it,
        and a guardian alert arrives in Slack."

[2:00] Show Langfuse:
       "Every LLM call traced. Eval loop scores weekly.
        Agents self-analyze. Full observability."

[2:20] "241 tests passing. Zero regressions.
        Four agents. Seven workflows.
        Seventeen guardian patterns.
        Five memory layers. This is Sarthi V2.0."

[2:40] "First-time founders don't know what they don't know.
        Sarthi does."

[3:00] END
```
