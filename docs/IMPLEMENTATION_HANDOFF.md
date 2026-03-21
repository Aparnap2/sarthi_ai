# Sarthi v1.0 — Implementation Handoff Report
## Current Status & Next Steps for Coding Agent

**Date:** March 18, 2026  
**Branch:** `fix/e2e-tests-and-env-vars` (from `v4.2.0-alpha`)  
**Baseline:** 255 tests passing

---

## ✅ COMPLETED (2/12 Phases)

### Phase 0: Baseline Verification ✅

**Status:** COMPLETE

**What was done:**
- Verified v4.2.0-alpha baseline (255 tests passing)
- Confirmed Docker infrastructure running:
  - PostgreSQL (`iterateswarm-postgres` on port 5433)
  - Redpanda (`iterateswarm-redpanda` on port 19092)
  - Neo4j (`saarathi-neo4j` on port 7687)
- Created feature branch structure

**Files touched:**
- None (verification only)

**Tests:** 255 PASS

---

### Phase 1: Database Migration 002 ✅

**Status:** COMPLETE

**What was done:**
- Created migration file: `apps/core/internal/db/migrations/002_sarthi_v1.sql`
- Applied to Docker PostgreSQL successfully
- Created comprehensive test file: `apps/core/internal/db/migration_002_test.go` (337 lines)
- All 10 v1.0 tables verified with 12 tests

**Files created:**
1. `apps/core/internal/db/migrations/002_sarthi_v1.sql` (8.9 KB)
2. `apps/core/internal/db/migration_002_test.go` (337 lines)

**Tables created (10 total):**
1. `founders` — Tenant/Founder management (tenant_id, telegram_chat_id, stage)
2. `raw_events` — Event archive with idempotency_key
3. `transactions` — Revenue/expense tracking
4. `pipeline_deals` — CRM pipeline for Revenue Tracker
5. `cs_customers` — Customer Success tracking (onboarding_stage, risk_score)
6. `employees` — HR/People ops (role_function, checklist JSONB)
7. `finance_snapshots` — Burn rate, runway tracking
8. `vendor_baselines` — Vendor spend baselines (avg, stddev)
9. `agent_outputs` — Agent output log (consumed by CoS)
10. `hitl_actions` — Telegram HITL callback tracking

**Indexes created:**
- `idx_raw_events_tenant_type` — (tenant_id, event_type, received_at DESC)
- Plus unique constraints on all _id columns

**Test results:**
```
TestMigration002TablesExist — PASS
TestMigration002IdempotencyKeyUnique — PASS
TestMigration002FoundersCRUD — PASS
TestMigration002TransactionsCRUD — PASS
TestMigration002PipelineDealsUnique — PASS
TestMigration002CsCustomersUnique — PASS
TestMigration002EmployeesUnique — PASS
TestMigration002VendorBaselinesUnique — PASS
TestMigration002RawEventsIndex — PASS
TestMigration002AgentOutputsInsert — PASS
TestMigration002HitlActionsInsert — PASS
TestMigration002FinanceSnapshotsInsert — PASS

TOTAL: 12/12 PASS ✅
```

---

## 🔲 REMAINING (10/12 Phases)

### Phase 2: Event Envelope Field Renames

**Status:** NOT STARTED

**What needs to be done:**
Rename EventEnvelope fields from v4.3.0-alpha pattern to v1.0 pattern.

**Field rename map:**
| Old Field (v4.3.0-alpha) | New Field (v1.0) | Reason |
|---|---|---|
| `FounderID` | `TenantID` | Multi-tenant from day one |
| `EventName` | `EventType` | Clearer semantics (normalized type) |
| `SOPName` | `AgentName` | v1.0 uses agents, not SOPs |
| `Topic` | *(removed)* | Normalizer handles routing |
| `Version` | *(removed)* | Unnecessary for v1.0 |

**Files to modify:**
1. `apps/core/internal/events/envelope.go` — Update Go struct
2. `apps/ai/src/schemas/event_envelope.py` — Update Pydantic model
3. `apps/ai/tests/test_event_envelope.py` — Update test fixtures
4. `apps/core/internal/events/envelope_test.go` — Update Go tests

**Expected tests:** 10 PASS (8 Python + 2 Go)

**Estimated time:** 2-3 hours

---

### Phase 3: Event Normalizer (10 Mappings)

**Status:** NOT STARTED

**What needs to be done:**
Create normalizer that maps source + raw_event → EventType.

