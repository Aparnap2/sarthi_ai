# Sarthi — Product Requirements Document
## v1.0 | 5-Agent Ops Automation System for Software Startups

***

## 1. Executive Summary

Sarthi is a multi-agent back-office automation system for software startup founders. It watches payment providers, CRM, support channels, HR events, bank feeds, and the founder's calendar — then acts silently on routine tasks and sends a single Telegram message only when genuine judgment is required. It integrates with tools founders already use. It replaces nothing. It eliminates the founder as the manual communication bus between all of them.

| Attribute | Value |
|---|---|
| Interface | Telegram (only surface the founder ever sees) |
| Foundation | IterateSwarm v4.2.0-alpha (255 tests passing) |
| Language stack | Go (gateway) + Python (agents) |
| Orchestration | Temporal (durable workflows) |
| Event bus | Redpanda |
| Memory | Qdrant (episodic) + PostgreSQL (structured) |
| Target | Solo technical founders, B2B SaaS, India |

***

## 2. System Architecture

### 2.1 Core Data Flow

```
External event
  → Go webhook handler (validate HMAC, normalize, store raw)
  → Redpanda: sarthi.events.raw
  → Temporal: route to correct workflow
  → LangGraph agent: reason, act, write memory
  → Outputs: PostgreSQL row + Qdrant memory + Telegram (only if HITL needed)
```

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

### 2.2 Five Agents — Responsibilities

| Agent | Primary Input | Primary Output | Telegram? |
|---|---|---|---|
| **Revenue Tracker** | Payment events, CRM updates | MRR snapshot, stale deal nudges | Stale deals, MRR milestones |
| **CS Agent** | Signup events, support tickets, time ticks | Onboarding sequences, churn risk | High-churn risk founders only |
| **People Coordinator** | Hire/exit events, checklist confirmations | Provisioning/revocation checklist | New hire checklist, offboard list |
| **Finance Monitor** | Payment + expense events, bank feed, time ticks | Burn/runway, anomaly alerts | Spend anomalies, runway < 90 days |
| **Chief of Staff** | All agent outputs + cron | Weekly briefing, investor draft | Weekly brief, monthly investor update |

### 2.3 Shared Infrastructure (built once, reused by all)

**Go API routes:**
```
POST /webhooks/payments     → sarthi.events.raw
POST /webhooks/crm          → sarthi.events.raw
POST /webhooks/support      → sarthi.events.raw
POST /webhooks/hr           → sarthi.events.raw
POST /webhooks/bank         → sarthi.events.raw
GET  /health
```

**Redpanda topics:**
```
sarthi.events.raw           — all normalized inbound events
sarthi.events.normalized    — post-routing classified events
sarthi.agent.outputs        — agent action results (consumed by CoS)
```

**Temporal activities (shared):**
```
CallLangGraph(agent, event)
SendTelegram(tenant, message, buttons)
QueryPostgres(query, params)
QueryQdrant(collection, query)
UpsertQdrant(collection, vector, payload)
EmitEvent(topic, payload)
```

**Python AI service:**
```
POST /agent/:name/run
Input:  { state, event }
Output: { actions, new_state, memories_to_write }
```

***

## 3. Agent LLD

### 3.1 Revenue Tracker

**State:**
```python
@dataclass
class RevenueState:
    tenant_id: str
    last_7d_revenue: float
    last_30d_mrr: float
    pipeline_deals: list[dict]   # {deal_id, amount, stage, last_contact_at}
    alerts_sent: list[dict]      # {alert_type, target_id, sent_at}
```

**Trigger events:**
```
PAYMENT_SUCCESS
SUBSCRIPTION_CREATED | UPDATED | CANCELED
CRM_DEAL_CREATED | UPDATED
TIME_TICK_WEEKLY
```

