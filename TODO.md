# Sarthi v1.0 — Implementation TODO List
## 5-Agent Ops Automation System

**Version:** 1.0.0-alpha  
**Date:** March 2026  
**Status:** Phase 0 COMPLETE ✅

---

## Phase 0 ✅ — Baseline Verification (COMPLETE)

**Target:** Confirm v4.2.0-alpha baseline (255 tests passing)

### Completed Tasks

- [x] Run `git log --oneline -3` — shows v4.2.0-alpha context
- [x] Create feature branch: `git checkout -b feature/sarthi-v1 v4.2.0-alpha`
- [x] Run baseline tests: `bash scripts/test_sarthi.sh` — 255 tests PASS
- [x] Check current migration number: `ls migrations/ | sort | tail -1`

**Exit Criteria:** ✅ MET

---

## Phase 1 🔲 — Database Migration (Commit 1)

**Target:** 9 new tables for 5-agent system

### Tasks

- [ ] Create `apps/core/internal/db/migrations/NNN_sarthi_v1.sql`
  - [ ] founders table (tenant_id, telegram_chat_id)
  - [ ] raw_events table (payload storage, idempotency_key)
  - [ ] transactions table (revenue/expense tracking)
  - [ ] pipeline_deals table (CRM deals, last_contact_at)
  - [ ] cs_customers table (onboarding_stage, risk_score)
  - [ ] employees table (checklist JSONB, role_function)
  - [ ] finance_snapshots table (burn_rate, runway_months)
  - [ ] vendor_baselines table (avg_monthly, stddev_monthly)
  - [ ] agent_outputs table (consumed by CoS)
  - [ ] hitl_actions table (Telegram callback tracking)
- [ ] Apply migration: `psql $DATABASE_URL -f migrations/NNN_sarthi_v1.sql`
- [ ] Create `apps/core/internal/db/migration_test.go`
  - [ ] TestMigration_TablesExist
  - [ ] TestMigration_IdempotencyUnique
- [ ] Run tests: `go test ./internal/db -run TestMigration -v` → expect PASS

**Exit Criteria:**
- 9 tables created
- Idempotency constraint works
- 2+ tests passing

---

## Phase 2 🔲 — Event Envelope (Commit 2)

**Target:** Canonical envelope (Go + Python)

### Tasks

- [ ] Create `apps/core/internal/events/envelope.go`
  - [ ] EventEnvelope struct (TenantID, EventType, PayloadRef, etc.)
  - [ ] NEVER contains raw JSON — only PayloadRef string
- [ ] Create `apps/ai/src/schemas/event_envelope.py`
  - [ ] EventEnvelope Pydantic model
  - [ ] Validators (event_name not empty, payload_ref is storage ref)
- [ ] Create `apps/ai/tests/test_event_envelope.py`
  - [ ] test_valid_envelope_passes
  - [ ] test_empty_event_name_fails
  - [ ] test_raw_json_as_payload_ref_fails
  - [ ] test_all_sources_valid
- [ ] Run tests: `uv run pytest tests/test_event_envelope.py -v` → expect 4 PASS

**Exit Criteria:**
- Envelope schema in Go + Python
- 4 tests passing
- Rejects raw JSON in payload_ref

---

## Phase 3 🔲 — Event Normalization (Commit 3)

**Target:** 10 source → EventType mappings

### Tasks

- [ ] Create `apps/core/internal/events/normalizer.go`
  - [ ] Normalize(source, raw_event) → EventType
  - [ ] Unknown events → dead_letter_events (no error)
- [ ] Event mappings:
  - [ ] Razorpay `payment.captured` → `PAYMENT_SUCCESS`
  - [ ] Razorpay `subscription.cancelled` → `SUBSCRIPTION_CANCELED`
  - [ ] Stripe `invoice.paid` → `PAYMENT_SUCCESS`
  - [ ] Intercom `user.created` → `USER_SIGNED_UP`
  - [ ] Intercom `conversation.created` → `SUPPORT_TICKET_CREATED`
  - [ ] Keka `employee.created` → `EMPLOYEE_CREATED`
  - [ ] Keka `employee.terminated` → `EMPLOYEE_TERMINATED`
  - [ ] Bank `bank.transaction` → `BANK_WEBHOOK`
  - [ ] Cron `cron.weekly` → `TIME_TICK_WEEKLY`
  - [ ] Cron `cron.daily` → `TIME_TICK_DAILY`