**Event mappings (10 total):**
| Source | Raw Event | Normalized EventType |
|---|---|---|
| Razorpay | `payment.captured` | `PAYMENT_SUCCESS` |
| Razorpay | `subscription.cancelled` | `SUBSCRIPTION_CANCELED` |
| Stripe | `invoice.paid` | `PAYMENT_SUCCESS` |
| Intercom/Crisp | `user.created` | `USER_SIGNED_UP` |
| Intercom | `conversation.created` | `SUPPORT_TICKET_CREATED` |
| Keka/Darwinbox | `employee.created` | `EMPLOYEE_CREATED` |
| Keka | `employee.terminated` | `EMPLOYEE_TERMINATED` |
| Bank webhook | `bank.transaction` | `BANK_WEBHOOK` |
| Cron | `cron.weekly` | `TIME_TICK_WEEKLY` |
| Cron | `cron.daily` | `TIME_TICK_DAILY` |

**Files to create:**
1. `apps/core/internal/events/normalizer.go` — Normalization logic
2. `apps/core/internal/events/normalizer_test.go` — Tests (10 mappings)

**Expected tests:** 2 PASS

**Estimated time:** 2 hours

---

### Phase 4: 5 Webhook Handlers

**Status:** NOT STARTED

**What needs to be done:**
Create 5 webhook handlers with HMAC verification, DLQ, idempotency.

**Handlers to create:**
1. **Payments Handler** (`apps/core/internal/api/payments.go`)
   - Razorpay + Stripe HMAC-SHA256 verification
   - Store raw event → PostgreSQL
   - Publish EventEnvelope → Redpanda
   - Return 200 immediately

2. **CRM Handler** (`apps/core/internal/api/crm.go`)
   - Same pattern as payments

3. **Support Handler** (`apps/core/internal/api/support.go`)
   - Intercom/Crisp webhooks

4. **HR Handler** (`apps/core/internal/api/hr.go`)
   - Keka/Darwinbox webhooks

5. **Bank Handler** (`apps/core/internal/api/bank.go`)
   - Bank webhooks or gws CLI cron

**Files to create:**
- 5 handler files (~200 lines each)
- 5 test files (~80 lines each)

**Expected tests:** 20 PASS (5 handlers × 4 tests each)

**Estimated time:** 1-2 days

---

### Phase 5: Temporal Workflow Router

**Status:** NOT STARTED

**What needs to be done:**
Create parent workflow that routes EventEnvelope to child workflows.

**Key features:**
- Continue-As-New at 1,000 events (not 5,000)
- Idempotency check (skip duplicates)
- Route by EventType:
  - `PAYMENT_* | SUBSCRIPTION_* | CRM_* | TIME_TICK_*` → RevenueWorkflow
  - `USER_* | SUPPORT_*` → CSWorkflow
  - `EMPLOYEE_* | CHECKLIST_*` → PeopleWorkflow
  - `EXPENSE_* | BANK_* | TIME_TICK_DAILY` → FinanceWorkflow
  - `TIME_TICK_WEEKLY | TIME_TICK_MONTHLY | AGENT_OUTPUT` → CoSWorkflow

**Files to create:**
1. `apps/core/internal/workflow/sarthi_router.go` — Parent workflow
2. `apps/core/internal/workflow/sarthi_router_test.go` — Tests

**Expected tests:** 3 PASS

**Estimated time:** 1 day

---

### Phase 6: Finance Monitor Agent

**Status:** NOT STARTED

**What needs to be done:**
Create LangGraph agent with 6 nodes for spend anomaly + runway detection.

**LangGraph nodes (6):**
1. `UpdateSnapshot` — Recompute burn + runway
2. `VendorBaseline` — Load typical spend per vendor (avg ± 2σ)
3. `DetectAnomaly` — Compare current tx to baseline
4. `ExplainAnomaly` — Query Qdrant: did this pattern appear before?
5. `DecideAlert` — Severity (info/warn/critical) + who to ping
6. `EmitActions` — Alert + runway update

**Thresholds:**
- Anomaly: `current_spend > vendor_baseline + 2σ`
- Runway critical: `runway_months < 3`
- Runway warning: `runway_months < 6`

**Files to create:**
1. `apps/ai/src/agents/finance_monitor.py` (~300 lines)
2. `apps/ai/tests/test_finance_monitor.py` (~180 lines)

**Expected tests:** 6 PASS

**Estimated time:** 1-2 days

---

### Phase 7: Revenue Tracker Agent

**Status:** NOT STARTED

**What needs to be done:**
Create LangGraph agent with 6 nodes for MRR + stale deals.

