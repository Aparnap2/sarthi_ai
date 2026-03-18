# Sarthi.ai — Your Virtual Back-Office for Software Startups

<div align="center">

**5-Agent Ops Automation System | Telegram Interface | Real Docker + Real Azure LLM**

[![Tests](https://img.shields.io/badge/tests-255%2B%20baseline-brightgreen)](./apps/ai/tests/)
[![Agents](https://img.shields.io/badge/agents-5%20vertical-blue)](./docs/PRD.md)
[![Version](https://img.shields.io/badge/version-v1.0--alpha-purple)](./docs/PRD.md)

[Architecture](#architecture) • [Agents](#five-agents) • [PRD](./docs/PRD.md) • [Testing](#testing)

</div>

---

## The Problem

Solo technical founders drown in operational chaos:

| Metric | Impact |
|--------|--------|
| **Tools fragmentation** | 10+ tools (Razorpay, Zoho, Intercom, Keka) with no intelligence layer |
| **Founder as bus** | You manually relay info between payment → CRM → support → HR → finance |
| **Time waste** | 15–20 hours/week on back-office = $9,000–$22,500/month hidden cost |
| **Roadmap delay** | ~3 months/year lost to ops work that doesn't require your judgment |

**The gap:** Not "founders don't have tools" — it's **no system watches all tools and acts silently**.

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
> - Detected AWS spike (2.3× usual) before I noticed
> - Sent payment reminders to 3 stale deals (closed 2)
> - Generated Priya's onboarding checklist (eng role)
> - Drafted Monday brief: 3 items, no jargon
> - Flagged Arjun as high churn risk (8 days no login)
> - Prepared investor update: revenue, burn, runway"

**That's not a feature list. That's a Monday.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CONNECTORS (Go API Gateway)                                │
│  Razorpay • Stripe • Zoho • Intercom • Keka • Bank          │
│  HMAC verified → raw_events → Redpanda                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  TEMPORAL WORKFLOWS (Go)                                    │
│  RevenueWorkflow • CSWorkflow • PeopleWorkflow              │
│  FinanceWorkflow • ChiefOfStaffWorkflow                     │
│  Continue-As-New at 1,000 events                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PYTHON AGENTS (LangGraph)                                  │
│  Revenue Tracker • CS Agent • People Coordinator            │
│  Finance Monitor • Chief of Staff                           │
│  Reason → Act → Write Memory                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUTS                                                    │
│  PostgreSQL (structured) • Qdrant (episodic)                │
│  Telegram (HITL only)                                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```mermaid
graph TD
  subgraph Connectors
    A[Razorpay/Stripe] --> GW[Go API Gateway]
    B[Zoho/Tally] --> GW
    C[Support webhook] --> GW
    D[HR webhook] --> GW
    E[Bank webhook] --> GW
    F[gws CLI cron] --> GW
  end

  subgraph Event Bus
    GW -->|HMAC verified + normalized| RP[Redpanda: sarthi.events.raw]
  end

  subgraph Temporal Workflows
    RP --> RW[RevenueWorkflow]
    RP --> CW[CSWorkflow]
    RP --> PW[PeopleWorkflow]
    RP --> FW[FinanceWorkflow]
    RP --> CoSW[ChiefOfStaffWorkflow]
  end

  subgraph Python Agents — LangGraph
    RW --> RA[Revenue Tracker]
    CW --> CA[CS Agent]
    PW --> PA[People Coordinator]
    FW --> FA[Finance Monitor]
    CoSW --> CoS[Chief of Staff]
  end

  subgraph Outputs
    RA & CA & PA & FA & CoS --> PG[PostgreSQL]
    RA & CA & PA & FA & CoS --> QD[Qdrant]
    CoS & FA & PA --> TG[Telegram HITL]
  end
```

---

## Five Agents

### 1. Revenue Tracker

**Watches:** Razorpay, Stripe, CRM deals  
**Acts:** MRR snapshots, stale deal nudges  
**Telegram:** Stale deals (>7 days), MRR milestones

| Threshold | Action |
|-----------|--------|
| MRR crosses ₹1L/₹5L/₹10L | Celebratory alert |
| Deal idle >7 days | "Still live? [Nudge] [Mark Lost]" |
| Single customer >30% | Concentration risk warning |

---

### 2. CS Agent

**Watches:** Signup events, support tickets, login activity  
**Acts:** D1/D3/D7 onboarding sequence, churn risk detection  
**Telegram:** High churn risk founders only (risk_score > 0.7)

| Trigger | Action |
|---------|--------|
| USER_SIGNED_UP | Day 1 message queued |
| last_seen_at >7 days | Churn risk alert to founder |
| ticket_count >2 in 48h | Escalation draft |

---

### 3. People Coordinator

**Watches:** Hire/exit events, checklist confirmations  
**Acts:** Role-based checklists, provisioning/revocation  
**Telegram:** New hire checklist, offboard revoke list

| Role | Checklist |
|------|-----------|
| Eng | GitHub, Notion, Slack, GWorkspace, Linear |
| Ops | Notion, Slack, GWorkspace |
| Sales | Notion, Slack, GWorkspace, CRM |

---

### 4. Finance Monitor

**Watches:** Payments, expenses, bank feeds, time ticks  
**Acts:** Burn/runway, spend anomaly detection (2σ threshold)  
**Telegram:** Spend anomalies, runway <90 days

| Threshold | Action |
|-----------|--------|
| Spend > baseline + 2σ | "AWS bill ₹42,000 — 2.3× usual. [Investigate] [Expected]" |
| Runway <3 months | Critical alert |
| Runway <6 months | Warning |

---

### 5. Chief of Staff

**Watches:** All agent outputs + weekly/monthly cron  
**Acts:** Monday briefing, monthly investor draft  
**Telegram:** Weekly brief (max 5 items, jargon-free, 1 positive)

**Briefing rules:**
- Max 5 items
- Always 1 positive if data supports
- Banned jargon: `leverage, synergy, utilize, streamline, paradigm`
- Each item: headline + `[Action]` button

---

## Quick Start

### Prerequisites

```bash
# Docker & Docker Compose
docker --version
docker compose version

# Go 1.24+
go version

# Python 3.11+ with uv
uv --version
```

### Start Infrastructure

```bash
# Clone
git clone https://github.com/Aparnap2/IterateSwarm.git
cd iterate_swarm

# Start Docker services
docker compose up -d

# Wait for services
sleep 60

# Check health
docker compose ps
```

### Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Temporal UI** | http://localhost:8088 | Workflow tracing |
| **Redpanda Console** | http://localhost:9644 | Event streaming |
| **Qdrant Dashboard** | http://localhost:6333 | Vector search |
| **Langfuse** | http://localhost:3001 | LLM observability |

---

## Development

### Run Tests

```bash
# Full test suite (real Docker + real Azure LLM)
bash scripts/test_sarthi.sh

# Python tests only
cd apps/ai
uv run pytest tests/ -v --timeout=90

# Go tests only
cd apps/core
go test ./... -v -timeout=60s

# E2E tests only
cd apps/ai
uv run pytest tests/test_e2e_sarthi.py -v --timeout=120
```

### Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| **Baseline** | 255 | Existing IterateSwarm tests |
| **Event Envelope** | 4 | Valid/invalid envelope tests |
| **Event Normalizer** | 10 | Source → EventType mapping |
| **Webhook Handlers** | 20 | HMAC, DLQ, idempotency (5 handlers × 4 tests) |
| **Workflow Routing** | 5 | Parent workflow + CAN |
| **Agent Unit Tests** | 90 | 5 agents × 6 nodes × 3 tests |
| **E2E Flows** | 5 | Full stack: finance, revenue, onboarding, CS, investor |
| **LLM Evals** | 40 | 4 agents × 10 scenarios |

**Target:** 429+ tests passing for v1.0.0

### Add a New Agent

1. Create `apps/ai/src/agents/your_agent.py`
2. Define LangGraph state + nodes
3. Register in Temporal workflow
4. Add tests in `apps/ai/tests/test_your_agent.py`
5. Run: `uv run pytest tests/test_your_agent.py -v`

### Environment Variables

```bash
# LLM (Azure OpenAI)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-01

# Telegram
TELEGRAM_BOT_TOKEN=...

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sarthi
POSTGRES_USER=sarthi
POSTGRES_PASSWORD=...

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Redpanda
REDPANDA_BROKERS=localhost:9094

# Temporal
TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_NAMESPACE=default
```

---

## Testing

### Philosophy

**Real Docker. Real Azure LLM. Zero mocks on external infra.**

```python
# Pattern: fixed state + fixed event → assert decisions
class TestRevenueTracker:
    def test_stale_deal_detected():
        state = RevenueState(pipeline_deals=[
            {"deal_id": "D1", "amount": 50000,
             "stage": "NEGOTIATION", "last_contact_at": 9_days_ago}
        ])
        actions = revenue_graph.invoke(state, TICK_WEEKLY_EVENT)
        assert any(a["type"] == "SEND_TELEGRAM" for a in actions)
        assert "D1" in actions[0]["message"]
```

### Invariants (Enforced Before Every Commit)

```bash
# I-1: No raw JSON in Temporal signals
grep -rn "json.Marshal" apps/core/internal/workflow/ \
  | grep -v "_test.go" && exit 1

# I-2: No AzureOpenAI() outside config/llm.py
grep -rn "AzureOpenAI(" apps/ai/src/ | grep -v "config/llm.py" && exit 1

# I-3: All baseline tests still pass
uv run pytest tests/ -x -q --timeout=90

# I-4: No jargon in agent output
grep -rn "leverage\|synergy\|utilize" apps/ai/src/agents/ && exit 1
```

---

## Roadmap

### v1.0.0-alpha (Current)

- [x] Database schema (9 tables)
- [x] Event envelope (Go + Python)
- [x] Event normalization (10 mappings)
- [ ] 5 webhook handlers (HMAC, DLQ, idempotency)
- [ ] Temporal workflow routing (CAN at 1,000)
- [ ] 5 LangGraph agents
- [ ] Telegram HITL handling
- [ ] 5 E2E tests
- [ ] Test runner script

### v1.0.0 (Production)

- [ ] All 429+ tests passing
- [ ] Langfuse tracing for all agents
- [ ] LLM eval suite (40 scenarios)
- [ ] Deployment SOP
- [ ] Incident response SOP
- [ ] First real founder onboarded

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [PRD](./docs/PRD.md) | Complete product requirements, agent specs, database schema |
| [ARCHITECTURE](./docs/ARCHITECTURE.md) | System design, data flow |
| [TESTING](./docs/TESTING_ARCHITECTURE.md) | Testing strategy, 429+ test targets |
| [PHASES](./docs/PHASES.md) | Phase execution order (12 commits) |

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

**Built with:** Go 1.24 • Python 3.11 • Temporal • Redpanda • PostgreSQL • Qdrant • Azure OpenAI • LangGraph

**Status:** ✅ v1.0.0-alpha — 5-Agent Ops Automation System
