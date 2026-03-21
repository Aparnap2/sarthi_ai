# Sarthi v1.0 — Strategic Code Reuse Analysis
## Leveraging Existing v4.3.0-alpha Code for Accelerated Development

**Date:** March 2026  
**Analysis:** Deep codebase audit for v4.3.0-alpha → v1.0 pivot

---

## Executive Summary

**Good news:** ~70% of v4.3.0-alpha code is directly reusable for v1.0 scoped system.

**Key insight:** v4.3.0-alpha built 13 virtual employees with generic infrastructure. v1.0 needs 5 agents with the SAME infrastructure. The foundation (event envelope, webhooks, Temporal routing, SOP registry) is already built and tested.

**Estimated acceleration:** 4-6 weeks of work already done.

---

## What Exists (v4.3.0-alpha) vs What v1.0 Needs

| Component | v4.3.0-alpha | v1.0 Needs | Reuse % | Action |
|-----------|--------------|------------|---------|--------|
| **Database Schema** | 9 tables (raw_events, transactions, etc.) | 9 tables (similar structure) | 80% | Rename tenant_id → founder_id, add cs_customers, employees |
| **Event Envelope** | ✅ Complete (Go + Python) | ✅ Same pattern | 100% | Direct reuse |
| **Event Dictionary** | 48 events mapped | 10 events mapped | 100% | Subset, direct reuse |
| **Webhook Handlers** | Razorpay, Telegram | Razorpay, CRM, Support, HR, Bank | 20% | Razorpay reusable, build 4 new |
| **Temporal Workflow** | Parent router + CAN at 5,000 | Parent router + CAN at 1,000 | 90% | Change threshold, update routing map |
| **SOP Registry** | ✅ Complete | Need agent registry | 50% | Adapt for LangGraph agents |
| **SOPs** | Revenue, Bank Statement, Weekly Briefing | Finance, Revenue, CS, People, CoS | 40% | Revenue/Briefing reusable, build 3 new |
| **Tests** | 138 tests (135 PASS) | 325+ tests | 30% | Reuse infrastructure tests, add agent tests |
| **Test Runner** | ✅ Complete | ✅ Same pattern | 100% | Direct reuse |

---

## Detailed Reuse Analysis

### 1. Database Layer (80% Reuse)

**What exists:**
```sql
-- From v4.3.0-alpha migration 001
raw_events (id, founder_id, source, event_type, payload_body, idempotency_key)
transactions (id, founder_id, raw_event_id, txn_date, debit, credit, category)
sop_jobs, sop_findings, connector_states, dead_letter_events
```

**What v1.0 needs:**
```sql
-- From v1.0 PRD
founders (tenant_id, telegram_chat_id, name, stage)
raw_events (tenant_id, source, event_type, payload_body, idempotency_key)
transactions (tenant_id, raw_event_id, txn_date, debit, credit, category)
pipeline_deals (tenant_id, deal_id, amount, stage, last_contact_at)
cs_customers (tenant_id, customer_id, signup_at, onboarding_stage, risk_score)
employees (tenant_id, employee_id, role_function, checklist JSONB)
finance_snapshots (tenant_id, burn_rate, runway_months)
vendor_baselines (tenant_id, vendor_name, avg_monthly, stddev_monthly)
agent_outputs (tenant_id, agent_name, output_type, headline, urgency)
hitl_actions (tenant_id, message_sent, buttons, founder_response)
```

**Reuse strategy:**
1. **Keep:** `raw_events`, `transactions` (rename `founder_id` → `tenant_id`)
2. **Drop:** `sop_jobs`, `sop_findings`, `connector_states` (not in v1.0 schema)
3. **Add:** `pipeline_deals`, `cs_customers`, `employees`, `finance_snapshots`, `vendor_baselines`, `agent_outputs`, `hitl_actions`
4. **Modify:** `founders` table (add `telegram_chat_id`, `stage`)

**Files to modify:**
- `apps/core/internal/db/migrations/001_sarthi_sop_runtime.sql` → `002_sarthi_v1.sql`
- `apps/core/internal/db/dbsqlc/` → regenerate after schema change

**Estimated time saved:** 1 week (schema design + migration testing)

---

### 2. Event Envelope (100% Reuse)

