# Sarthi v1.0 — Phases 5-12 Execution Brief
## Complete, Self-Contained Coding Agent Instructions

**Date:** March 18, 2026  
**Pickup Point:** After Phase 4 completion (16 tests passing)  
**Target:** v1.0.0-alpha tag

---

## Current State Checkpoint

```bash
# Verify before starting Phase 5
cd apps/core && go test ./... -timeout=60s    # must include 16 new tests
cd apps/ai  && uv run pytest tests/ -q        # must be green
# If not — STOP. Fix before proceeding.
```

---

## Invariants — Run Before Every Commit

```bash
# I-1: No raw JSON in Temporal signals
grep -rn "json.Marshal\|json.Unmarshal" apps/core/internal/workflow/ \
  | grep -v "_test.go" | grep -v "// safe:" \
  && echo "FAIL I-1" && exit 1 || true

# I-2: No AzureOpenAI() outside config/llm.py
grep -rn "AzureOpenAI(" apps/ai/src/ | grep -v "config/llm.py" \
  && echo "FAIL I-2" && exit 1 || true

# I-3: Existing tests still pass
cd apps/ai && uv run pytest tests/ -x -q --timeout=90 && cd -
cd apps/core && go test ./... -timeout=60s && cd -

# I-4: No jargon in agent output strings
grep -rn "leverage\|synergy\|utilize\|streamline\|paradigm" \
  apps/ai/src/agents/ | grep -v "# allowed:" \
  && echo "FAIL I-4" && exit 1 || true

echo "All invariants ✓"
```

---

## PHASE 5 — Temporal Router + CAN at 1,000

### Test first:

**File:** `apps/core/internal/workflow/sarthi_router_test.go`

```go
package workflow_test

func TestRouterPaymentGoesToRevenue(t *testing.T)        {}
func TestRouterUserSignupGoesToCS(t *testing.T)          {}
func TestRouterEmployeeGoesToPeople(t *testing.T)        {}
func TestRouterBankWebhookGoesToFinance(t *testing.T)    {}
func TestRouterWeeklyTickGoesToCoS(t *testing.T)         {}
func TestRouterAgentOutputGoesToCoS(t *testing.T)        {}
func TestContinueAsNewAt1000Events(t *testing.T)         {}
func TestDuplicateIdempotencyKeySkipped(t *testing.T)    {}
func TestUnknownEventTypeGoesToDLQ(t *testing.T)         {}
```

**Run:** `go test ./internal/workflow -run TestRouter -v` → **expect FAIL**

### Implement:

**File:** `apps/core/internal/workflow/sarthi_router.go`