- [ ] Create `apps/core/internal/events/normalizer_test.go`
  - [ ] TestNormalizer_10MappingsCorrect
  - [ ] TestNormalizer_UnknownEventToDLQ
- [ ] Run tests: `go test ./internal/events -run TestNormalizer -v` → expect PASS

**Exit Criteria:**
- 10 mappings implemented
- Unknown events go to DLQ
- 2+ tests passing

---

## Phase 4 🔲 — Go Webhook Handlers (Commit 4)

**Target:** 5 handlers with HMAC, DLQ, idempotency

### Tasks

#### Payments Handler
- [ ] Create `apps/core/internal/api/payments.go`
  - [ ] Razorpay HMAC-SHA256 verification
  - [ ] Store raw event in PostgreSQL FIRST
  - [ ] Publish EventEnvelope (PayloadRef only) to Redpanda
  - [ ] Return 200 immediately
- [ ] Create `apps/core/internal/api/payments_test.go`
  - [ ] TestPaymentsWebhook_ValidSignatureAccepted
  - [ ] TestPaymentsWebhook_InvalidSignatureRejected
  - [ ] TestPaymentsWebhook_UnknownEventToDLQ
  - [ ] TestPaymentsWebhook_DuplicateIdempotent

#### CRM Handler
- [ ] Create `apps/core/internal/api/crm.go`
  - [ ] Same pattern as payments

#### Support Handler
- [ ] Create `apps/core/internal/api/support.go`

#### HR Handler
- [ ] Create `apps/core/internal/api/hr.go`

#### Bank Handler
- [ ] Create `apps/core/internal/api/bank.go`

- [ ] Run tests: `go test ./internal/api -v` → expect 20 PASS (5 handlers × 4 tests)

**Exit Criteria:**
- 5 webhook handlers
- HMAC verification working
- DLQ for unknown events
- Idempotency working
- 20 tests passing

---

## Phase 5 🔲 — Temporal Workflow Routing (Commit 5)

**Target:** Parent workflow with CAN at 1,000 events

### Tasks

- [ ] Create `apps/core/internal/workflow/sarthi_router.go`
  - [ ] Parent workflow receives EventEnvelope signal
  - [ ] Routes by EventType:
    - `PAYMENT_* | SUBSCRIPTION_* | CRM_* | TIME_TICK_*` → RevenueWorkflow
    - `USER_* | SUPPORT_*` → CSWorkflow
    - `EMPLOYEE_* | CHECKLIST_*` → PeopleWorkflow
    - `EXPENSE_* | BANK_* | TIME_TICK_DAILY` → FinanceWorkflow
    - `TIME_TICK_WEEKLY | TIME_TICK_MONTHLY | AGENT_OUTPUT` → CoSWorkflow
  - [ ] Continue-As-New at 1,000 events
- [ ] Create `apps/core/internal/workflow/sarthi_router_test.go`
  - [ ] TestSarthiRouter_CorrectWorkflowSpawned
  - [ ] TestSarthiRouter_CANFiresAt1000
  - [ ] TestSarthiRouter_DuplicateKeySkipped
- [ ] Run tests: `go test ./internal/workflow -run TestSarthiRouter -v` → expect PASS

**Exit Criteria:**
- Parent workflow routes correctly
- CAN fires at 1,000 events
- 3+ tests passing

---

## Phase 6 🔲 — Finance Monitor Agent (Commit 6)

**Target:** LangGraph agent with 6 nodes

### Tasks

- [ ] Create `apps/ai/src/agents/finance_monitor.py`
  - [ ] LangGraph nodes:
    - UpdateSnapshot (recompute burn + runway)
    - VendorBaseline (load avg ± 2σ)
    - DetectAnomaly (compare to baseline)
    - ExplainAnomaly (query Qdrant history)
    - DecideAlert (severity + who to ping)
    - EmitActions (alert + runway update)
  - [ ] Thresholds: 2σ anomaly, runway <3mo critical, <6mo warn
- [ ] Create `apps/ai/tests/test_finance_monitor.py`
  - [ ] test_spend_anomaly_2sigma_fires
  - [ ] test_spend_within_1sigma_silent
  - [ ] test_runway_critical_fires
  - [ ] test_runway_healthy_silent
  - [ ] test_anomaly_explained_by_qdrant_history
  - [ ] test_normal_expense_silent
- [ ] Run tests: `uv run pytest tests/test_finance_monitor.py -v` → expect 6 PASS