**What exists:**
```go
// apps/core/internal/events/envelope.go
type EventEnvelope struct {
    EventID        string
    FounderID      string      // → TenantID
    Source         EventSource
    EventName      string      // → EventType
    Topic          string
    SOPName        string
    PayloadRef     string      // "raw_events:<uuid>" — perfect
    PayloadHash    string
    OccurredAt     time.Time
    ReceivedAt     time.Time
    TraceID        string
    IdempotencyKey string
    Version        string
}
```

**What v1.0 needs:**
```go
type EventEnvelope struct {
    TenantID       string      // renamed from FounderID
    EventType      string      // renamed from EventName
    Source         string      // same
    PayloadRef     string      // same — "raw_events:<uuid>"
    PayloadHash    string      // same
    IdempotencyKey string      // same
    OccurredAt     time.Time   // same
    ReceivedAt     time.Time   // same
    TraceID        string      // same
}
```

**Reuse strategy:**
1. **Rename fields:** `FounderID` → `TenantID`, `EventName` → `EventType`
2. **Remove fields:** `Topic`, `SOPName`, `Version` (not in v1.0 envelope)
3. **Keep validators:** payload_ref must be storage ref, event_name not empty

**Files to modify:**
- `apps/core/internal/events/envelope.go` (rename fields)
- `apps/ai/src/schemas/event_envelope.py` (rename fields)
- `apps/ai/tests/test_event_envelope.py` (update field names in tests)

**Estimated time saved:** 3 days (envelope design + validation logic)

---

### 3. Event Dictionary (100% Reuse)

**What exists:**
```python
# apps/ai/src/config/event_dictionary.py
_REGISTRY = [
    DictionaryEntry("razorpay", "payment.captured", "finance.revenue.captured", "SOP_REVENUE_RECEIVED", ...),
    DictionaryEntry("razorpay", "subscription.cancelled", "finance.subscription.cancelled", "SOP_CHURN_DETECTED", ...),
    # 48 events total
]
```

**What v1.0 needs:**
```python
# Event type map from PRD
EVENT_TYPE_MAP = {
    ("razorpay", "payment.captured"): "PAYMENT_SUCCESS",
    ("razorpay", "subscription.cancelled"): "SUBSCRIPTION_CANCELED",
    ("stripe", "invoice.paid"): "PAYMENT_SUCCESS",
    ("intercom", "user.created"): "USER_SIGNED_UP",
    ("intercom", "conversation.created"): "SUPPORT_TICKET_CREATED",
    ("keka", "employee.created"): "EMPLOYEE_CREATED",
    ("keka", "employee.terminated"): "EMPLOYEE_TERMINATED",
    ("bank", "bank.transaction"): "BANK_WEBHOOK",
    ("cron", "cron.weekly"): "TIME_TICK_WEEKLY",
    ("cron", "cron.daily"): "TIME_TICK_DAILY",
}
```

**Reuse strategy:**
1. **Keep:** `EventDictionary` class structure
2. **Replace:** `_REGISTRY` contents with v1.0 event type map
3. **Add:** Normalizer function (source + raw_event → EventType)

**Files to modify:**
- `apps/ai/src/config/event_dictionary.py` (update registry)
- `apps/core/internal/events/dictionary.go` (update Go version)
- `apps/core/internal/events/normalizer.go` (NEW — normalization logic)

**Estimated time saved:** 2 days (dictionary pattern already proven)

---

### 4. Webhook Handlers (20% Reuse)

**What exists:**
```go
// apps/core/internal/web/razorpay.go
type RazorpayHandler struct {
    secret   string
    store    db.RawEventStore
    producer redpanda.Producer
    dict     *events.EventDictionary
}

func (h *RazorpayHandler) Handle(c *fiber.Ctx) error {
    // 1. Verify HMAC-SHA256
    // 2. Parse event name
    // 3. Resolve via dictionary
    // 4. Persist raw event
    // 5. Publish envelope
}
```

**What v1.0 needs:**
```go
// apps/core/internal/api/payments.go
type PaymentsHandler struct {
    razorpaySecret string
    store          db.RawEventStore
    producer       redpanda.Producer
}

// Same pattern for: CRM, Support, HR, Bank handlers
```