```go
package workflow

import (
    "fmt"
    "go.temporal.io/sdk/workflow"
    "github.com/your-org/sarthi/apps/core/internal/events"
)

const continueAsNewThreshold = 1000

// Event type → workflow name routing table
var eventTypeToWorkflow = map[string]string{
    // Revenue Tracker
    "PAYMENT_SUCCESS":         "RevenueWorkflow",
    "SUBSCRIPTION_CREATED":    "RevenueWorkflow",
    "SUBSCRIPTION_UPDATED":    "RevenueWorkflow",
    "SUBSCRIPTION_CANCELED":   "RevenueWorkflow",
    "CRM_DEAL_CREATED":        "RevenueWorkflow",
    "CRM_DEAL_UPDATED":        "RevenueWorkflow",
    "TIME_TICK_WEEKLY":        "RevenueWorkflow",

    // CS Agent
    "USER_SIGNED_UP":          "CSWorkflow",
    "USER_LOGGED_IN":          "CSWorkflow",
    "SUPPORT_TICKET_CREATED":  "CSWorkflow",
    "TIME_TICK_D1":            "CSWorkflow",
    "TIME_TICK_D3":            "CSWorkflow",
    "TIME_TICK_D7":            "CSWorkflow",

    // People Coordinator
    "EMPLOYEE_CREATED":        "PeopleWorkflow",
    "EMPLOYEE_TERMINATED":     "PeopleWorkflow",
    "CHECKLIST_ITEM_CONFIRMED":"PeopleWorkflow",

    // Finance Monitor
    "EXPENSE_RECORDED":        "FinanceWorkflow",
    "BANK_WEBHOOK":            "FinanceWorkflow",
    "TIME_TICK_DAILY":         "FinanceWorkflow",

    // Chief of Staff only
    "TIME_TICK_MONTHLY":       "ChiefOfStaffWorkflow",
    "AGENT_OUTPUT":            "ChiefOfStaffWorkflow",
}

// Multi-route events: sent to BOTH workflows
var multiRouteEvents = map[string][]string{
    "TIME_TICK_WEEKLY": {"RevenueWorkflow", "ChiefOfStaffWorkflow"},
}

type SarthiRouterState struct {
    TenantID        string
    EventsProcessed int
    SeenKeys        map[string]bool
}

func SarthiRouterWorkflow(ctx workflow.Context, tenantID string) error {
    state := SarthiRouterState{
        TenantID: tenantID,
        SeenKeys: make(map[string]bool),
    }
    ch := workflow.GetSignalChannel(ctx, "sarthi.events")

    for {
        // Guard: Continue-As-New before history bloats
        if state.EventsProcessed >= continueAsNewThreshold {
            return workflow.NewContinueAsNewError(ctx, SarthiRouterWorkflow, tenantID)
        }

        var envelope events.EventEnvelope
        ch.Receive(ctx, &envelope)

        // Idempotency guard
        if state.SeenKeys[envelope.IdempotencyKey] {
            continue
        }
        state.SeenKeys[envelope.IdempotencyKey] = true
        state.EventsProcessed++

        // Determine target workflows
        targets := resolveTargets(envelope.EventType)
        if len(targets) == 0 {
            // Unknown event — fire DLQ activity, continue
            workflow.ExecuteActivity(ctx, WriteDLQActivity, envelope)
            continue
        }

        // Spawn child workflow per target (fire-and-continue, no blocking)
        for _, target := range targets {
            childCtx := workflow.WithChildOptions(ctx, workflow.ChildWorkflowOptions{
                WorkflowID: fmt.Sprintf("%s:%s:%s", target, envelope.TenantID, envelope.EventID),
                TaskQueue:  "AI_TASK_QUEUE",
            })
            // Non-blocking: parent does NOT wait for child completion
            workflow.ExecuteChildWorkflow(childCtx, target, envelope)
        }
    }
}

func resolveTargets(eventType string) []string {
    if multi, ok := multiRouteEvents[eventType]; ok {
        return multi
    }
    if single, ok := eventTypeToWorkflow[eventType]; ok {
        return []string{single}
    }
    return nil // unknown
}
```

**Run invariants + tests:** `go test ./internal/workflow -v` → **expect PASS (9 tests)**

---

## PHASE 6 — Finance Monitor Agent

### Test first:

**File:** `apps/ai/tests/test_finance_monitor.py`

```python
import pytest
from datetime import datetime, timezone, timedelta
from apps.ai.src.agents.finance_monitor import FinanceMonitorAgent

TENANT = "test-tenant-finance"

class TestFinanceMonitor:

    def setup_method(self):
        self.agent = FinanceMonitorAgent()

    def test_spend_anomaly_2sigma_fires(self):
        state = {
            "tenant_id": TENANT,
            "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
            "runway_months": 8.0,
        }
        event = {"event_type": "BANK_WEBHOOK", "vendor": "AWS",
                 "amount": 42000, "description": "AWS consolidated bill"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert "AWS" in result["headline"]
        assert "2.3" in result["headline"] or "2×" in result["headline"]
        assert result["urgency"] == "high"

    def test_spend_within_1sigma_silent(self):
        state = {
            "tenant_id": TENANT,
            "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
            "runway_months": 8.0,
        }
        event = {"event_type": "BANK_WEBHOOK", "vendor": "AWS",
                 "amount": 19500, "description": "AWS consolidated bill"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is False

    def test_runway_critical_fires(self):
        state = {"tenant_id": TENANT, "vendor_baselines": {},
                 "runway_months": 2.5}
        event = {"event_type": "TIME_TICK_DAILY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert result["urgency"] == "critical"
        assert "runway" in result["headline"].lower()

    def test_runway_warning_fires(self):
        state = {"tenant_id": TENANT, "vendor_baselines": {},
                 "runway_months": 5.0}
        event = {"event_type": "TIME_TICK_DAILY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is True
        assert result["urgency"] == "warn"

    def test_runway_healthy_silent(self):
        state = {"tenant_id": TENANT, "vendor_baselines": {},
                 "runway_months": 12.0}
        event = {"event_type": "TIME_TICK_DAILY"}
        result = self.agent.run(state, event)
        assert result["fire_telegram"] is False

    def test_agent_output_written_to_postgres(self):
        state = {"tenant_id": TENANT, "vendor_baselines": {}, "runway_months": 8.0}
        event = {"event_type": "TIME_TICK_DAILY"}
        result = self.agent.run(state, event)
        assert result["agent_output_id"] is not None

    def test_qdrant_memory_written(self):
        state = {"tenant_id": TENANT,
                 "vendor_baselines": {"Vercel": {"avg": 5000, "stddev": 500}},
                 "runway_months": 8.0}
        event = {"event_type": "BANK_WEBHOOK", "vendor": "Vercel",
                 "amount": 12000, "description": "Vercel Pro"}
        result = self.agent.run(state, event)
        assert result["qdrant_point_id"] is not None

    def test_no_jargon_in_headline(self):
        from apps.ai.src.agents.base import BANNED_JARGON
        state = {"tenant_id": TENANT,
                 "vendor_baselines": {"AWS": {"avg": 18000, "stddev": 2000}},
                 "runway_months": 8.0}
        event = {"event_type": "BANK_WEBHOOK", "vendor": "AWS",
                 "amount": 42000, "description": "AWS bill"}
        result = self.agent.run(state, event)
        for term in BANNED_JARGON:
            assert term.lower() not in result.get("headline", "").lower()
```

