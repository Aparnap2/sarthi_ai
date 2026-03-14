# Sarthi v4.3 — SOP Runtime Implementation
## TODO List & Execution Plan

**Version:** 4.3.0  
**Date:** March 2026  
**Status:** Phase 0 COMPLETE ✅

---

## Current State (v4.2.0-alpha)

**What's Already Built:**
- ✅ 13 virtual employees across 6 desks
- ✅ 255+ tests passing
- ✅ LLM factory with thread safety
- ✅ 5 ops tables (finance_ops, people_ops, legal_ops, it_assets, admin_events)
- ✅ Chief of Staff routing (internal-ops only)
- ✅ Go Temporal workflows wired
- ✅ 6/6 E2E flows green
- ✅ 15/15 DSPy evals green
- ✅ Production hardening complete

**What's Missing:**
- ❌ Canonical event envelope
- ❌ Event dictionary (48 events mapped to SOPs)
- ❌ raw_events persistence pattern
- ❌ Temporal child workflow pattern (parent router + child SOPs)
- ❌ SOP registry with base class
- ❌ Connector backfill/polling logic

---

## PHASE 0 ✅ — Baseline Verification (COMPLETE)

**Target:** Tag v4.2-baseline before SOP runtime work

### Completed Tasks

- [x] Run `docker compose up -d` — all containers healthy
- [x] Run `bash scripts/test_sarthi.sh` — all 255+ tests pass
- [x] Confirm Azure LLM reachable
- [x] Git tag: `v4.2.0-alpha` tagged

**Exit Criteria:** ✅ MET

---

## PHASE 1 🔲 — Canonical Event Envelope

**Target:** Every event has exactly one envelope shape

### Tasks

- [ ] Create `apps/ai/src/schemas/event_envelope.py`
  - [ ] EventSource enum (8 sources)
  - [ ] EventEnvelope Pydantic model
  - [ ] Validators (event_name not empty, payload_ref is reference)
- [ ] Create `apps/core/internal/events/envelope.go`
  - [ ] EventSource type
  - [ ] EventEnvelope struct
- [ ] Create `apps/ai/tests/test_event_envelope.py`
  - [ ] test_valid_razorpay_envelope_passes
  - [ ] test_unknown_event_name_raises
  - [ ] test_payload_ref_never_contains_raw_json
- [ ] Run tests: `uv run pytest tests/test_event_envelope.py -v` → expect PASS

**Exit Criteria:**
- Envelope schema defined in Python + Go
- 3+ tests passing
- payload_ref validation working

---

## PHASE 2 🔲 — Event Dictionary

**Target:** One event → one topic → one SOP. Enforced in code.

### Tasks

- [ ] Create `apps/ai/src/config/event_dictionary.py`
  - [ ] DictionaryEntry dataclass
  - [ ] UnknownEventError exception
  - [ ] _REGISTRY with 48 events
  - [ ] EventDictionary class with resolve() method
- [ ] Create `apps/core/internal/events/dictionary.go`
  - [ ] DictionaryEntry struct
  - [ ] registry slice
  - [ ] Resolve() function
- [ ] Create `apps/ai/tests/test_event_dictionary.py`
  - [ ] test_razorpay_payment_captured_maps_correctly
  - [ ] test_zoho_invoice_created_maps_correctly
  - [ ] test_cron_weekly_briefing_maps_correctly
  - [ ] test_unknown_event_raises
  - [ ] test_every_sop_has_exactly_one_mapping
- [ ] Run tests: `uv run pytest tests/test_event_dictionary.py -v` → expect PASS

**Exit Criteria:**
- 48 events mapped in Python + Go
- 5+ tests passing
- Unknown events raise errors

---

## PHASE 3 🔲 — Database Migrations

**Target:** Append-only SOP runtime tables

### Tasks