**LangGraph nodes:**
```
IngestEvent     → classify event type, extract amount + customer
UpdateMetrics   → recompute MRR + 7d/30d windows from PostgreSQL
DetectStaleDeals → deals with last_contact_at > 7 days
DecideAlerts    → which founders to ping + why (milestone / stale / anomaly)
WriteMemory     → write weekly summary to Qdrant
EmitActions     → queue Telegram messages + emit WEEKLY_REVENUE_SUMMARY
```

**Key thresholds:**
- MRR milestones: ₹1L, ₹5L, ₹10L, ₹50L, ₹1Cr
- Stale deal: `last_contact_at > 7 days AND stage != CLOSED`
- Concentration risk: single customer > 30% of last 90d revenue

**Actions:**
```python
SendTelegram("Deal with Acme idle 9 days. Still live? [Nudge] [Mark Lost]")
EmitEvent("WEEKLY_REVENUE_SUMMARY", {mrr, deals, anomalies})
UpsertQdrant("revenue_summary", weekly_text_embedding)
```

***

### 3.2 Customer Success Agent

**State:**
```python
@dataclass
class CSState:
    tenant_id: str
    customer_id: str
    signup_at: datetime
    last_seen_at: datetime
    onboarding_stage: Literal["WELCOME", "CHECKIN", "ACTIVATION", "DONE"]
    risk_score: float   # 0–1
```

**Trigger events:**
```
USER_SIGNED_UP
USER_LOGGED_IN
SUPPORT_TICKET_CREATED
TIME_TICK_D1 | D3 | D7
```

**LangGraph nodes:**
```
OnSignup          → initialize CSState, queue D1 message
OnTimeTick        → check stage, decide next touchpoint
OnSupportTicket   → classify (FAQ vs real issue), draft reply
RiskAssessment    → infer churn risk from inactivity + ticket count
EmitActions       → user messages + founder alert if risk_score > 0.7
```

**Key thresholds:**
- High churn risk: `last_seen_at > 7 days` AND `onboarding_stage != DONE`
- Ticket escalation: `ticket_count > 2 in 48h`

**Actions:**
```python
SendTelegram(user_telegram, "Day 1: Quick tip to get your first win in 10 min →")
SendTelegram(founder_telegram, "User Arjun hasn't logged in for 8 days. High churn risk. [Send Nudge] [Mark OK]")
UpsertQdrant("cs_case", conversation_summary_embedding)
```

***

### 3.3 People Coordinator

**State:**
```python
@dataclass
class PeopleState:
    employee_id: str
    tenant_id: str
    status: Literal["ONBOARDING", "ACTIVE", "OFFBOARDING"]
    checklist: dict   # {slack_invited, notion_added, github_added,
                      #  gworkspace_created, license_provisioned}
    role_function: Literal["eng", "ops", "sales", "design"]
```

**Trigger events:**
```
EMPLOYEE_CREATED
EMPLOYEE_TERMINATED
CHECKLIST_ITEM_CONFIRMED
TIME_TICK_D1 | D3
```

**LangGraph nodes:**
```
OnHireEvent        → create checklist based on role_function
GenerateChecklist  → eng checklist ≠ ops checklist ≠ sales checklist
ProgressTracking   → track confirmed items, compute % complete
NagLoop            → send reminder if item incomplete after 24h
Offboarding        → mirror of onboarding, generate revoke list
```

**Role-based checklists:**

| Tool | Eng | Ops | Sales |
|---|---|---|---|
| GitHub | ✅ | — | — |
| Notion | ✅ | ✅ | ✅ |
| Slack | ✅ | ✅ | ✅ |
| Google Workspace | ✅ | ✅ | ✅ |
| Linear/Jira | ✅ | — | — |
| CRM | — | — | ✅ |

**Actions:**
```python
SendTelegram("Priya (Eng) joins Monday. Checklist: [GitHub] [Notion] [Slack] [GWorkspace] [Linear]. [Mark Done]")
SendTelegram("Offboard Rahul today. Revoke: GitHub, Notion, Slack, GWorkspace, Linear. [Confirm Done]")
UpsertQdrant("onboarding_run", narrative_of_issues_embedding)
```