**Reuse strategy:**
1. **Reuse:** `RazorpayHandler` → `PaymentsHandler` (rename, simplify)
2. **Extract common logic:** HMAC verification, raw event storage, envelope publishing
3. **Build 4 new handlers:** CRM, Support, HR, Bank (same pattern, different HMAC secrets)

**Files to reuse:**
- `apps/core/internal/web/razorpay.go` → `apps/core/internal/api/payments.go`
- `apps/core/internal/web/razorpay_test.go` → `apps/core/internal/api/payments_test.go`

**Files to create:**
- `apps/core/internal/api/crm.go`
- `apps/core/internal/api/support.go`
- `apps/core/internal/api/hr.go`
- `apps/core/internal/api/bank.go`

**Estimated time saved:** 1 week (handler pattern proven, just replicate)

---

### 5. Temporal Workflow (90% Reuse)

**What exists:**
```go
// apps/core/internal/workflow/business_os_workflow.go
const ContinueAsNewThreshold = 5000

func BusinessOSWorkflow(ctx workflow.Context, founderID string) error {
    state := BusinessOSState{...}
    ch := workflow.GetSignalChannel(ctx, "sarthi.events")
    
    for {
        if state.EventsProcessed >= ContinueAsNewThreshold {
            return workflow.NewContinueAsNewError(...)
        }
        
        var envelope events.EventEnvelope
        ch.Receive(ctx, &envelope)
        
        // Idempotency check
        if state.SeenKeys[envelope.IdempotencyKey] {
            continue
        }
        
        // Spawn child workflow
        workflow.ExecuteChildWorkflow(childCtx, envelope.SOPName, envelope)
    }
}
```

**What v1.0 needs:**
```go
// apps/core/internal/workflow/sarthi_router.go
const ContinueAsNewThreshold = 1000  // Changed from 5000

func SarthiRouter(ctx workflow.Context, tenantID string) error {
    // Same pattern, different routing map:
    // EventType → Workflow (not SOP name)
    switch envelope.EventType {
    case "PAYMENT_SUCCESS", "SUBSCRIPTION_*":
        spawn(RevenueWorkflow, envelope)
    case "USER_*", "SUPPORT_*":
        spawn(CSWorkflow, envelope)
    // etc.
    }
}
```

**Reuse strategy:**
1. **Keep:** Parent workflow pattern, idempotency logic, CAN mechanism
2. **Change:** Threshold from 5,000 → 1,000
3. **Update:** Routing map (EventType → Workflow, not SOP name)
4. **Rename:** `BusinessOSWorkflow` → `SarthiRouter`

**Files to modify:**
- `apps/core/internal/workflow/business_os_workflow.go` → `sarthi_router.go`
- `apps/core/internal/workflow/business_os_workflow_test.go` → `sarthi_router_test.go`

**Estimated time saved:** 1.5 weeks (workflow pattern is complex, already debugged)

---

### 6. SOP Registry → Agent Registry (50% Reuse)

**What exists:**
```python
# apps/ai/src/sops/registry.py
_REGISTRY: dict[str, BaseSOP] = {}

def register(sop: BaseSOP):
    _REGISTRY[sop.sop_name] = sop

class SOPRegistry:
    def has(self, sop_name: str) -> bool: ...
    def get(self, sop_name: str) -> BaseSOP: ...
```

**What v1.0 needs:**
```python
# apps/ai/src/agents/registry.py
_REGISTRY: dict[str, LangGraphAgent] = {}

def register(agent: LangGraphAgent):
    _REGISTRY[agent.name] = agent

class AgentRegistry:
    def has(self, agent_name: str) -> bool: ...
    def get(self, agent_name: str) -> LangGraphAgent: ...
```

**Reuse strategy:**
1. **Keep:** Registry pattern (has/get/register)
2. **Change:** BaseSOP → LangGraphAgent base class
3. **Update:** Registration calls for 5 agents

**Files to modify:**
- `apps/ai/src/sops/registry.py` → `apps/ai/src/agents/registry.py`
- `apps/ai/src/sops/base.py` → `apps/ai/src/agents/base.py` (LangGraph state pattern)

**Estimated time saved:** 3 days (registry pattern proven)

---

### 7. SOPs → Agents (40% Reuse)

