# Sarthi.ai — Your Internal Ops Virtual Office

<div align="center">

**13 virtual employees. 6 desks. Zero external-facing work.**

[![Tests](https://img.shields.io/badge/tests-~189%20target-brightgreen)](./apps/ai/tests/)
[![Employees](https://img.shields.io/badge/employees-13%20virtual-blue)](./docs/PRD.md)
[![Desks](https://img.shields.io/badge/desks-6%20internal-purple)](./docs/PRD.md)
[![ROI](https://img.shields.io/badge/ROI-20x%E2%80%9350x-green)](./docs/PRD.md)
[![Version](https://img.shields.io/badge/version-v4.2.0--alpha-purple)](./docs/PRD.md)

[Live Demo](#) • [Architecture](#architecture) • [6 Desks](#the-6-desks--13-virtual-employees) • [API Docs](./docs/api/) • [PRD](./docs/PRD.md) • [Scope](./docs/INTERNAL_OPS_SCOPE.md)

</div>

---

## The Problem

Early-stage startups drown in operational chaos:

| Metric | Impact |
|--------|--------|
| **Tools fragmentation** | Average startup uses **15 different tools** across payroll, finance, HR, compliance |
| **Founder time waste** | **15–20 hours/week** on back-office = **₹90,000–₹2,25,000/month** hidden cost |
| **Fractional admin cost** | **₹3.5L–₹7.5L/month** for CFO, bookkeeper, HR, legal retainer, EA |
| **Roadmap delay** | Back-office drag delays product roadmaps by **~3 months per year** |

**The gap:** Not "startups don't have tools" — it's **15 disconnected tools with no intelligence layer connecting them**.

---

## The Solution

**Sarthi** is the internal operations virtual office for Seed to Series A startups.

```
We don't find you customers.
We make sure your company doesn't collapse while you do.

Every operational task that doesn't require your
unique human judgment — Sarthi handles.
Everything that does — Sarthi prepares perfectly
and puts in front of you in 30 seconds, not 3 hours.
```

### What Sarthi Does (Real Examples)

> "Sarthi saved me 18 hours this week:
> - Prepared my GST + VAT filing data automatically (India + UK)
> - Sent payment reminders to 5 overdue clients
> - Told me my runway dropped from 9 to 7 months and showed me exactly why
> - Drafted the offer letter for my new UK hire (compliant with UK law)
> - Found ₹23k/month in unused SaaS subscriptions
> - Tracked all contract renewals and flagged 2 expiring soon"

**That's not a feature list. That's a Wednesday.**

### What Sarthi Does NOT Do

❌ RevOps / GTM / CRM outreach
❌ Customer success / support
❌ External market intelligence (competitors, pricing)
❌ Content generation / marketing
❌ Cap table management
❌ Tax filing
❌ Grant applications

**Why?** Internal ops is painful enough. We solve that completely.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 0 — KERNEL (Go + Temporal + Graphiti)                     │
│  BusinessOSWorkflow: orchestrates all agents, manages state     │
│  enforces HITL gates, temporal knowledge graph                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1 — CHIEF OF STAFF (1 agent)                              │
│  The only agent that talks to the founder.                      │
│  Routes work to 6 desks.                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2 — 6 DESKS (13 Virtual Employees)                        │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ Finance     │ │ People      │ │ Legal       │               │
│  │ Desk (4)    │ │ Desk (2)    │ │ Desk (2)    │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ Intelligence│ │ IT & Tools  │ │ Admin       │               │
│  │ Desk (2)    │ │ Desk (1)    │ │ Desk (2)    │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3 — DATA LAYER (ingest + memory, never surfaces)          │
│  Ingestion | Memory (Qdrant + Neo4j) | Connector                │
└─────────────────────────────────────────────────────────────────┘
```

### Infrastructure Stack ($0/month)

| Layer | Tool | Cost |
|-------|------|------|
| **Interface** | Telegram Bot API | $0 forever |
| **LLM** | Azure OpenAI | $0 (existing) |
| **Orchestration** | Temporal (self-hosted) | $0 |
| **Message Queue** | Redpanda (self-hosted) | $0 |
| **Databases** | PostgreSQL + Qdrant + Neo4j | $0 |
| **Graph** | Graphiti (Neo4j plugin) | $0 OSS |
| **Bank Parsing** | Docling + pdfplumber (OSS) | $0 |

**Total monthly cost for MVP: $0**

---

## The 6 Desks — 13 Virtual Employees

### Tier 1: Chief of Staff Agent

**Role:** The face of Sarthi. Routes work to 6 desks, synthesizes intelligence, manages the relationship.

**Output:**
- "Here's what I found + one action"
- "I handled X — here's what I did"
- "I need your decision on X — here's context"
- "Weekly briefing: X handled, Y needs you"

---

### Tier 2: The 6 Desks

#### 📊 Finance Desk (4 employees)

**CFO Agent**
- 13-week rolling cash flow forecast
- Burn rate + runway calculation
- Unit economics: CAC, LTV, payback
- Scenario modeling: "what if we hire in March?"

**Bookkeeper Agent**
- Expense categorization (auto)
- Bank vs books reconciliation
- Monthly P&L narrative generation

**AR/AP Clerk Agent**
- Invoice generation + payment reminders
- Accounts receivable aging report

**Payroll Clerk Agent**
- Payroll data preparation
- PF/ESIC/pension filing reminders

---

#### 👥 People Desk (2 employees)

**HR Coordinator Agent**
- Onboarding checklist execution
- Offer letter generation
- Leave balance tracking

**Internal Recruiter Agent**
- Job description drafting
- Interview scheduling coordination

---

#### ⚖️ Legal Desk (2 employees)

**Contracts Coordinator Agent**
- NDA generation (templates)
- Contract review summary
- Contract expiry tracking

**Compliance Tracker Agent**
- GST, TDS, advance tax deadlines
- PF, ESIC, PT compliance
- DPDP Act / GDPR compliance checklist

---

#### 📈 Intelligence Desk (2 employees)

**BI Analyst Agent (Internal-Only)**
- Customer cohort analysis (retention, churn)
- Revenue concentration risk
- Anomaly detection across all data sources

**Policy Watcher Agent**
- Regulatory change monitoring
- Tax law updates affecting THIS company

---

#### 🖥️ IT & Tools Desk (1 employee)

**IT Admin Agent**
- SaaS subscription audit + optimization
- Cloud spend analysis
- Tool access provisioning/deprovisioning

---

#### 📋 Admin Desk (2 employees)

**Executive Assistant Agent**
- Meeting prep (pulls context, agenda)
- Action item extraction from meeting notes

**Knowledge Manager Agent**
- SOP documentation from observed workflows
- Internal wiki organization

---

### Tier 3: Data Layer (Invisible)

- **IngestionAgent:** Normalizes all data (bank PDF, accounting, Notion, Slack, Stripe)
- **MemoryAgent:** Qdrant + Neo4j + Graphiti — company's long-term brain (vector + temporal)
- **ConnectorAgent:** OAuth + API connections to all tools

---

## The Self-Correcting System

**How Sarthi gets smarter about YOUR company over time:**

1. **AGENT ACTS** → Bookkeeper categorizes AWS expense
2. **OUTCOME OBSERVED** → Founder confirms category is correct
3. **MEMORY UPDATED** → "AWS expenses: categorized as 'Cloud Infrastructure'" (Qdrant + Neo4j)
4. **FUTURE ADJUSTED** → Auto-categorize similar expenses, flag anomalies
5. **CONTEXT DRIFT DETECTED** → "Cloud spend up 40% MoM. New deployment or pricing change?"

**Not generic AI. Company-specific intelligence.**

---

## ROI & Pricing

### What Sarthi Replaces

| Role | Fractional Cost (₹/month) | Sarthi Desk |
|------|--------------------------|-------------|
| Fractional CFO | ₹75,000–₹1,50,000 | Finance Desk |
| Bookkeeper | ₹25,000–₹40,000 | Finance Desk |
| HR Coordinator | ₹30,000–₹50,000 | People Desk |
| Legal Retainer | ₹50,000–₹1,00,000 | Legal Desk |
| EA/Admin | ₹20,000–₹35,000 | Admin Desk |
| **Total** | **₹2,00,000–₹3,75,000** | **6 Desks** |

### Sarthi Pricing

| Tier | Price (₹/month) | Desks Included | ROI |
|------|-----------------|----------------|-----|
| Starter | ₹5,000 | Finance + Admin | 20x |
| Growth | ₹10,000 | All 6 Desks | 35x |
| Scale | ₹15,000 | All 6 Desks + Priority | 50x |

**Replace ₹3.5L–₹7.5L/month in admin costs with ₹5K–₹15K/month.**

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Azure OpenAI account (or OpenRouter)
- Telegram Bot Token (from @BotFather, free)

### Start All Services

```bash
# Clone
git clone https://github.com/Aparnap2/IterateSwarm.git
cd iterate_swarm

# Start infrastructure
docker compose up -d

# Wait for services
sleep 60

# Check health
docker compose ps
```

### Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Telegram Bot** | @YourBotName | Primary interface |
| **Temporal UI** | http://localhost:8088 | Workflow tracing |
| **Neo4j Browser** | http://localhost:7474 | Knowledge graph |
| **Qdrant Dashboard** | http://localhost:6333 | Vector search |
| **Redpanda Console** | http://localhost:9644 | Event streaming |

### First Run

1. Message your Telegram bot: `/start`
2. Complete 6-question onboarding
3. Upload first bank statement (CSV/Excel/PDF)
4. Receive first insight: "Here's your cash position + one action"

---

## Development

### Run Tests

```bash
# All tests
cd apps/ai
uv run pytest tests/ -v --timeout=120

# Specific groups
uv run pytest tests/test_sarthi_tdd.py -v           # TDD tests (~80)
uv run pytest tests/test_e2e_saarathi.py -v         # E2E flows (20)
uv run pytest tests/test_llm_eval.py -v             # LLM evals (15)
uv run pytest tests/test_llm_connectivity.py -v     # LLM connectivity (4)

# Phase 3 Tests (TBD - Not Yet Available)
# uv run pytest tests/test_finance_desk.py -v         # Finance Desk (25) - Phase 3
# uv run pytest tests/test_people_desk.py -v          # People Desk (12) - Phase 3
# uv run pytest tests/test_legal_desk.py -v           # Legal Desk (12) - Phase 3
# uv run pytest tests/test_intelligence_desk.py -v    # Intelligence Desk (15) - Phase 3
# uv run pytest tests/test_it_desk.py -v              # IT Desk (10) - Phase 3
# uv run pytest tests/test_admin_desk.py -v           # Admin Desk (12) - Phase 3

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

**Test Categories:**
1. **Infrastructure Health** (6 tests) — Azure LLM, Qdrant, Neo4j, PostgreSQL reachable
2. **Memory Agent** (22 tests) — Embeddings, Qdrant upsert, Neo4j graph, semantic search
3. **Chief of Staff** (8 tests) — Plain language, correct routing, ToneFilter fidelity
4. **Bank Parser** (8 tests) — HDFC/ICICI/SBI CSV, Docling accurate mode, multi-format
5. **Finance Desk** (25 tests) — CFO, Bookkeeper, AR/AP, Payroll agents - Phase 3 TBD
6. **People Desk** (12 tests) — HR Coordinator, Internal Recruiter - Phase 3 TBD
7. **Legal Desk** (12 tests) — Contracts, Compliance Tracker - Phase 3 TBD
8. **Intelligence Desk** (15 tests) — BI Analyst, Policy Watcher
9. **IT & Tools Desk** (10 tests) — IT Admin
10. **Admin Desk** (12 tests) — EA, Knowledge Manager
11. **E2E Flows** (20 tests) — Full stack: onboarding, bank ingestion, HITL approval
12. **LLM Evals** (15 evals) — LLM-as-judge for tone, jargon, actionability

**Test Status Target:** ~189 tests passing

**v4.2.0 Status:** v4.2.0-alpha — Internal Ops Virtual Office Only.

See [`docs/TESTING_ARCHITECTURE.md`](./docs/TESTING_ARCHITECTURE.md) for complete testing docs.

### Add a New Desk Employee

1. Create `apps/ai/src/agents/desks/your_agent.py`
2. Define role, tools, APIs, output format (Pydantic)
3. Register in Chief of Staff routing
4. Add tests in `apps/ai/tests/test_your_agent.py`
5. Run: `uv run pytest tests/test_your_agent.py -v`

### Environment Variables

```bash
# LLM (swap provider by changing these 3 lines)
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-...
LLM_MODEL=openai/gpt-4o-mini

# Telegram
TELEGRAM_BOT_TOKEN=...

# Neo4j / Graphiti
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sarthi

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Sandbox
SANDBOX_URL=http://localhost:5001
SANDBOX_SECRET=...
```

---

## v4.2 Roadmap

### Phase 1 (IN PROGRESS)
- [ ] LLM unification (`get_llm_client` everywhere)
- [ ] Graphiti + Neo4j full integration
- [ ] 125 tests passing

### Phase 2
- [ ] Finance Desk (CFO + Bookkeeper + AR/AP + Payroll)
- [ ] People Desk (HR + Internal Recruiter)
- [ ] Legal Desk (Contracts + Compliance)
- [ ] 150 tests passing

### Phase 3
- [ ] Intelligence Desk (BI + Policy Watcher)
- [ ] IT & Tools Desk (IT Admin)
- [ ] Admin Desk (EA + Knowledge Manager)
- [ ] 175 tests passing

### Phase 4
- [ ] Chief of Staff routing (internal-only)
- [ ] BusinessOS workflow (Go + Temporal)
- [ ] HITL gate E2E test
- [ ] 20/20 E2E tests green

### Phase 5: v4.2.0
- [ ] One real founder onboards
- [ ] Uses at least 2 desks
- [ ] Reports "This saved me admin time"
- → **TAG v4.2.0**

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [PRD](./docs/PRD.md) | Complete product requirements, agent specs (v4.2) |
| [INTERNAL_OPS_SCOPE](./docs/INTERNAL_OPS_SCOPE.md) | What we do / don't do boundary |
| [TESTING](./docs/TESTING_ARCHITECTURE.md) | Testing strategy, ~189 test targets |
| [Architecture](./docs/architecture/) | System design, data flow |
| [API Docs](./docs/api/) | All endpoints, request/response schemas |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Write tests first (RED → GREEN → REFACTOR)
4. Commit with conventional commits
5. Open a PR

**Note:** All agents must have 100% test coverage before merge.

---

## License

MIT License — see [LICENSE](LICENSE) file.

---

**Built with:** Go 1.24 • Python 3.13 • Temporal • Redpanda • PostgreSQL • Qdrant • Neo4j • Graphiti • Azure OpenAI • LangGraph • DSPy • Pydantic v2

**Status:** ✅ v4.2.0-alpha — Internal Ops Virtual Office Only