***

### 3.4 Finance Monitor

**State:**
```python
@dataclass
class FinanceState:
    tenant_id: str
    monthly_revenue: float
    monthly_expense: float
    burn_rate: float
    runway_months: float
    known_vendors: list[dict]    # {vendor, avg_monthly_spend, stddev}
    last_anomalies: list[dict]
```

**Trigger events:**
```
PAYMENT_SUCCESS
EXPENSE_RECORDED
BANK_WEBHOOK
TIME_TICK_DAILY | WEEKLY
```

**LangGraph nodes:**
```
UpdateSnapshot    → recompute burn + runway from PostgreSQL
VendorBaseline    → load typical spend per vendor (avg ± 2σ)
DetectAnomaly     → compare current tx to baseline
ExplainAnomaly    → query Qdrant: did this pattern appear before?
DecideAlert       → severity (info/warn/critical) + who to ping
EmitActions       → anomaly alert, runway update, emit RUNWAY_UPDATED
```

**Key thresholds:**
- Anomaly: `current_spend > vendor_baseline + 2σ`
- Runway critical: `runway_months < 3`
- Runway warning: `runway_months < 6`

**Actions:**
```python
SendTelegram("AWS bill ₹42,000 — 2.3× usual. First spike. [Investigate] [Expected]")
EmitEvent("RUNWAY_UPDATED", {runway_months, burn_rate, snapshot_at})
UpsertQdrant("anomaly", event_plus_explanation_embedding)
```

***

### 3.5 Chief of Staff

**State:**
```python
@dataclass
class CoSState:
    tenant_id: str
    last_briefing_at: datetime
    last_investor_update_at: datetime
```

**Trigger events:**
```
TIME_TICK_WEEKLY
TIME_TICK_MONTHLY
AGENT_OUTPUT events from all 4 agents (via sarthi.agent.outputs)
```

**LangGraph nodes:**
```
CollectSignals     → pull last N agent outputs from PostgreSQL + Qdrant
Prioritize         → rank by urgency × impact score
ComposeBriefing    → LLM: 3–5 bullets, plain English, no jargon
ComposeInvestorDraft → optional, monthly, from finance + revenue data
EmitActions        → Telegram briefing + investor draft to Drive (via gws)
```

**Briefing rules:**
- Max 5 items
- Always include one positive item if data supports it
- No jargon: banned terms list enforced (`leverage, synergy, utilize, streamline, paradigm`)
- Each item: one headline + one `[Action]` button

**Actions:**
```python
SendTelegram("""
Monday Brief. 3 things need you today.

🔴 TDS due tomorrow: ₹47,230. Challan ready. [Pay Now] [Remind 5PM]
🟡 Priya's offer unsigned 6 days. Joins Monday. [Send Reminder]
🟢 Runway: 14.2 months. AWS spike under review.

Everything else: handled.
""")
WriteQdrant("briefing", summary_embedding)
```

***

## 4. Database Schema