- [ ] Create `apps/core/internal/db/migrations/009_sarthi_sop_runtime.sql`
  - [ ] raw_events table (event archive)
  - [ ] sop_jobs table (SOP execution tracking)
  - [ ] connector_states table (OAuth tokens, cursors)
  - [ ] dead_letter_events table (failed events)
  - [ ] transactions table (normalized ledger)
  - [ ] accounts_payable table
  - [ ] compliance_calendar table
  - [ ] sop_findings table (typed SOP results)
  - [ ] 12+ indexes
- [ ] Create `apps/core/internal/db/raw_events_test.go`
  - [ ] TestRawEventInsertAndFetch
- [ ] Apply migration: `psql $DATABASE_URL -f migrations/009_sarthi_sop_runtime.sql`
- [ ] Run tests: `go test ./internal/db -run TestRawEvent -v` → expect PASS

**Exit Criteria:**
- 9 new tables created
- 12+ indexes created
- Go tests passing

---

## PHASE 4 🔲 — Go Webhook Handlers

**Target:** Validate → persist raw event → publish envelope. Nothing else.

### Tasks

- [ ] Update `apps/core/internal/api/razorpay.go`
  - [ ] HMAC-SHA256 verification
  - [ ] Event dictionary resolution
  - [ ] raw_events persistence
  - [ ] Envelope publishing to Redpanda
  - [ ] DLQ for unknown events
- [ ] Update `apps/core/internal/api/telegram.go`
  - [ ] File persistence pattern
  - [ ] Intent classification routing
- [ ] Create `apps/core/internal/api/razorpay_test.go`
  - [ ] TestRazorpaySignatureValid
  - [ ] TestRazorpaySignatureInvalid
  - [ ] TestRazorpayUnknownEventSentToDLQ
  - [ ] TestRazorpayPaymentCapturedPublishesToRedpanda
- [ ] Run tests: `go test ./internal/api -run TestRazorpay -v` → expect PASS

**Exit Criteria:**
- Razorpay webhook validated, persisted, routed
- Telegram file uploads persisted
- 4+ Go tests passing

---

## PHASE 5 🔲 — Temporal Workflow Redesign

**Target:** Parent = pure router. Children = SOP executors. Pass refs not payloads.

### Tasks

- [ ] Create `apps/core/internal/workflow/business_os_workflow.go`
  - [ ] BusinessOSState struct
  - [ ] Continue-As-New at 5000 events
  - [ ] Idempotency check (SeenKeys map)
  - [ ] Child workflow spawning
- [ ] Create `apps/core/internal/workflow/cron_workflows.go`
  - [ ] WeeklyBriefingCron
  - [ ] ComplianceCheckCron
  - [ ] CloudCostCron
  - [ ] All 9 cron jobs from event dictionary
- [ ] Create `apps/core/internal/workflow/sop_router_test.go`
  - [ ] TestSOPRouterSpawnsCorrectChildWorkflow
  - [ ] TestContinueAsNewTriggersBeforeLimit
  - [ ] TestDuplicateEnvelopeShortCircuits
- [ ] Run tests: `go test ./internal/workflow -v` → expect PASS