**Reuse opportunity:** 80% logic from `apps/ai/src/sops/revenue_received.py` (v4.3.0-alpha)

**LangGraph nodes (6):**
1. `IngestEvent` — Classify event type, extract amount + customer
2. `UpdateMetrics` — Recompute MRR + 7d/30d windows
3. `DetectStaleDeals` — Deals with `last_contact_at > 7 days`
4. `DecideAlerts` — Which founders to ping + why
5. `WriteMemory` — Write weekly summary to Qdrant
6. `EmitActions` — Telegram messages + WEEKLY_REVENUE_SUMMARY

**Thresholds:**
- MRR milestones: ₹1L, ₹5L, ₹10L, ₹50L, ₹1Cr
- Stale deal: `last_contact_at > 7 days AND stage != CLOSED`
- Concentration risk: single customer > 30% of last 90d revenue

**Files to create:**
1. `apps/ai/src/agents/revenue_tracker.py` (~300 lines)
2. `apps/ai/tests/test_revenue_tracker.py` (~180 lines)

**Expected tests:** 6 PASS

**Estimated time:** 1 day (2-3 days if not reusing v4.3.0-alpha code)

---

### Phase 8: CS Agent

**Status:** NOT STARTED

**What needs to be done:**
Create LangGraph agent with 5 nodes for onboarding + churn risk.

**LangGraph nodes (5):**
1. `OnSignup` — Initialize CSState, queue D1 message
2. `OnTimeTick` — Check stage, decide next touchpoint
3. `OnSupportTicket` — Classify (FAQ vs real issue), draft reply
4. `RiskAssessment` — Infer churn risk from inactivity + ticket count
5. `EmitActions` — User messages + founder alert if risk_score > 0.7

**Thresholds:**
- High churn risk: `last_seen_at > 7 days` AND `onboarding_stage != DONE`
- Ticket escalation: `ticket_count > 2 in 48h`

**Files to create:**
1. `apps/ai/src/agents/cs_agent.py` (~250 lines)
2. `apps/ai/tests/test_cs_agent.py` (~180 lines)

**Expected tests:** 6 PASS

**Estimated time:** 1-2 days

---

### Phase 9: People Coordinator Agent

**Status:** NOT STARTED

**What needs to be done:**
Create LangGraph agent with 5 nodes for role-based checklists.

**LangGraph nodes (5):**
1. `OnHireEvent` — Create checklist based on role_function
2. `GenerateChecklist` — Eng ≠ Ops ≠ Sales checklists
3. `ProgressTracking` — Track confirmed items, compute % complete
4. `NagLoop` — Send reminder if item incomplete after 24h
5. `Offboarding` — Mirror of onboarding, generate revoke list

**Role-based checklists:**
| Tool | Eng | Ops | Sales |
|---|---|---|---|
| GitHub | ✅ | — | — |
| Notion | ✅ | ✅ | ✅ |
| Slack | ✅ | ✅ | ✅ |
| Google Workspace | ✅ | ✅ | ✅ |
| Linear/Jira | ✅ | — | — |
| CRM | — | — | ✅ |

**Files to create:**
1. `apps/ai/src/agents/people_coordinator.py` (~250 lines)
2. `apps/ai/tests/test_people_coordinator.py` (~180 lines)

**Expected tests:** 6 PASS

**Estimated time:** 1-2 days

---

### Phase 10: Chief of Staff Agent

**Status:** NOT STARTED

**What needs to be done:**
Create LangGraph agent with 5 nodes for weekly briefing + investor draft.

**Reuse opportunity:** 60% logic from `apps/ai/src/sops/weekly_briefing.py` (v4.3.0-alpha)

**LangGraph nodes (5):**
1. `CollectSignals` — Pull last N agent outputs from PostgreSQL + Qdrant
2. `Prioritize` — Rank by urgency × impact score
3. `ComposeBriefing` — LLM: 3–5 bullets, plain English, no jargon
4. `ComposeInvestorDraft` — Optional, monthly, from finance + revenue data
5. `EmitActions` — Telegram briefing + investor draft

**Briefing rules:**
- Max 5 items
- Always include one positive item if data supports it
- No jargon: banned terms list enforced (`leverage, synergy, utilize, streamline, paradigm`)
- Each item: one headline + one `[Action]` button

**Files to create:**
1. `apps/ai/src/agents/chief_of_staff.py` (~300 lines)
2. `apps/ai/tests/test_chief_of_staff.py` (~180 lines)

**Expected tests:** 6 PASS