```sql
-- ── Tenant / Founder ──────────────────────────────────────────────
CREATE TABLE founders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) UNIQUE NOT NULL,
    telegram_chat_id VARCHAR(50) NOT NULL,
    name            VARCHAR(100),
    stage           VARCHAR(30) DEFAULT 'prerevenue',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Raw events archive ────────────────────────────────────────────
CREATE TABLE raw_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    source          VARCHAR(50) NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    payload_hash    VARCHAR(100) NOT NULL,
    payload_body    JSONB NOT NULL,
    idempotency_key VARCHAR(200) UNIQUE,
    received_at     TIMESTAMPTZ DEFAULT NOW(),
    processed_at    TIMESTAMPTZ
);

-- ── Revenue ───────────────────────────────────────────────────────
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    raw_event_id    UUID REFERENCES raw_events(id),
    txn_date        DATE NOT NULL,
    description     TEXT NOT NULL,
    debit           NUMERIC(18,2) DEFAULT 0,
    credit          NUMERIC(18,2) DEFAULT 0,
    category        VARCHAR(50),
    confidence      FLOAT,
    source          VARCHAR(50),
    external_id     VARCHAR(200),
    UNIQUE(tenant_id, external_id)
);

CREATE TABLE pipeline_deals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    deal_id         VARCHAR(100) NOT NULL,
    name            VARCHAR(200),
    amount          NUMERIC(18,2),
    stage           VARCHAR(50),
    last_contact_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, deal_id)
);

-- ── Customer Success ──────────────────────────────────────────────
CREATE TABLE cs_customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    customer_id     VARCHAR(100) NOT NULL,
    telegram_id     VARCHAR(50),
    signup_at       TIMESTAMPTZ,
    last_seen_at    TIMESTAMPTZ,
    onboarding_stage VARCHAR(20) DEFAULT 'WELCOME',
    risk_score      FLOAT DEFAULT 0,
    UNIQUE(tenant_id, customer_id)
);

-- ── People ────────────────────────────────────────────────────────
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    employee_id     VARCHAR(100) NOT NULL,
    name            VARCHAR(100),
    role_function   VARCHAR(20),
    status          VARCHAR(20) DEFAULT 'ONBOARDING',
    checklist       JSONB DEFAULT '{}',
    hired_at        TIMESTAMPTZ,
    terminated_at   TIMESTAMPTZ,
    UNIQUE(tenant_id, employee_id)
);

-- ── Finance ───────────────────────────────────────────────────────
CREATE TABLE finance_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    snapshot_date   DATE NOT NULL,
    monthly_revenue NUMERIC(18,2),
    monthly_expense NUMERIC(18,2),
    burn_rate       NUMERIC(18,2),
    runway_months   FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE vendor_baselines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    vendor_name     VARCHAR(200) NOT NULL,
    avg_monthly     NUMERIC(18,2),
    stddev_monthly  NUMERIC(18,2),
    sample_count    INT DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, vendor_name)
);

-- ── Agent output log (consumed by Chief of Staff) ─────────────────
CREATE TABLE agent_outputs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    agent_name      VARCHAR(50) NOT NULL,
    output_type     VARCHAR(50),
    headline        TEXT,
    urgency         VARCHAR(10) DEFAULT 'low',
    hitl_sent       BOOLEAN DEFAULT FALSE,
    output_json     JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Telegram HITL log ─────────────────────────────────────────────
CREATE TABLE hitl_actions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       VARCHAR(50) NOT NULL,
    agent_name      VARCHAR(50),
    message_sent    TEXT,
    buttons         JSONB,
    founder_response VARCHAR(50),
    responded_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

***

## 5. Webhook Normalization Contract

Every source normalizes to this envelope before hitting Redpanda. Raw payload stored in PostgreSQL first; only the ref flows forward.

```go
// apps/core/internal/events/envelope.go
type EventEnvelope struct {
    TenantID       string    `json:"tenant_id"`
    EventType      string    `json:"event_type"`
    // e.g. PAYMENT_SUCCESS, USER_SIGNED_UP, EMPLOYEE_CREATED
    Source         string    `json:"source"`
    // e.g. razorpay, stripe, intercom, keka, bank
    PayloadRef     string    `json:"payload_ref"`
    // "raw_events:<uuid>" — NEVER raw JSON
    PayloadHash    string    `json:"payload_hash"`
    IdempotencyKey string    `json:"idempotency_key"`
    OccurredAt     time.Time `json:"occurred_at"`
    ReceivedAt     time.Time `json:"received_at"`
    TraceID        string    `json:"trace_id"`
}
```

**Event type map:**

| Source | Raw event | Normalized EventType |
|---|---|---|
| Razorpay | `payment.captured` | `PAYMENT_SUCCESS` |
| Razorpay | `subscription.cancelled` | `SUBSCRIPTION_CANCELED` |
| Stripe | `invoice.paid` | `PAYMENT_SUCCESS` |
| Intercom/Crisp | `user.created` | `USER_SIGNED_UP` |
| Intercom | `conversation.created` | `SUPPORT_TICKET_CREATED` |
| Keka/Darwinbox | `employee.created` | `EMPLOYEE_CREATED` |
| Keka | `employee.terminated` | `EMPLOYEE_TERMINATED` |
| Bank webhook/gws | `bank.transaction` | `BANK_WEBHOOK` |
| Cron | `cron.weekly` | `TIME_TICK_WEEKLY` |
| Cron | `cron.daily` | `TIME_TICK_DAILY` |

***

## 6. Testing Strategy

### 6.1 Unit Tests — Python (per LangGraph node, no mocks except LLM)

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

    def test_mrr_milestone_fires():
        # mrr crosses ₹5L threshold
        ...

    def test_normal_payment_silent():
        # routine payment, no anomaly, no telegram
        ...

class TestFinanceMonitor:
    def test_spend_anomaly_2sigma():
        baseline = VendorBaseline(vendor="AWS", avg=18000, stddev=2000)
        tx = Transaction(vendor="AWS", amount=42000)
        actions = finance_graph.invoke(state, tx)
        assert actions[0]["type"] == "SEND_TELEGRAM"
        assert "2.3×" in actions[0]["message"]

    def test_runway_critical_fires():
        # runway drops below 3 months
        ...

    def test_normal_expense_silent():
        # AWS bill within 1σ — no telegram
        ...
```