**What exists:**
- `SOP_REVENUE_RECEIVED` (Razorpay payments, MRR milestones)
- `SOP_BANK_STATEMENT_INGEST` (CSV/PDF parsing, categorization)
- `SOP_WEEKLY_BRIEFING` (Monday 9am briefing, max 5 items)

**What v1.0 needs:**
- **Finance Monitor** (spend anomaly, runway alerts)
- **Revenue Tracker** (stale deals, MRR milestones) ← 80% reuse from SOP_REVENUE_RECEIVED
- **CS Agent** (D1/D3/D7 onboarding, churn risk)
- **People Coordinator** (role-based checklists)
- **Chief of Staff** (weekly brief, investor draft) ← 60% reuse from SOP_WEEKLY_BRIEFING

**Reuse strategy:**

**Revenue Tracker (80% reuse):**
```python
# From: apps/ai/src/sops/revenue_received.py
class RevenueReceivedSOP(BaseSOP):
    async def execute(self, payload_ref, founder_id):
        # Extract payment entity
        # Write transaction
        # Check MRR milestones
        # Check concentration risk

# To: apps/ai/src/agents/revenue_tracker.py
class RevenueTracker(LangGraphAgent):
    async def invoke(self, state, event):
        # Same logic, wrapped in LangGraph nodes
        # + DetectStaleDeals node (new)
```

**Chief of Staff (60% reuse):**
```python
# From: apps/ai/src/sops/weekly_briefing.py
class WeeklyBriefingSOP(BaseSOP):
    async def execute(self, payload_ref, founder_id):
        # Collect from desks
        # Score and rank
        # Max 5 items
        # Apply tone filter

# To: apps/ai/src/agents/chief_of_staff.py
class ChiefOfStaff(LangGraphAgent):
    # Same logic, LangGraph nodes
    # + ComposeInvestorDraft node (new)
```

**Files to reuse:**
- `apps/ai/src/sops/revenue_received.py` → `apps/ai/src/agents/revenue_tracker.py`
- `apps/ai/src/sops/weekly_briefing.py` → `apps/ai/src/agents/chief_of_staff.py`

**Files to create:**
- `apps/ai/src/agents/finance_monitor.py`
- `apps/ai/src/agents/cs_agent.py`
- `apps/ai/src/agents/people_coordinator.py`

**Estimated time saved:** 2 weeks (Revenue + CoS logic already written)

---

### 8. Tests (30% Reuse)

**What exists:**
- 138 tests (135 PASS, 3 SKIPPED)
- Event envelope tests (4)
- Event dictionary tests (14)
- Webhook handler tests (13 Razorpay + 7 Telegram)
- SOP tests (13 + 12 + 11)
- E2E tests (3)

**What v1.0 needs:**
- 325+ tests for v1.0-alpha
- 429+ tests for v1.0.0 (including LLM evals)

**Reuse strategy:**
1. **Keep:** All infrastructure tests (envelope, dictionary, webhook pattern)
2. **Update:** SOP tests → Agent tests (rename, adapt to LangGraph)
3. **Add:** New agent tests (Finance, CS, People)
4. **Expand:** E2E tests (3 → 5)

**Tests to reuse directly:**
- `test_event_envelope.py` (4 tests)
- `test_event_dictionary.py` (14 tests)
- `test_sop_registry.py` (14 tests) → `test_agent_registry.py`
- `test_e2e_sop_flows.py` (3 tests) → `test_e2e_sarthi.py` (5 tests)

**Tests to adapt:**
- `test_sop_revenue_received.py` (13 tests) → `test_revenue_tracker.py` (6 tests)
- `test_sop_weekly_briefing.py` (11 tests) → `test_chief_of_staff.py` (6 tests)

**Tests to create:**
- `test_finance_monitor.py` (6 tests)
- `test_cs_agent.py` (6 tests)
- `test_people_coordinator.py` (6 tests)
- Webhook handler tests (CRM, Support, HR, Bank: 16 tests)

**Estimated time saved:** 1 week (test infrastructure + patterns proven)

---

## Strategic Recommendations

### Priority 1: Reuse Infrastructure (Week 1)

**Focus:** Database, Event Envelope, Event Dictionary, Test Runner

**Why:** These are foundational. Once done, all agents can build on top.