**Exit Criteria:**
- Parent workflow spawns children (doesn't execute SOPs)
- Continue-As-New fires at 5000 events
- Idempotency working
- 3+ Go tests passing

---

## PHASE 6 🔲 — Python SOP Registry

**Target:** SOP registry with base class + execute pattern

### Tasks

- [ ] Create `apps/ai/src/sops/base.py`
  - [ ] SOPResult Pydantic model
  - [ ] BaseSOP abstract base class
  - [ ] fetch_payload() helper
- [ ] Create `apps/ai/src/sops/registry.py`
  - [ ] _REGISTRY dict
  - [ ] register() function
  - [ ] SOPRegistry class
  - [ ] Auto-import all SOPs
- [ ] Create `apps/ai/tests/test_sop_registry.py`
  - [ ] test_all_dictionary_sops_have_registered_executor
  - [ ] test_registry_returns_correct_executor_class
- [ ] Run tests: `uv run pytest tests/test_sop_registry.py -v` → expect PASS

**Exit Criteria:**
- BaseSOP class defined
- SOPRegistry working
- 2+ tests passing

---

## PHASE 7 🔲 — Three Priority SOPs

**Target:** Implement SOP_REVENUE_RECEIVED, SOP_BANK_STATEMENT_INGEST, SOP_WEEKLY_BRIEFING

### SOP 1: Revenue Received

- [ ] Create `apps/ai/src/sops/revenue_received.py`
  - [ ] RevenueReceivedSOP class
  - [ ] execute() method
  - [ ] MRR milestone check
  - [ ] Concentration risk check
  - [ ] register() call
- [ ] Create `apps/ai/tests/test_sop_revenue_received.py`
  - [ ] test_normal_payment_logs_silently
  - [ ] test_mrr_milestone_fires_positive_trigger
  - [ ] test_concentration_risk_fires_when_customer_exceeds_30_pct
- [ ] Run tests: `uv run pytest tests/test_sop_revenue_received.py -v` → expect PASS

### SOP 2: Bank Statement Ingest

- [ ] Create `apps/ai/src/sops/bank_statement_ingest.py`
  - [ ] BankStatementIngestSOP class
  - [ ] execute() method with Docling/pdfplumber routing
  - [ ] Deduplication logic
  - [ ] Category confidence flagging
  - [ ] Runway check
  - [ ] register() call
- [ ] Create `apps/ai/tests/test_sop_bank_statement_ingest.py`
  - [ ] test_hdfc_csv_ingested_correctly
  - [ ] test_duplicate_transactions_skipped
  - [ ] test_low_confidence_transaction_flagged
  - [ ] test_runway_below_90_days_fires_alert
  - [ ] test_telegram_message_contains_no_jargon
- [ ] Run tests: `uv run pytest tests/test_sop_bank_statement_ingest.py -v` → expect PASS

### SOP 3: Weekly Briefing

- [ ] Create `apps/ai/src/sops/weekly_briefing.py`
  - [ ] WeeklyBriefingSOP class
  - [ ] execute() method
  - [ ] Max 5 items enforcement
  - [ ] Positive item inclusion
  - [ ] ToneFilter jargon validation
  - [ ] register() call
- [ ] Create `apps/ai/tests/test_sop_weekly_briefing.py`
  - [ ] test_briefing_contains_max_5_items
  - [ ] test_briefing_always_includes_at_least_one_positive_if_exists
  - [ ] test_briefing_output_is_jargon_free
  - [ ] test_briefing_uses_real_azure_llm_not_mock
- [ ] Run tests: `uv run pytest tests/test_sop_weekly_briefing.py -v` → expect PASS

**Exit Criteria:**
- 3 SOPs implemented
- 12+ tests passing
- All SOPs jargon-free
- All SOPs use real Azure LLM

---

## PHASE 8 🔲 — Full E2E Tests

**Target:** 6/6 E2E SOP flows green

### Tasks

- [ ] Create `apps/ai/tests/test_e2e_sop_flows.py`
  - [ ] TestE2ERevenueReceived
    - [ ] test_razorpay_payment_captured_full_flow
  - [ ] TestE2EBankStatementIngest
    - [ ] test_telegram_hdfc_pdf_full_flow
  - [ ] TestE2EWeeklyBriefing
    - [ ] test_weekly_briefing_cron_fires_and_produces_message
- [ ] Update `scripts/test_sarthi.sh`
  - [ ] Add E2E test execution
- [ ] Run tests: `uv run pytest tests/test_e2e_sop_flows.py -v --timeout=120` → expect PASS

**Exit Criteria:**
- 6/6 E2E flows green
- Full suite runs in <10 minutes

---

## PHASE 9 🔲 — Connector Layer

**Target:** Razorpay backfill, Zoho polling, Google Workspace polling

### Tasks

- [ ] Create `apps/core/internal/connectors/razorpay/backfill.go`
  - [ ] Fetch last 90 days via Razorpay API
  - [ ] Convert to envelopes
  - [ ] Push to Redpanda with idempotency
- [ ] Create `apps/core/internal/connectors/zoho_books/poller.go`
  - [ ] Temporal scheduled workflow (every 15min)
  - [ ] Fetch modified invoices
  - [ ] Normalize to envelopes
- [ ] Create `apps/core/internal/connectors/google_workspace/poller.go`
  - [ ] Calendar push + polling fallback
  - [ ] Drive /contracts/ polling
  - [ ] Directory polling
- [ ] Run tests: `go test ./internal/connectors/... -v` → expect PASS

**Exit Criteria:**
- Razorpay backfill working
- Zoho polling working
- Google Workspace polling working

---

## PHASE 10 🔲 — Update Test Runner

**Target:** `scripts/test_sarthi.sh` includes all Phases 1-9 tests

### Tasks

- [ ] Update `scripts/test_sarthi.sh`
  - [ ] Phase 1-2: Event envelope + dictionary tests
  - [ ] Phase 3: DB migration tests
  - [ ] Phase 4: Go webhook tests
  - [ ] Phase 5: Temporal workflow tests
  - [ ] Phase 6: SOP registry tests
  - [ ] Phase 7: SOP unit tests
  - [ ] Phase 8: E2E flow tests
  - [ ] Phase 9: Connector tests
- [ ] Run: `bash scripts/test_sarthi.sh` → expect ALL GREEN

**Exit Criteria:**
- All tests run in sequence
- All tests pass

---

## Test Count Summary

| Phase | Target | Cumulative | Status |
|-------|--------|------------|--------|
| Phase 0 | Baseline | 255+ | ✅ COMPLETE |
| Phase 1 | 3 tests | 258 | 🔲 Pending |
| Phase 2 | 5 tests | 263 | 🔲 Pending |
| Phase 3 | 1 test | 264 | 🔲 Pending |
| Phase 4 | 4 tests | 268 | 🔲 Pending |
| Phase 5 | 3 tests | 271 | 🔲 Pending |
| Phase 6 | 2 tests | 273 | 🔲 Pending |
| Phase 7 | 12 tests | 285 | 🔲 Pending |
| Phase 8 | 6 tests | 291 | 🔲 Pending |
| Phase 9 | 3 tests | 294 | 🔲 Pending |
| Phase 10 | Script update | 294 | 🔲 Pending |

**Target:** 300+ tests passing for v4.3.0

---

## Definition of Done (v4.3.0)

This implementation is complete only when **all** of the following are true:

```
✅ Migration 009 applied — all 9 new tables exist
✅ Event Dictionary covers all 48 events from design doc
✅ Razorpay payment.captured webhook verified, persisted, routed
✅ Telegram PDF bank statement classified and routed
✅ BusinessOSWorkflow spawns child workflows (not executes SOPs itself)
✅ Continue-As-New fires at 5000 events (not at Temporal's hard limit)
✅ Payloads passed by ref (raw_events:uuid), never inline in Temporal state
✅ SOP_REVENUE_RECEIVED passes all unit + E2E tests
✅ SOP_BANK_STATEMENT_INGEST deduplicates correctly
✅ SOP_WEEKLY_BRIEFING produces max 5 items, jargon-free
✅ All SOP outputs pass ToneFilter jargon validator
✅ Langfuse traces every SOP execution
✅ All tests use real Docker, real Azure LLM, zero mocks
✅ bash scripts/test_sarthi.sh → all green
```

```
DO NOT MARK COMPLETE IF:
✗ Any test uses pytest-mock on Docker infrastructure
✗ Any Temporal workflow passes raw JSON in signals
✗ Any founder-facing string contains banned jargon
✗ E2E test does not actually trigger a Temporal child workflow
```

---

## Current Status

**Phase:** 0 (COMPLETE ✅)

**Next:** Phase 1 — Canonical Event Envelope

**Target:** 3 tests passing

---

**Document Version:** 4.3  
**Last Updated:** March 2026  
**Status:** Phase 0 COMPLETE — Ready for Phase 1