**Minimum per agent:** 3 unit tests per LangGraph node, covering normal / edge / failure.

### 6.2 E2E Tests — Full Stack (real Docker, real Azure LLM)

```python
# apps/ai/tests/test_e2e_sarthi.py
@pytest.mark.e2e
async def test_finance_anomaly_full_flow():
    """
    POST /webhooks/payments (AWS bill 2.3× baseline)
    → raw_events row created
    → Redpanda: BANK_WEBHOOK published
    → FinanceWorkflow triggered
    → Finance Monitor: anomaly detected
    → agent_outputs row created, urgency=high
    → Telegram message queued (assert via mock Telegram endpoint)
    → Qdrant memory written
    """

@pytest.mark.e2e
async def test_weekly_revenue_briefing():
    """
    Seed 5 payment events over 7 days
    → Trigger TIME_TICK_WEEKLY
    → RevenueWorkflow completes
    → agent_outputs: WEEKLY_REVENUE_SUMMARY emitted
    → CoS collects + composes briefing
    → Telegram briefing sent, ≤5 items, no banned jargon
    """

@pytest.mark.e2e
async def test_onboarding_sequence_with_nag():
    """
    POST /webhooks/hr (EMPLOYEE_CREATED, role=eng)
    → PeopleWorkflow starts
    → Checklist generated (6 items for eng)
    → Telegram sent with checklist buttons
    → 24h tick fires → reminder for incomplete items
    """

@pytest.mark.e2e
async def test_cs_churn_alert():
    """
    USER_SIGNED_UP → D7 tick with zero logins
    → CS risk_score > 0.7
    → Telegram alert to founder
    → message contains customer name + action buttons
    """

@pytest.mark.e2e
async def test_investor_update_draft():
    """
    1 month of payment + expense events → TIME_TICK_MONTHLY
    → CoS composes investor draft
    → Draft contains: revenue, burn, runway
    → Draft written to Qdrant memory
    → Telegram: "Investor update ready. [Review] [Send]"
    """
```

### 6.3 LLM Eval Suite

```python
# 10 scripted scenarios per agent, scored with custom evaluator
EVAL_CRITERIA = {
    "correctness":  float,  # 0–1, does decision match gold label
    "hallucination": bool,   # any fabricated numbers/names
    "brevity":      int,     # Telegram message token count (target < 80)
    "jargon_free":  bool,    # no banned terms
}

EVAL_SUITES = {
    "revenue":  "stale deal detection across 10 scripted pipelines",
    "cs":       "churn vs non-churn for 20 user histories",
    "finance":  "anomaly vs expected spike (campaign launch vs real overspend)",
    "cos":      "correct ordering of top 3 from mixed bag of 10 signals",
}
```