**Estimated time:** 1 day (2-3 days if not reusing v4.3.0-alpha code)

---

### Phase 11: Telegram Handler

**Status:** NOT STARTED

**What needs to be done:**
Create Telegram handler for outbound messages + inbound callbacks.

**Decision made:** Option A — Pure Bot API (`go-telegram-bot-api/telegram-bot-api`)

**Features:**
- Outbound: POST to Telegram Bot API with inline keyboard buttons
- Inbound: `POST /webhooks/telegram/callback`
  - Parse `callback_query.data`
  - Update `hitl_actions` table
  - Emit downstream action (PAYMENT_INSTRUCTION, etc.)

**Files to create:**
1. `apps/core/internal/api/telegram.go` (~200 lines)
2. `apps/core/internal/api/telegram_test.go` (~160 lines)

**Expected tests:** 4 PASS

**Estimated time:** 1 day

---

### Phase 12: E2E Suite + Test Runner

**Status:** NOT STARTED

**What needs to be done:**
Create 5 E2E tests + update test runner script.

**E2E tests to create:**
1. `test_finance_anomaly_full_flow` — AWS spike detection
2. `test_weekly_revenue_briefing` — Monday briefing
3. `test_onboarding_sequence_with_nag` — New hire checklist
4. `test_cs_churn_alert` — High churn risk detection
5. `test_investor_update_draft` — Monthly investor update

**Files to create:**
1. `apps/ai/tests/test_e2e_sarthi.py` (~400 lines)
2. Update `scripts/test_sarthi.sh` (add E2E step)

**Expected tests:** 5 PASS

**Estimated time:** 1-2 days

---

## Summary

### Completed
| Phase | Deliverable | Tests | Status |
|-------|-------------|-------|--------|
| 0 | Baseline verification | 255 | ✅ COMPLETE |
| 1 | Database migration 002 | 12 | ✅ COMPLETE |

### Remaining
| Phase | Deliverable | Tests | Est. Time |
|-------|-------------|-------|-----------|
| 2 | Event envelope renames | 10 | 2-3 hours |
| 3 | Event normalizer | 2 | 2 hours |
| 4 | 5 webhook handlers | 20 | 1-2 days |
| 5 | Temporal router | 3 | 1 day |
| 6 | Finance Monitor | 6 | 1-2 days |
| 7 | Revenue Tracker | 6 | 1 day |
| 8 | CS Agent | 6 | 1-2 days |
| 9 | People Coordinator | 6 | 1-2 days |
| 10 | Chief of Staff | 6 | 1 day |
| 11 | Telegram handler | 4 | 1 day |
| 12 | E2E suite | 5 | 1-2 days |

**Total remaining:** ~12-15 days of work

**Total tests target:** 325+ for v1.0.0-alpha

---

## Critical Invariants (Enforce Before Every Commit)

```bash
# I-1: No raw JSON in Temporal signals (only PayloadRef strings)
grep -rn "json.Marshal\|json.Unmarshal" apps/core/internal/workflow/ \
  | grep -v "_test.go" | grep -v "// safe:" \
  && echo "FAIL: raw JSON in workflow" && exit 1

# I-2: No AzureOpenAI() outside config/llm.py
grep -rn "AzureOpenAI(" apps/ai/src/ | grep -v "config/llm.py" \
  && echo "FAIL: direct AzureOpenAI() call" && exit 1

# I-3: All 255 baseline tests still pass
cd apps/ai && uv run pytest tests/ -x -q --timeout=90 && cd -
cd apps/core && go test ./... -timeout=60s && cd -

# I-4: No jargon in Telegram messages
grep -rn "leverage\|synergy\|utilize\|streamline\|paradigm" \
  apps/ai/src/agents/ | grep -v "# allowed:" \
  && echo "FAIL: banned jargon in agent output" && exit 1
```

---

## Next Agent Instructions

**Start here:**
```bash
cd /home/aparna/Desktop/iterate_swarm
git checkout -b feature/sarthi-v1 v4.2.0-alpha
```

**First task (Phase 2):**
1. Update `apps/core/internal/events/envelope.go` — rename fields
2. Update `apps/ai/src/schemas/event_envelope.py` — rename fields
3. Update test files
4. Run tests: `uv run pytest tests/test_event_envelope.py -v`
5. Run invariants
6. Commit

**Then proceed sequentially through Phases 3-12.**

---

**Document Version:** 1.0  
**Last Updated:** March 18, 2026  
**Status:** Ready for Phase 2 implementation
