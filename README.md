# Sarthi.ai — Your Virtual Back-Office OS

<div align="center">

**Internal ops OS powered by self-correcting, context-aware, proactive, obedient vertical agentic AI**

[![Tests](https://img.shields.io/badge/tests-151%2B%20target-brightgreen)](./apps/ai/tests/)
[![Agents](https://img.shields.io/badge/agents-17%20vertical-blue)](./docs/PRD.md)
[![Cost](https://img.shields.io/badge/cost-%240%2Fmonth-green)](./docs/PRD.md)
[![Version](https://img.shields.io/badge/version-v4.1.0--alpha-purple)](./docs/PRD.md)

[Live Demo](#) • [Architecture](#architecture) • [Agents](#the-complete-agent-hierarchy-v41) • [API Docs](./docs/api/) • [PRD](./docs/PRD.md) • [Phases](./docs/PHASES.md)

</div>

---

## The Problem

Early-stage startups drown in operational chaos:

| Metric | Impact |
|--------|--------|
| **Tools fragmentation** | Average startup uses **15 different tools** across payroll, finance, HR, compliance |
| **Founder time waste** | **15–20 hours/week** on back-office = **$9,000–$22,500/month** hidden cost |
| **Roadmap delay** | Back-office drag delays product roadmaps by **~3 months per year** |

**The gap:** Not "startups don't have tools" — it's **15 disconnected tools with no intelligence layer connecting them**.

---

## The Solution

**Sarthi** is the intelligence layer that sits above all your existing tools and runs the ops *between* them.

```
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
> - Found an R&D tax credit I didn't know about (£35k value)
> - Applied to an Innovate UK grant on my behalf"

**That's not a feature list. That's a Wednesday.**

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
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2 — INTELLIGENCE (observe + advise)                       │
│  CFO | BI | Risk | Market | Fundraise | Tax Intel | Grant      │
│  | Jurisdiction                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3 — OPERATIONS (execute, not advise)                      │
│  Finance | Accounting | Legal | HR | RevOps | Admin            │
│  | Procurement | Cap Table | Grant Ops                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 4 — DATA LAYER (ingest + memory, never surfaces)          │
│  Ingestion | Memory (Qdrant + Neo4j) | Crawler | Connector      │
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
| **Market Crawling** | Crawl4AI (Docker, OSS) | $0 |

**Total monthly cost for MVP: $0**

---

## The Complete Agent Hierarchy (v4.1)

### Tier 1: Chief of Staff Agent

**Role:** The face of Sarthi. Routes work, synthesizes intelligence, manages the relationship.

**Output:**
- "Here's what I found + one action"
- "I handled X — here's what I did"
- "I need your decision on X — here's context"
- "Weekly briefing: X handled, Y needs you"

---

### Tier 2: Intelligence Agents (8 agents)

#### CFO Agent
- 13-week rolling cash flow forecast
- Burn rate + runway calculation
- Unit economics: CAC, LTV, payback
- Scenario modeling: "what if we hire in March?"

**Fires when:** Runway < 6 months, burn spikes >15%, margin goes negative

#### BI Agent
- Customer cohort analysis (retention, churn)
- Revenue concentration risk
- Anomaly detection across all data sources
- Cross-source pattern correlation

**Fires when:** Churn pattern detected, one customer >30% revenue, usage predicts churn

#### Risk Agent
- GST, TDS, advance tax deadlines (India)
- VAT, Corporation Tax, PAYE (UK)
- PF, ESIC, PT compliance
- Contract expiry tracking
- DPDP Act / GDPR compliance

**Fires when:** Deadline <14 days, contract expires <30 days, regulatory change

#### Market Agent
- Competitor pricing + feature tracking
- Funding announcements in sector
- Hiring signals (what competitors building)
- Emerging customer pain points

**Fires when:** Competitor changes pricing, major funding in space, regulation affects them

#### Fundraise Readiness Agent (NEW v4.1)
- Fundraising readiness score (0-100)
- Data room completeness audit
- Financial model review
- Cap table health check
- Pitch deck gap analysis

**Fires when:** Readiness score <70, data room incomplete, cap table red flags

#### Tax Intelligence Agent (NEW v4.1)
- R&D tax credit identification (US, UK, EU)
- QSBS tracking (US Section 1202)
- Patent box optimization (UK, EU)
- GST input credit optimization (India)
- Transfer pricing risk assessment

**Fires when:** R&D credit eligibility (£/$/₹50k+), QSBS window closing

#### Grant & Credit Agent (NEW v4.1)
- SBIR/STTR grant matching (US)
- Innovate UK grant matching
- Horizon Europe grant matching
- State-level incentive tracking
- Application deadline tracking

**Fires when:** Grant match score >80%, deadline <30 days

#### Jurisdiction Agent (NEW v4.1)
- Entity formation recommendation
- Tax residency optimization
- Permanent establishment risk
- Local compliance requirements
- Banking/payroll recommendations

**Fires when:** Expansion signal detected, PE risk triggered

---

### Tier 3: Operations Agents (9 agents)

#### Finance Ops Agent
- Expense categorization (auto)
- Invoice generation + payment reminders
- GST/VAT return data prep
- Bank vs books reconciliation

**HITL:** Low-risk auto, medium 1-tap, high explicit confirm

#### Accounting Ops Agent (NEW v4.1)
- Month-end close checklist
- Accrual calculations
- Depreciation schedules
- Consolidated financial statements
- Audit prep workpapers

#### HR Ops Agent
- Onboarding checklist execution
- Offer letter generation
- Payroll data prep
- PF/ESIC/pension filing reminders

#### Legal Ops Agent
- NDA generation (templates)
- Contract review summary
- MCA/Companies House filing reminders
- Term sheet summary

#### RevOps Agent
- CRM hygiene (auto-update stale deals)
- Pipeline velocity + stall detection
- Proposal generation
- Customer health scoring

#### Admin Ops Agent
- Meeting prep + action items
- SOP documentation
- Tool stack audit
- Subscription management

#### Procurement Ops Agent (NEW v4.1)
- Vendor quote comparison
- Contract renewal tracking (90-day warning)
- Spend analysis by category
- Negotiation prep (benchmarks)

#### Cap Table Ops Agent (NEW v4.1)
- Cap table maintenance
- Option pool tracking
- Dilution scenario modeling
- SAFE/convertible tracking
- Exit waterfall analysis

#### Grant Ops Agent (NEW v4.1)
- Grant application drafting
- Supporting document collection
- Milestone tracking (post-award)
- Reporting compliance

---

### Tier 4: Data Layer (Invisible)

- **IngestionAgent:** Normalizes all data (bank PDF, accounting, Notion, Slack, Stripe)
- **MemoryAgent:** Qdrant + Neo4j + Graphiti — company's long-term brain (vector + temporal)
- **CrawlerAgent:** Crawl4AI + Firecrawl for external intelligence
- **ConnectorAgent:** OAuth + API connections to all tools

---

## The Self-Correcting System

**How Sarthi gets smarter about YOUR company over time:**

1. **AGENT ACTS** → Finance Ops sends payment reminder to Client X
2. **OUTCOME OBSERVED** → Client X pays within 24 hours
3. **MEMORY UPDATED** → "Client X responds to reminders within 24h. High relationship quality." (Qdrant + Neo4j)
4. **FUTURE ADJUSTED** → Next time: warmer tone, less formal timing
5. **CONTEXT DRIFT DETECTED** → "You've raised prices twice but win rate unchanged. Pricing headroom?"

**Not generic AI. Company-specific intelligence.**

---

## Global Expansion

### Market Entry Order

| Phase | Market | Key Features |
|-------|--------|--------------|
| **v4.0.0** | 🇮🇳 India | GST, TDS, PF, ESIC, Razorpay, Zoho |
| **v4.1.0** | 🇺🇸 United States | Delaware C-Corp, QSBS, R&D credits, Stripe, Gusto |
| **v4.1.0** | 🇬🇧 United Kingdom | UK Ltd, VAT, Innovate UK, Xero, Wise |
| **v4.1.0** | 🇪🇺 European Union | VAT MOSS, Horizon Europe, GDPR, Deel |
| **v4.2.0** | 🇸🇬 Southeast Asia | Singapore Pte, PDPA, CPF, EDB grants |

### Jurisdiction-Specific Compliance

| Feature | India | US | UK | EU |
|---------|-------|----|----|----|
| **Tax** | GST, TDS | Sales tax | VAT, PAYE | VAT MOSS |
| **Grants** | DST, BIRAC | SBIR/STTR | Innovate UK | Horizon Europe |
| **Credits** | Limited | R&D, QSBS | R&D, Patent Box | R&D, Patent Box |
| **Privacy** | DPDP Act | CCPA | UK GDPR | EU GDPR |

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
# All tests (~151+ target)
cd apps/ai
uv run pytest tests/ -v --timeout=120

# Specific groups
uv run pytest tests/test_sarthi_tdd.py -v           # TDD tests (~80)
uv run pytest tests/test_e2e_saarathi.py -v         # E2E flows (20)
uv run pytest tests/test_llm_eval.py -v             # LLM evals (15)
uv run pytest tests/test_tier2_agents.py -v         # Tier 2 agents (40)
uv run pytest tests/test_tier3_agents.py -v         # Tier 3 agents (45)

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

**Test Categories:**
1. **Infrastructure Health** (6 tests) — Azure LLM, Qdrant, Neo4j, PostgreSQL reachable
2. **Memory Agent** (15 tests) — Embeddings, Qdrant upsert, Neo4j graph, semantic search
3. **Chief of Staff** (5 tests) — Plain language, correct routing, ToneFilter fidelity
4. **Bank Parser** (8 tests) — HDFC/ICICI/SBI CSV, Docling accurate mode, multi-format
5. **CFO Agent** (5 tests) — Runway calculation, proactive alert, scenario modeling
6. **Tier 2 Agents** (40 tests) — BI, Risk, Market, Fundraise, Tax, Grant, Jurisdiction
7. **Tier 3 Agents** (45 tests) — Finance, Accounting, HR, Legal, RevOps, Admin, Procurement, Cap Table, Grant Ops
8. **E2E Flows** (20 tests) — Full stack: onboarding, reflection, market signal, sandbox, calibration
9. **LLM Evals** (15 evals) — LLM-as-judge for tone, jargon, actionability

**Test Status Target:** 151+ tests passing

**v4.1.0 Status:** v4.1.0-alpha — Global expansion, Neo4j + Graphiti locked in.

See [`docs/TESTING_ARCHITECTURE.md`](./docs/TESTING_ARCHITECTURE.md) for complete testing docs.

### Add a New Agent

1. Create `apps/ai/src/agents/your_agent.py`
2. Define role, tools, APIs, output format (Pydantic)
3. Register in `supervisor_agent.py`
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

## v4.1 Roadmap

### Phase 2 (IN PROGRESS)
- [ ] LLM unification (`get_llm_client` everywhere)
- [ ] Graphiti + Neo4j full integration
- [ ] 125 tests passing

### Phase 3
- [ ] ToneFilter DSPy-compiled (4 signatures)
- [ ] Telegram inline keyboards
- [ ] Pydantic findings schemas
- [ ] Bank statement parser (multi-format)
- [ ] 160 tests passing

### Phase 4
- [ ] CFO agent (complete)
- [ ] Risk agent (multi-jurisdiction)
- [ ] Jurisdiction agent (NEW)
- [ ] Fundraise readiness agent (NEW)
- [ ] Tax intelligence agent (NEW)
- [ ] Grant & credit agent (NEW)
- [ ] 195 tests passing

### Phase 5
- [ ] All Tier 3 ops agents (9 total)
- [ ] BusinessOS workflow (Go + Temporal)
- [ ] Onboarding workflow (Go)
- [ ] HITL gate E2E test
- [ ] 20/20 E2E tests green

### Phase 6
- [ ] DSPy eval suite (≥13/15 pass)
- [ ] Circuit breaker (all external calls)
- [ ] GitHub Actions CI
- [ ] Langfuse traces < 8s p95

### Phase 7: v4.0.0
- [ ] One real founder onboards
- [ ] Receives real CFO finding
- [ ] Reports "This saved me time"
- → **TAG v4.0.0**

### Phase 8: v4.1.0
- [ ] Jurisdiction agent live (US + UK + EU)
- [ ] Grant agent: SBIR, Innovate UK, Horizon Europe
- [ ] First non-India founder onboarded
- → **TAG v4.1.0**

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [PRD](./docs/PRD.md) | Complete product requirements, agent specs (v4.1) |
| [PHASES](./docs/PHASES.md) | Phase execution order (PHASE 0-8) |
| [TESTING](./docs/TESTING_ARCHITECTURE.md) | Testing strategy, 151+ test targets |
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

**Status:** ✅ v4.1.0-alpha — Global expansion, Neo4j + Graphiti locked in