***

## 7. SOPs

### 7.1 Deployment SOP
```
1. git push to main
2. CI: go test ./... + pytest + ruff + mypy
3. Build: sarthi-gateway + sarthi-ai Docker images
4. Push to registry
5. Deploy via docker-compose (prod) or k8s manifests
6. Smoke test:
   - GET /health → 200
   - POST /webhooks/payments (fake Razorpay event) → agent runs
   - Check Langfuse traces → no errors
   - Check Temporal UI → workflow completed
```

### 7.2 Incident Response SOP
```
Alert condition: 5xx > 1% OR Temporal backlog > 100 OR Redpanda lag > 1000

Steps:
1. Temporal UI → look for stuck workflows
2. Redpanda admin → check sarthi.events.raw lag
3. Langfuse → filter failed LLM calls in last 15 min
4. PostgreSQL → check raw_events.processed_at NULL backlog
5. Roll back to previous image if cause unclear
```

***

## 8. Coding Agent Brief

This is a self-contained, paste-and-execute instruction block. No clarifying questions needed.

***

### BOOTSTRAP — Run Once

```bash
# 1. Confirm you are on the correct base
git log --oneline -3
# Must show v4.2.0-alpha context (255 tests passing)

# 2. Create feature branch
git checkout -b feature/sarthi-v1 v4.2.0-alpha

# 3. Verify baseline green before touching anything
cd apps/ai && uv run pytest tests/ -q --timeout=90
cd apps/core && go test ./... -timeout=60s
# Expected: 255 tests passing. STOP if not.

# 4. Check current migration number
ls apps/core/internal/db/migrations/ | sort | tail -1
# Use LAST + 1 for your migration file
```

***

### INVARIANTS — Run Before Every Commit

```bash
# I-1: No raw JSON in Temporal signals (only PayloadRef strings)
grep -rn "json.Marshal\|json.Unmarshal" apps/core/internal/workflow/ \
  | grep -v "_test.go" | grep -v "// safe:" \
  && echo "FAIL: raw JSON in workflow" && exit 1

# I-2: No AzureOpenAI() outside config/llm.py
grep -rn "AzureOpenAI(" apps/ai/src/ | grep -v "config/llm.py" \
  && echo "FAIL: direct AzureOpenAI() call" && exit 1

# I-3: All 255 tests still pass
cd apps/ai && uv run pytest tests/ -x -q --timeout=90 && cd -
cd apps/core && go test ./... -timeout=60s && cd -

# I-4: No jargon in Telegram messages
grep -rn "leverage\|synergy\|utilize\|streamline\|paradigm" \
  apps/ai/src/agents/ | grep -v "# allowed:" \
  && echo "FAIL: banned jargon in agent output"
```

***

### COMMIT SEQUENCE — Execute in Order

#### COMMIT 1 — Database migration
```bash
# File: apps/core/internal/db/migrations/NNN_sarthi_v1.sql
# Content: all tables from Section 4 above
# Apply: psql $DATABASE_URL -f migrations/NNN_sarthi_v1.sql
# Test:
go test ./internal/db -run TestMigration -v
# Expected: tables exist, idempotency_key unique constraint works
```

#### COMMIT 2 — Event Envelope (Go + Python)
```bash
# Files:
#   apps/core/internal/events/envelope.go   (EventEnvelope struct)
#   apps/ai/src/schemas/event_envelope.py   (Pydantic model)
# Test:
uv run pytest tests/test_event_envelope.py -v
# Expected: 4 tests — valid envelope, empty event_name fails,
#           raw JSON as payload_ref fails, all sources valid
```

#### COMMIT 3 — Event normalization map
```bash
# File: apps/core/internal/events/normalizer.go
# Logic: source + raw_event → EventType from the table in Section 5
# Unknown events → dead_letter_events table, no error returned
# Test:
go test ./internal/events -run TestNormalizer -v
# Expected: 10 mappings correct, unknown event goes to DLQ
```