**Files to touch:**
1. `apps/core/internal/db/migrations/002_sarthi_v1.sql` (NEW migration)
2. `apps/core/internal/events/envelope.go` (rename fields)
3. `apps/ai/src/schemas/event_envelope.py` (rename fields)
4. `apps/ai/src/config/event_dictionary.py` (update registry)
5. `scripts/test_sarthi.sh` (direct reuse)

**Expected outcome:** Infrastructure ready for agent development.

---

### Priority 2: Reuse Webhooks + Temporal (Week 2)

**Focus:** Payments handler, Temporal router

**Why:** These connect external world to agents. Unblock E2E testing.

**Files to touch:**
1. `apps/core/internal/api/payments.go` (from Razorpay handler)
2. `apps/core/internal/api/crm.go` (NEW, same pattern)
3. `apps/core/internal/api/support.go` (NEW)
4. `apps/core/internal/api/hr.go` (NEW)
5. `apps/core/internal/api/bank.go` (NEW)
6. `apps/core/internal/workflow/sarthi_router.go` (from BusinessOSWorkflow)

**Expected outcome:** Events flow from webhooks → Temporal → agents.

---

### Priority 3: Reuse Revenue + CoS Agents (Week 3)

**Focus:** Revenue Tracker, Chief of Staff

**Why:** These have most reuse from v4.3.0-alpha SOPs.

**Files to touch:**
1. `apps/ai/src/agents/revenue_tracker.py` (from SOP_REVENUE_RECEIVED)
2. `apps/ai/src/agents/chief_of_staff.py` (from SOP_WEEKLY_BRIEFING)
3. `apps/ai/tests/test_revenue_tracker.py` (adapt from revenue_received tests)
4. `apps/ai/tests/test_chief_of_staff.py` (adapt from weekly_briefing tests)

**Expected outcome:** 2/5 agents complete, E2E tests possible.

---

### Priority 4: Build New Agents (Weeks 4-5)

**Focus:** Finance Monitor, CS Agent, People Coordinator

**Why:** These are new logic, but can reuse infrastructure.

**Files to create:**
1. `apps/ai/src/agents/finance_monitor.py`
2. `apps/ai/src/agents/cs_agent.py`
3. `apps/ai/src/agents/people_coordinator.py`
4. Corresponding test files

**Expected outcome:** All 5 agents complete.

---

### Priority 5: E2E + Polish (Week 6)

**Focus:** E2E tests, LLM evals, documentation

**Files to create:**
1. `apps/ai/tests/test_e2e_sarthi.py` (5 E2E tests)
2. `apps/ai/tests/test_llm_evals.py` (40 eval scenarios)
3. Update README.md, docs/PRD.md

**Expected outcome:** v1.0.0-alpha ready to tag.

---

## Risk Mitigation

### Risk 1: Schema Migration Conflicts

**Mitigation:**
- Use migration `002` (not modifying `001`)
- Test migration on fresh database first
- Keep `001` tables for backward compatibility during transition

### Risk 2: Field Name Changes Break Tests

**Mitigation:**
- Rename fields incrementally (one per commit)
- Run full test suite after each rename
- Use grep to find all references before renaming

### Risk 3: Agent Logic Diverges from SOP Logic

**Mitigation:**
- Keep SOP files during transition (don't delete)
- Run both SOP and agent tests in parallel
- Verify agent output matches SOP output for same input

---

## Conclusion

**70% of v4.3.0-alpha code is directly reusable for v1.0.**

**Time saved:** 4-6 weeks of development.

**Key reusable components:**
1. Event envelope (100%)
2. Event dictionary (100%)
3. Test runner (100%)
4. Temporal workflow pattern (90%)
5. Webhook handler pattern (20% → pattern reuse)
6. Revenue Tracker logic (80%)
7. Chief of Staff logic (60%)

**Recommended approach:**
1. Week 1: Infrastructure (DB, envelope, dictionary)
2. Week 2: Webhooks + Temporal routing
3. Week 3: Reuse Revenue + CoS agents
4. Weeks 4-5: Build new agents (Finance, CS, People)
5. Week 6: E2E tests + polish

**v1.0.0-alpha timeline:** 6 weeks from v4.3.0-alpha baseline.

---

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Status:** Ready for implementation