**Exit Criteria:**
- 6 LangGraph nodes implemented
- 2σ anomaly detection working
- 6 tests passing

---

## Phase 7 🔲 — Revenue Tracker Agent (Commit 7)

**Target:** LangGraph agent with 6 nodes

### Tasks

- [ ] Create `apps/ai/src/agents/revenue_tracker.py`
  - [ ] LangGraph nodes:
    - IngestEvent (classify, extract amount + customer)
    - UpdateMetrics (recompute MRR + windows)
    - DetectStaleDeals (last_contact_at >7 days)
    - DecideAlerts (milestone / stale / anomaly)
    - WriteMemory (weekly summary to Qdrant)
    - EmitActions (Telegram + WEEKLY_REVENUE_SUMMARY)
  - [ ] Thresholds: MRR milestones, stale >7d, concentration >30%
- [ ] Create `apps/ai/tests/test_revenue_tracker.py`
  - [ ] test_stale_deal_7d_fires
  - [ ] test_active_deal_silent
  - [ ] test_mrr_milestone_fires
  - [ ] test_routine_payment_silent
  - [ ] test_concentration_risk_fires
  - [ ] test_weekly_summary_written_to_qdrant
- [ ] Run tests: `uv run pytest tests/test_revenue_tracker.py -v` → expect 6 PASS

**Exit Criteria:**
- 6 LangGraph nodes implemented
- Stale deal detection working
- 6 tests passing

---

## Phase 8 🔲 — CS Agent (Commit 8)

**Target:** LangGraph agent with 5 nodes

### Tasks

- [ ] Create `apps/ai/src/agents/cs_agent.py`
  - [ ] LangGraph nodes:
    - OnSignup (initialize state, queue D1 message)
    - OnTimeTick (check stage, decide next touchpoint)
    - OnSupportTicket (classify FAQ vs real, draft reply)
    - RiskAssessment (infer churn from inactivity + tickets)
    - EmitActions (user messages + founder alert if risk >0.7)
  - [ ] Thresholds: last_seen >7d, ticket_count >2 in 48h
- [ ] Create `apps/ai/tests/test_cs_agent.py`
  - [ ] test_signup_initializes_cs_state
  - [ ] test_d1_message_queued
  - [ ] test_7d_no_login_risk_high
  - [ ] test_active_user_risk_low
  - [ ] test_support_ticket_faq_draft_reply
  - [ ] test_support_ticket_escalation
- [ ] Run tests: `uv run pytest tests/test_cs_agent.py -v` → expect 6 PASS

**Exit Criteria:**
- 5 LangGraph nodes implemented
- D1/D3/D7 sequence working
- 6 tests passing

---

## Phase 9 🔲 — People Coordinator Agent (Commit 9)

**Target:** LangGraph agent with 5 nodes

### Tasks

- [ ] Create `apps/ai/src/agents/people_coordinator.py`
  - [ ] LangGraph nodes:
    - OnHireEvent (create checklist based on role_function)
    - GenerateChecklist (eng ≠ ops ≠ sales)
    - ProgressTracking (track confirmed items, compute %)
    - NagLoop (reminder if incomplete after 24h)
    - Offboarding (mirror of onboarding, revoke list)
  - [ ] Role-based checklists (Eng: GitHub, Ops: no GitHub, Sales: CRM)
- [ ] Create `apps/ai/tests/test_people_coordinator.py`
  - [ ] test_eng_checklist_has_github
  - [ ] test_sales_checklist_no_github
  - [ ] test_incomplete_item_nag_after_24h
  - [ ] test_complete_checklist_no_nag
  - [ ] test_offboarding_generates_revoke_list
  - [ ] test_checklist_confirmed_updates_state
- [ ] Run tests: `uv run pytest tests/test_people_coordinator.py -v` → expect 6 PASS

**Exit Criteria:**
- 5 LangGraph nodes implemented
- Role-based checklists working
- 6 tests passing

---

## Phase 10 🔲 — Chief of Staff Agent (Commit 10)

**Target:** LangGraph agent with 5 nodes

### Tasks

- [ ] Create `apps/ai/src/agents/chief_of_staff.py`
  - [ ] LangGraph nodes:
    - CollectSignals (pull agent outputs from PostgreSQL + Qdrant)
    - Prioritize (rank by urgency × impact)
    - ComposeBriefing (LLM: 3–5 bullets, plain English)
    - ComposeInvestorDraft (monthly, revenue + burn + runway)
    - EmitActions (Telegram briefing + investor draft)
  - [ ] Rules: max 5 items, 1 positive if exists, no jargon