**Run:** `uv run pytest tests/test_finance_monitor.py -v` → **expect FAIL**

### Implement:

**File:** `apps/ai/src/agents/finance_monitor.py`

See full implementation in user's brief above (FinanceMonitorAgent class with all methods).

**Run invariants + tests:** `uv run pytest tests/test_finance_monitor.py -v` → **expect PASS (8 tests)**

---

## PHASE 7 — Revenue Tracker Agent

### Test first:

**File:** `apps/ai/tests/test_revenue_tracker.py`

```python
class TestRevenueTracker:

    def test_stale_deal_7d_fires(self):
        # pipeline_deals: last_contact_at = 9 days ago, stage = NEGOTIATION
        # event: TIME_TICK_WEEKLY
        # assert: fire_telegram=True, deal name in headline

    def test_active_deal_silent(self):
        # pipeline_deals: last_contact_at = 2 days ago
        # assert: fire_telegram=False

    def test_mrr_milestone_crosses_1L(self):
        # current_mrr = 98000, new payment = 3500
        # assert: fire_telegram=True, is_good_news=True
        # assert: "1,00,000" or "1L" in headline

    def test_routine_payment_silent(self):
        # current_mrr = 50000, new payment = 1500 (no milestone)
        # assert: fire_telegram=False

    def test_concentration_risk_fires(self):
        # single customer = 38% of last 90d revenue
        # assert: fire_telegram=True
        # assert: percentage mentioned in headline

    def test_weekly_summary_written_to_qdrant(self):
        # TIME_TICK_WEEKLY event
        # assert: qdrant_point_id not None

    def test_no_jargon_in_output(self):
        # stale deal scenario
        # assert: no BANNED_JARGON in headline or do_this
```

### Key implementation logic:

**File:** `apps/ai/src/agents/revenue_tracker.py`

```python
MRR_MILESTONES_INR = [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]
STALE_DEAL_DAYS    = 7
CONCENTRATION_PCT  = 0.30   # 30% threshold

class RevenueTrackerAgent(BaseAgent):
    agent_name = "revenue_tracker"

    def run(self, state: dict, event: dict) -> dict:
        etype = event.get("event_type", "")
        result = None

        if etype == "PAYMENT_SUCCESS":
            result = self._handle_payment(state, event)
        elif etype in ("CRM_DEAL_CREATED", "CRM_DEAL_UPDATED"):
            result = self._update_pipeline(state, event)
        elif etype == "TIME_TICK_WEEKLY":
            result = self._weekly_summary(state, event)
        else:
            result = AgentResult(tenant_id=state["tenant_id"],
                                 agent_name=self.agent_name)

        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        if result.fire_telegram or etype == "TIME_TICK_WEEKLY":
            result.qdrant_point_id = self._write_qdrant_memory(
                state["tenant_id"],
                f"Revenue event: {result.headline or etype}",
                "revenue",
            )
        return result.__dict__
```

**Run invariants + tests** → **PASS (7 tests)**. Commit.

---

## PHASE 8 — CS Agent

### Test first:

**File:** `apps/ai/tests/test_cs_agent.py`

```python
class TestCSAgent:
    def test_signup_initializes_state(self):          # CSState created in DB
    def test_d1_message_queued(self):                 # TIME_TICK_D1 → fire_telegram=True
    def test_d7_no_login_risk_high(self):             # last_seen > 7d → risk_score > 0.7, fire
    def test_active_user_risk_low(self):              # logged in yesterday → fire=False
    def test_support_ticket_faq_draft(self):          # ticket text → draft reply generated
    def test_support_ticket_escalation(self):         # 3 tickets in 48h → fire founder
    def test_risk_score_stored_in_postgres(self):     # cs_customers.risk_score updated
```