#### COMMIT 4 — Go webhook handlers (all 5 routes)
```bash
# Files:
#   apps/core/internal/api/payments.go
#   apps/core/internal/api/crm.go
#   apps/core/internal/api/support.go
#   apps/core/internal/api/hr.go
#   apps/core/internal/api/bank.go
# Each handler must:
#   1. Verify HMAC (provider-specific)
#   2. Store raw event in PostgreSQL FIRST
#   3. Publish EventEnvelope (PayloadRef only) to Redpanda
#   4. Return 200 immediately
#   5. Unknown events → DLQ, still 200
#   6. Duplicate idempotency_key → 200 + "duplicate"
# Test per handler:
go test ./internal/api -run TestPaymentsWebhook -v
# Expected: valid sig accepted, invalid rejected, unknown to DLQ,
#           duplicate idempotent, Redpanda receives envelope
```

#### COMMIT 5 — Temporal workflow routing
```bash
# File: apps/core/internal/workflow/sarthi_router.go
# Logic:
#   Parent workflow receives EventEnvelope signal
#   Routes to child workflow by EventType:
#     PAYMENT_* | SUBSCRIPTION_* | CRM_* | TIME_TICK_* → RevenueWorkflow
#     USER_* | SUPPORT_* → CSWorkflow
#     EMPLOYEE_* | CHECKLIST_* → PeopleWorkflow
#     EXPENSE_* | BANK_* | TIME_TICK_DAILY → FinanceWorkflow
#     TIME_TICK_WEEKLY | TIME_TICK_MONTHLY | AGENT_OUTPUT → CoSWorkflow
#   Parent Continue-As-New at 1,000 events
# Test:
go test ./internal/workflow -run TestSarthiRouter -v
# Expected: correct workflow spawned per event type,
#           CAN fires at 1000, duplicate key skipped
```

#### COMMIT 6 — Finance Monitor LangGraph agent
```bash
# File: apps/ai/src/agents/finance_monitor.py
# LangGraph nodes: UpdateSnapshot, VendorBaseline, DetectAnomaly,
#                  ExplainAnomaly, DecideAlert, EmitActions
# Thresholds: 2σ anomaly, runway < 3 months critical, < 6 months warn
# Test:
uv run pytest tests/test_finance_monitor.py -v
# Per-node tests:
#   test_spend_anomaly_2sigma_fires
#   test_spend_within_1sigma_silent
#   test_runway_critical_fires
#   test_runway_healthy_silent
#   test_anomaly_explained_by_qdrant_history
#   test_normal_expense_silent
# Run invariants. Commit.
```

#### COMMIT 7 — Revenue Tracker LangGraph agent
```bash
# File: apps/ai/src/agents/revenue_tracker.py
# LangGraph nodes: IngestEvent, UpdateMetrics, DetectStaleDeals,
#                  DecideAlerts, WriteMemory, EmitActions
# Test:
uv run pytest tests/test_revenue_tracker.py -v
# Per-node tests:
#   test_stale_deal_7d_fires
#   test_active_deal_silent
#   test_mrr_milestone_fires
#   test_routine_payment_silent
#   test_concentration_risk_fires
#   test_weekly_summary_written_to_qdrant
# Run invariants. Commit.
```

#### COMMIT 8 — CS Agent LangGraph agent
```bash
# File: apps/ai/src/agents/cs_agent.py
# LangGraph nodes: OnSignup, OnTimeTick, OnSupportTicket,
#                  RiskAssessment, EmitActions
# Test:
uv run pytest tests/test_cs_agent.py -v
# Per-node tests:
#   test_signup_initializes_cs_state
#   test_d1_message_queued
#   test_7d_no_login_risk_high
#   test_active_user_risk_low
#   test_support_ticket_faq_draft_reply
#   test_support_ticket_escalation
# Run invariants. Commit.
```

