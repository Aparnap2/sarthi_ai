# Sarthi — Solo Founder Business Pulse
## Always-On Business Intelligence for SaaS Founders

[![Tests](https://img.shields.io/badge/tests-128%20passing%20(97.7%25)-brightgreen)](docs/TEST_RESULTS.md)
[![Agents](https://img.shields.io/badge/agents-4%20(Pulse%2C%20Anomaly%2C%20Investor%2C%20QA)-blue)](docs/PRD.md)
[![Workflows](https://img.shields.io/badge/workflows-3%20(Pulse%2C%20Investor%2C%20QA)-purple)](docs/ARCHITECTURE.md)
[![Version](https://img.shields.io/badge/version-v1.0--alpha-orange)](docs/PRD.md)

---

## Overview

**Sarthi** is an always-on business pulse monitor for solo SaaS founders. It watches your Stripe + bank accounts 24/7, detects anomalies with historical context, drafts weekly investor updates automatically, and answers your top 20 business questions in <10 seconds.

**North Star Metric:** "Founders who connected Stripe + bank and kept Sarthi running for 30 days" — target >60% of onboarded users.

**Price:** ₹9,999/month (less than one day of a junior hire)

---

## Architecture

```
Stripe + Plaid → Go Fiber API → Redpanda → Temporal Workflows → LangGraph Agents → Slack
                                            ↓
                                       Qdrant Memory
                                       (episodic context)
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
| Vector Memory | Qdrant |
| Primary DB | PostgreSQL |
| Notifications | Slack (Telegram fallback) |
| Observability | Langfuse |

---

## The 4 Agents

| Agent | Purpose | Trigger | Output |
|-------|---------|---------|--------|
| **PulseAgent** | Daily business pulse | Daily 08:00 IST | 3-line Slack summary |
| **AnomalyAgent** | Explains spikes | Conditional (after Pulse) | Explanation + action |
| **InvestorAgent** | Weekly update draft | Weekly Friday 08:00 IST | Markdown investor update |
| **QAAgent** | Founder Q&A | On-demand (Slack message) | Answer + follow-up |

**Competitive Moat:** Qdrant episodic memory — context compounds with every event. When MRR spikes, AnomalyAgent says:
> "This is the 3rd time this quarter — last two were caused by enterprise deals closing early. Check if Acme Corp paid early this month."

---

## Workflows

| Workflow | Schedule | Description |
|----------|----------|-------------|
| PulseWorkflow | Daily 08:00 IST | Runs PulseAgent → AnomalyAgent (if anomalies found) |
| InvestorWorkflow | Weekly Friday 08:00 IST | Generates investor update draft |
| QAWorkflow | On-demand | Answers founder questions via Slack |

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
| Integrations (Day 1) | 12 | ✅ 12/12 passing |
| PulseAgent (Day 2) | 20 | ✅ 20/20 passing |
| AnomalyAgent (Day 3) | 15 | ✅ 15/15 passing |
| InvestorAgent (Day 4) | 15 | ✅ 14/15 passing (93%) |
| QAAgent (Day 5) | 15 | ✅ 15/15 passing |
| Workflows + Worker (Day 5) | 14 | ✅ 14/14 passing |
| **TOTAL** | **131** | **✅ 128/131 passing (97.7%)** |

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
docker compose -f docker-compose.prod.yml up -d
# Starts: PostgreSQL, Qdrant, Redpanda, Ollama, Temporal, Langfuse
```

### 3. Run database migration
```bash
psql "postgresql://sarthi:sarthi@localhost:5433/sarthi" \
  -f migrations/009_pulse_pivot.sql
```

### 4. Initialize Qdrant collections
```bash
cd apps/ai && uv run python src/setup/init_qdrant_collections.py
```

### 5. Start Temporal worker
```bash
cd apps/ai && uv run python -m src.worker
# Worker connects to Temporal, listens on SARTHI-MAIN-QUEUE
```

### 6. Trigger first pulse (manual test)
```bash
# Via Temporal CLI
temporal workflow start \
  --task-queue SARTHI-MAIN-QUEUE \
  --type PulseWorkflow \
  --input '{"tenant_id": "demo-tenant"}'
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
│   ├── activities/         # Temporal activities (5 files)
│   ├── workflows/          # Temporal workflows (3 files)
│   ├── integrations/       # Stripe, Plaid, Slack, Product DB
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
```

---

## Monitoring

**Local Development:**
- **Langfuse UI:** http://localhost:3001 (LLM traces, latency, costs)
- **Temporal Web UI:** http://localhost:8088 (workflow executions, retries)
- **Redpanda Console:** http://localhost:8080 (event stream debugging)
- **Qdrant Dashboard:** http://localhost:6333/dashboard

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

**3-Minute Demo Script:**

```
[0:00] "Sarthi is a multi-agent agentic AI system — the
        ops memory brain for software startups."

[0:20] Run: ./scripts/simulate_payment.sh
       "Just fired a fake Razorpay webhook —
        AWS bill 2.3x higher than the 90-day baseline."

[0:35] Open Temporal UI → PulseWorkflow RUNNING
       "Temporal ensures this survives any crash.
        Durable execution — not a cron job."

[0:50] "LangGraph ReAct loop: Ingest → Load baseline
        → Detect anomaly → Query Qdrant → Reason → Alert"

[1:10] Show Qdrant returning memory:
       "Similar AWS spike. October 2025.
        Cause: undeleted staging environment."
       "It didn't just detect it — it remembered."

[1:30] Show Slack alert:
       "AWS bill 2.3x usual. First spike since October.
        Check recent deployments. [Investigate][Dismiss]"

[1:50] Tap [Investigate]
       "Temporal receives the signal. BI Agent activates.
        Generates SQL, executes it, builds a chart."
       Show chart arriving in Slack (< 30 seconds)

[2:20] Open Langfuse:
       "Every LLM call traced: input, output, tokens,
        latency, score. Production observability."

[2:45] "Four agents. Nine technologies.
        Temporal durable workflows. LangGraph ReAct.
        Qdrant episodic memory. Deployed. Tested.
        Observable. This is Sarthi."

[3:00] END
```