### Key implementation logic:

**File:** `apps/ai/src/agents/cs_agent.py`

```python
D_SEQUENCE = {1: "D1", 3: "D3", 7: "D7"}
CHURN_RISK_THRESHOLD = 0.7
ESCALATION_TICKET_COUNT = 3
ESCALATION_WINDOW_HOURS = 48

class CSAgent(BaseAgent):
    agent_name = "cs_agent"

    def run(self, state: dict, event: dict) -> dict:
        etype = event.get("event_type", "")
        result = None

        if etype == "USER_SIGNED_UP":
            result = self._on_signup(state, event)
        elif etype in ("TIME_TICK_D1", "TIME_TICK_D3", "TIME_TICK_D7"):
            result = self._on_time_tick(state, event)
        elif etype == "SUPPORT_TICKET_CREATED":
            result = self._on_support_ticket(state, event)
        elif etype == "USER_LOGGED_IN":
            result = self._on_login(state, event)
        else:
            result = AgentResult(tenant_id=state["tenant_id"],
                                 agent_name=self.agent_name)

        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        return result.__dict__
```

**Run invariants + tests** → **PASS (7 tests)**. Commit.

---

## PHASE 9 — People Coordinator

### Test first:

**File:** `apps/ai/tests/test_people_coordinator.py`

```python
class TestPeopleCoordinator:
    def test_eng_checklist_has_github(self):         # role=eng → checklist includes github
    def test_sales_checklist_no_github(self):        # role=sales → no github
    def test_incomplete_item_nag_24h(self):          # D1 tick, github not confirmed → nag
    def test_complete_checklist_no_nag(self):        # all items done → fire=False
    def test_offboarding_generates_revoke_list(self):# EMPLOYEE_TERMINATED → revoke list
    def test_checklist_confirmed_updates_db(self):   # CHECKLIST_ITEM_CONFIRMED → DB updated
    def test_new_hire_fires_telegram(self):          # EMPLOYEE_CREATED → fire=True
```

### Key implementation logic:

**File:** `apps/ai/src/agents/people_coordinator.py`

```python
CHECKLISTS_BY_ROLE = {
    "eng":    ["slack", "notion", "github", "gworkspace", "linear"],
    "ops":    ["slack", "notion", "gworkspace"],
    "sales":  ["slack", "notion", "gworkspace", "crm"],
    "design": ["slack", "notion", "gworkspace", "figma"],
    "default":["slack", "notion", "gworkspace"],
}

REVOKE_LIST_BY_ROLE = {
    "eng":    ["github", "linear", "notion", "slack", "gworkspace", "aws"],
    "ops":    ["notion", "slack", "gworkspace"],
    "sales":  ["crm", "notion", "slack", "gworkspace"],
    "default":["slack", "notion", "gworkspace"],
}

class PeopleCoordinatorAgent(BaseAgent):
    agent_name = "people_coordinator"

    def run(self, state: dict, event: dict) -> dict:
        etype = event.get("event_type", "")

        if etype == "EMPLOYEE_CREATED":
            result = self._on_hire(state, event)
        elif etype == "EMPLOYEE_TERMINATED":
            result = self._on_offboard(state, event)
        elif etype == "CHECKLIST_ITEM_CONFIRMED":
            result = self._on_confirmed(state, event)
        elif etype in ("TIME_TICK_D1", "TIME_TICK_D3"):
            result = self._nag_loop(state, event)
        else:
            result = AgentResult(tenant_id=state["tenant_id"],
                                 agent_name=self.agent_name)

        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        return result.__dict__
```

**Run invariants + tests** → **PASS (7 tests)**. Commit.

---

## PHASE 10 — Chief of Staff

### Test first:

**File:** `apps/ai/tests/test_chief_of_staff.py`

```python
class TestChiefOfStaff:
    def test_briefing_max_5_items(self):
    def test_briefing_has_one_positive_item(self):
    def test_briefing_no_banned_jargon(self):
    def test_high_urgency_ranked_first(self):
    def test_critical_items_fire_telegram(self):
    def test_investor_draft_contains_revenue_burn_runway(self):
    def test_empty_week_graceful(self):
    def test_briefing_written_to_qdrant(self):
```

### Key implementation logic:

**File:** `apps/ai/src/agents/chief_of_staff.py`