#### COMMIT 9 — People Coordinator LangGraph agent
```bash
# File: apps/ai/src/agents/people_coordinator.py
# LangGraph nodes: OnHireEvent, GenerateChecklist, ProgressTracking,
#                  NagLoop, Offboarding
# Test:
uv run pytest tests/test_people_coordinator.py -v
# Per-node tests:
#   test_eng_checklist_has_github
#   test_sales_checklist_no_github
#   test_incomplete_item_nag_after_24h
#   test_complete_checklist_no_nag
#   test_offboarding_generates_revoke_list
#   test_checklist_confirmed_updates_state
# Run invariants. Commit.
```

#### COMMIT 10 — Chief of Staff LangGraph agent
```bash
# File: apps/ai/src/agents/chief_of_staff.py
# LangGraph nodes: CollectSignals, Prioritize, ComposeBriefing,
#                  ComposeInvestorDraft, EmitActions
# Rules enforced in code:
#   - max 5 items
#   - at least 1 positive item if data supports it
#   - BANNED_JARGON list checked on every output
# Test:
uv run pytest tests/test_chief_of_staff.py -v
# Per-node tests:
#   test_briefing_max_5_items
#   test_briefing_has_one_positive_item
#   test_briefing_no_banned_jargon
#   test_high_urgency_items_ranked_first
#   test_investor_draft_contains_revenue_burn_runway
#   test_empty_week_briefing_graceful
# Run invariants. Commit.
```

#### COMMIT 11 — Telegram handler
```bash
# File: apps/core/internal/api/telegram.go
# Logic:
#   Outbound: POST to Telegram Bot API with inline keyboard buttons
#   Inbound:  POST /webhooks/telegram/callback
#     → parse callback_query.data → update hitl_actions table
#     → if action is "pay_now" → emit PAYMENT_INSTRUCTION event
#     → if action is "mark_ok" → update relevant record
#     → if action is "send_reminder" → queue re-send
# Test:
go test ./internal/api -run TestTelegram -v
# Expected: message sent, callback parsed correctly,
#           hitl_actions row written, downstream action emitted
```

#### COMMIT 12 — E2E test suite + test runner
```bash
# File: apps/ai/tests/test_e2e_sarthi.py
# 5 E2E tests from Section 6.2:
#   test_finance_anomaly_full_flow
#   test_weekly_revenue_briefing
#   test_onboarding_sequence_with_nag
#   test_cs_churn_alert
#   test_investor_update_draft
# File: scripts/test_sarthi.sh
#   Step 1: Docker health check
#   Step 2: Azure LLM smoke test
#   Step 3: Unit tests (all agents)
#   Step 4: Go tests
#   Step 5: E2E tests
# All must pass. No mocks. Real Docker. Real Azure LLM.
# Tag: git tag v1.0.0-alpha
```

***

### DEFINITION OF DONE

```
REQUIRED BEFORE TAGGING v1.0.0:

  ✅ Migration applied cleanly, all tables created
  ✅ EventEnvelope rejects raw JSON in payload_ref
  ✅ All 5 webhook handlers: HMAC, DLQ, idempotency
  ✅ Parent workflow routes correctly, CAN at 1,000
  ✅ Finance Monitor: 2σ anomaly + runway alerts
  ✅ Revenue Tracker: stale deals + milestones
  ✅ CS Agent: D1/D3/D7 sequence + churn risk
  ✅ People Coordinator: role-based checklists + nag loop
  ✅ Chief of Staff: ≤5 items, jargon-free, 1 positive
  ✅ Telegram: outbound messages + callback handling
  ✅ All 255 original tests still pass
  ✅ bash scripts/test_sarthi.sh → FAILED: 0

BLOCKED IF:
  ✗ Temporal signal contains raw JSON payload
  ✗ AzureOpenAI() called directly outside config/llm.py
  ✗ Any Telegram message contains banned jargon
  ✗ Original test count dropped below 255
  ✗ Any E2E test uses a mock
```