- [ ] Create `apps/ai/tests/test_chief_of_staff.py`
  - [ ] test_briefing_max_5_items
  - [ ] test_briefing_has_one_positive_item
  - [ ] test_briefing_no_banned_jargon
  - [ ] test_high_urgency_items_ranked_first
  - [ ] test_investor_draft_contains_revenue_burn_runway
  - [ ] test_empty_week_briefing_graceful
- [ ] Run tests: `uv run pytest tests/test_chief_of_staff.py -v` → expect 6 PASS

**Exit Criteria:**
- 5 LangGraph nodes implemented
- Max 5 items enforced
- Jargon-free output
- 6 tests passing

---

## Phase 11 🔲 — Telegram Handler (Commit 11)

**Target:** Outbound messages + callback handling

### Tasks

- [ ] Create `apps/core/internal/api/telegram.go`
  - [ ] Outbound: POST to Telegram Bot API with inline keyboard buttons
  - [ ] Inbound: POST /webhooks/telegram/callback
    - Parse callback_query.data
    - Update hitl_actions table
    - Emit downstream action (PAYMENT_INSTRUCTION, etc.)
- [ ] Create `apps/core/internal/api/telegram_test.go`
  - [ ] TestTelegram_MessageSent
  - [ ] TestTelegram_CallbackParsed
  - [ ] TestTelegram_HITLActionsRowWritten
  - [ ] TestTelegram_DownstreamActionEmitted
- [ ] Run tests: `go test ./internal/api -run TestTelegram -v` → expect 4 PASS

**Exit Criteria:**
- Outbound messages working
- Callback handling working
- 4 tests passing

---

## Phase 12 🔲 — E2E Suite + Test Runner (Commit 12)

**Target:** 5 E2E tests + test runner script

### Tasks

- [ ] Create `apps/ai/tests/test_e2e_sarthi.py`
  - [ ] test_finance_anomaly_full_flow
  - [ ] test_weekly_revenue_briefing
  - [ ] test_onboarding_sequence_with_nag
  - [ ] test_cs_churn_alert
  - [ ] test_investor_update_draft
- [ ] Update `scripts/test_sarthi.sh`
  - [ ] Step 1: Docker health check
  - [ ] Step 2: Azure LLM smoke test
  - [ ] Step 3: Unit tests (all agents)
  - [ ] Step 4: Go tests
  - [ ] Step 5: E2E tests
- [ ] Run: `bash scripts/test_sarthi.sh` → expect ALL PASS
- [ ] Tag: `git tag v1.0.0-alpha`

**Exit Criteria:**
- 5 E2E tests passing
- Test runner working
- v1.0.0-alpha tagged

---

## Test Count Summary

| Phase | Target | Cumulative | Status |
|-------|--------|------------|--------|
| Phase 0 | Baseline | 255 | ✅ COMPLETE |
| Phase 1 | 2 tests | 257 | 🔲 Pending |
| Phase 2 | 4 tests | 261 | 🔲 Pending |
| Phase 3 | 2 tests | 263 | 🔲 Pending |
| Phase 4 | 20 tests | 283 | 🔲 Pending |
| Phase 5 | 3 tests | 286 | 🔲 Pending |
| Phase 6 | 6 tests | 292 | 🔲 Pending |
| Phase 7 | 6 tests | 298 | 🔲 Pending |
| Phase 8 | 6 tests | 304 | 🔲 Pending |
| Phase 9 | 6 tests | 310 | 🔲 Pending |
| Phase 10 | 6 tests | 316 | 🔲 Pending |
| Phase 11 | 4 tests | 320 | 🔲 Pending |
| Phase 12 | 5 tests | 325 | 🔲 Pending |

**Target:** 325+ tests passing for v1.0.0-alpha  
**Full Target:** 429+ tests (including LLM evals) for v1.0.0

---

## Definition of Done (v1.0.0)

```
REQUIRED BEFORE TAGGING v1.0.0:

  ✅ Migration applied cleanly, all 9 tables created
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

---

## Current Status

**Phase:** 0 (COMPLETE ✅)

**Next:** Phase 1 — Database Migration

**Target:** 9 tables, 2 tests

---

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Status:** Phase 0 COMPLETE — Ready for Phase 1