```python
MAX_BRIEFING_ITEMS = 5
URGENCY_RANK = {"critical": 0, "high": 1, "warn": 2, "low": 3}

class ChiefOfStaffAgent(BaseAgent):
    agent_name = "chief_of_staff"

    def run(self, state: dict, event: dict) -> dict:
        etype = event.get("event_type", "")

        if etype == "TIME_TICK_WEEKLY":
            result = self._compose_weekly_briefing(state)
        elif etype == "TIME_TICK_MONTHLY":
            result = self._compose_investor_draft(state)
        elif etype == "AGENT_OUTPUT":
            result = self._ingest_agent_output(state, event)
        else:
            result = AgentResult(tenant_id=state["tenant_id"],
                                 agent_name=self.agent_name)

        violations = result.validate_tone()
        assert not violations, f"Tone violations: {violations}"
        result.agent_output_id = self._write_agent_output(state["tenant_id"], result)
        result.qdrant_point_id = self._write_qdrant_memory(
            state["tenant_id"],
            f"Briefing: {result.headline}",
            "briefing",
        )
        return result.__dict__
```

**Run invariants + tests** → **PASS (8 tests)**. Commit.

---

## PHASE 11 — Telegram Handler

### Test first:

**File:** `apps/core/internal/api/telegram_test.go`

```go
func TestTelegramSendMessage(t *testing.T)              {}
func TestTelegramInlineKeyboardRendered(t *testing.T)   {}
func TestTelegramCallbackParsed(t *testing.T)           {}
func TestTelegramCallbackWritesToHITLTable(t *testing.T){}
func TestTelegramCallbackPayNowEmitsEvent(t *testing.T) {}
func TestTelegramCallbackMarkOKSilent(t *testing.T)     {}
```

### Implement:

**File:** `apps/core/internal/api/telegram.go`

See full implementation in user's brief above (TelegramHandler struct with all methods).

**Run invariants + tests:** `go test ./internal/api -run TestTelegram -v` → **PASS (6 tests)**. Commit.

---

## PHASE 12 — E2E Suite + Test Runner

### E2E tests:

**File:** `apps/ai/tests/test_e2e_sarthi.py`

```python
import pytest, asyncio

@pytest.mark.e2e
async def test_finance_anomaly_full_flow(http_client, seed_tenant):
    """
    POST /webhooks/bank (AWS bill 2.3× baseline)
    → raw_events row created
    → FinanceWorkflow triggered via Temporal
    → FinanceMonitor detects anomaly
    → agent_outputs row: urgency=high
    → Telegram message queued
    → Qdrant memory written
    """
    payload = {"vendor": "AWS", "amount": 42000, "description": "AWS consolidated"}
    sig = compute_hmac(payload, BANK_SECRET)
    resp = await http_client.post("/webhooks/bank",
        json=payload, headers={"X-Bank-Signature": sig})
    assert resp.status_code == 200

    job = await poll_agent_output("finance_monitor", timeout=30)
    assert job["urgency"] == "high"
    assert job["headline"] is not None
```

(See user's brief for all 5 E2E test implementations)

### Test runner:

**File:** `scripts/test_sarthi.sh`

See full implementation in user's brief above.

### Tag:

```bash
bash scripts/test_sarthi.sh
# Must show: PASSED: N  FAILED: 0

git tag v1.0.0-alpha
git push origin v1.0.0-alpha
```

---

## Definition of Done

```
REQUIRED BEFORE v1.0.0-alpha TAG:

  ✅ Phase 5:  Temporal router — 9 tests, CAN at 1,000
  ✅ Phase 6:  Finance Monitor — 8 tests, 2σ anomaly + runway
  ✅ Phase 7:  Revenue Tracker — 7 tests, stale deals + milestones
  ✅ Phase 8:  CS Agent — 7 tests, D1/D7 sequence + churn
  ✅ Phase 9:  People Coordinator — 7 tests, role checklists + nag
  ✅ Phase 10: Chief of Staff — 8 tests, ≤5 items, jargon-free
  ✅ Phase 11: Telegram — 6 tests, outbound + callback + HITL log
  ✅ Phase 12: 5 E2E tests pass, bash test_sarthi.sh → FAILED: 0
  ✅ All original tests still passing (baseline preserved)
  ✅ No banned jargon anywhere in agent output strings
  ✅ No raw JSON in any Temporal signal

BLOCKED IF:
  ✗ Any E2E test uses a mock
  ✗ Any agent fires Telegram for non-urgent events
  ✗ Chief of Staff sends > 5 items in a briefing
  ✗ Temporal signal contains inline payload (not PayloadRef)
```

---

**Document Version:** 1.0  
**Last Updated:** March 18, 2026  
**Status:** Ready for Phase 5 implementation
