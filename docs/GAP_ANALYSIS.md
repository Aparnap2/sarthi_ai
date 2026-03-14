# Sarthi SOP Runtime — Gap Analysis
## Current State (v4.2.0-alpha) vs Target State (AGENT_INSTRUCTION.md)

**Date:** March 2026  
**Version:** 1.0

---

## Executive Summary

**Current State:** v4.2.0-alpha with 13 virtual employees across 6 desks, 255+ tests passing.

**Target State:** Full SOP runtime with event-driven architecture, canonical event envelopes, and Temporal child workflow pattern.

**Gap:** The current implementation uses **agent-centric** architecture (desks route to agents). The target design uses **SOP-centric** architecture (events route to SOP workflows). Both are valid — this document maps what needs to change.

---

## Architecture Comparison

| Aspect | Current (v4.2.0-alpha) | Target (AGENT_INSTRUCTION.md) | Change Required |
|--------|------------------------|-------------------------------|-----------------|
| **Routing** | Chief of Staff → Desk → Agent | Event Dictionary → SOP → Child Workflow | **MEDIUM** — Add event dictionary layer |
| **Event Shape** | Ad-hoc per agent | Canonical EventEnvelope | **MEDIUM** — Add envelope schema |
| **Payload Passing** | In-memory objects | PostgreSQL refs (`raw_events:uuid`) | **HIGH** — Redesign Temporal signals |
| **Temporal Pattern** | Single workflow per event | Parent router + child SOP workflows | **HIGH** — Refactor workflows |
| **Database** | 5 ops tables + findings | 9 tables (raw_events, sop_jobs, connector_states, DLQ, etc.) | **MEDIUM** — Add migration 009 |
| **Webhooks** | Go handlers → Python agents | Go handlers → Redpanda → Temporal | **LOW** — Already similar |
| **Tests** | 255+ passing | 300+ with E2E SOP flows | **LOW** — Add E2E tests |

---

## Phase-by-Phase Gap Analysis

### Phase 0 — Baseline Verification

**Current:** ✅ Already done (v4.2.0-alpha tagged)

**Action:** Run `git tag v4.2-baseline` before starting SOP runtime work.

---

### Phase 1 — Canonical Event Envelope

**Current:** ❌ No canonical envelope

**Target:** `EventEnvelope` Pydantic model + Go struct with payload_ref pattern

**Files to Create:**
- `apps/ai/src/schemas/event_envelope.py`
- `apps/core/internal/events/envelope.go`
- `apps/ai/tests/test_event_envelope.py`

**Effort:** 4 hours

---

### Phase 2 — Event Dictionary

**Current:** ✅ Chief of Staff routing logic exists

**Target:** Explicit `EventDictionary` with 48 events mapped to SOPs

**Files to Create:**
- `apps/ai/src/config/event_dictionary.py`
- `apps/core/internal/events/dictionary.go`
- `apps/ai/tests/test_event_dictionary.py`

**Overlap:** Current CoS routing can be migrated to dictionary pattern.

**Effort:** 6 hours

---

### Phase 3 — Database Migrations

**Current:** ✅ 5 ops tables exist (finance_ops, people_ops, legal_ops, it_assets, admin_events)

**Target:** 9 tables (raw_events, sop_jobs, connector_states, dead_letter_events, transactions, accounts_payable, compliance_calendar, sop_findings) + existing 5

**Files to Create:**
- `apps/core/internal/db/migrations/009_sarthi_sop_runtime.sql`
- `apps/core/internal/db/raw_events_test.go`

**Overlap:** Some tables overlap with current schema. Need to reconcile.

**Effort:** 8 hours

---

### Phase 4 — Go Webhook Handlers

**Current:** ✅ Razorpay, Telegram handlers exist

**Target:** Same handlers but with envelope + raw_events persistence pattern

**Files to Modify:**
- `apps/core/internal/api/razorpay.go` (add envelope, raw_events insert)
- `apps/core/internal/api/telegram.go` (add file persistence pattern)

**Files to Create:**
- `apps/core/internal/api/razorpay_test.go` (4 new tests)

**Effort:** 6 hours

---

### Phase 5 — Temporal Workflow Redesign

**Current:** ⚠️ Single workflow per event type

**Target:** BusinessOSWorkflow (parent router) + child SOP workflows with Continue-As-New at 5000 events

**Files to Create:**
- `apps/core/internal/workflow/business_os_workflow.go`
- `apps/core/internal/workflow/cron_workflows.go`
- `apps/core/internal/workflow/sop_router_test.go`

**Overlap:** Current workflows can become child SOP workflows.

**Effort:** 12 hours (highest complexity)

---

### Phase 6 — Python SOP Registry

**Current:** ✅ Agent registry exists (6 desks)

**Target:** SOP registry with base class + execute pattern

**Files to Create:**
- `apps/ai/src/sops/base.py`
- `apps/ai/src/sops/registry.py`
- `apps/ai/tests/test_sop_registry.py`

**Overlap:** Current agents can be wrapped as SOPs.

**Effort:** 6 hours

---

### Phase 7 — Three Priority SOPs

**Current:** ⚠️ Partial (CFO agent exists, bank parser exists)

**Target:** SOP_REVENUE_RECEIVED, SOP_BANK_STATEMENT_INGEST, SOP_WEEKLY_BRIEFING with full E2E tests

**Files to Create:**
- `apps/ai/src/sops/revenue_received.py`
- `apps/ai/src/sops/bank_statement_ingest.py`
- `apps/ai/src/sops/weekly_briefing.py`
- Test files for each

**Overlap:** Reuse existing CFO agent logic, bank parser, weekly briefing code.

**Effort:** 16 hours

---

### Phase 8 — Full E2E Tests

**Current:** ✅ 6 E2E flows exist

**Target:** Same flows but with SOP runtime pattern

**Files to Modify:**
- `apps/ai/tests/test_e2e_internal_ops.py` (update to use SOP pattern)

**Effort:** 4 hours

---

### Phase 9 — Connector Layer

**Current:** ❌ No connector backfill/polling logic

**Target:** Razorpay backfill, Zoho polling, Google Workspace polling

**Files to Create:**
- `apps/core/internal/connectors/razorpay/backfill.go`
- `apps/core/internal/connectors/zoho_books/poller.go`
- `apps/core/internal/connectors/google_workspace/poller.go`

**Effort:** 12 hours

---

### Phase 10 — Update Test Runner

**Current:** ✅ `scripts/test_sarthi.sh` exists

**Target:** Same script with Phase 1-9 tests added

**Files to Modify:**
- `scripts/test_sarthi.sh` (add Phase 1-6 test execution)

**Effort:** 2 hours

---

## Implementation Strategy

### Option A: Big Bang Rewrite (NOT RECOMMENDED)
- Stop all work on v4.2.0-alpha
- Implement all 10 phases sequentially
- Tag v4.3.0 when complete

**Risk:** 2-3 weeks of no shippable releases.

### Option B: Incremental Migration (RECOMMENDED)
- Keep v4.2.0-alpha production-ready
- Implement SOP runtime in parallel branch
- Migrate one SOP at a time (Revenue → Bank Statement → Weekly Briefing)
- Tag v4.3.0-alpha after Phase 5, v4.3.0 after Phase 7

**Benefit:** Continuous shippable releases.

---

## Recommended Next Steps

1. **Create `feature/sop-runtime` branch** from v4.2.0-alpha tag
2. **Implement Phases 1-3** (Event Envelope, Dictionary, Migrations) — 18 hours
3. **Tag v4.3.0-alpha** with SOP runtime foundation
4. **Implement Phases 4-6** (Webhooks, Temporal, SOP Registry) — 24 hours
5. **Implement Phase 7** (3 priority SOPs) — 16 hours
6. **Tag v4.3.0** with full SOP runtime
7. **Implement Phases 8-10** (E2E, Connectors, Test Runner) — 18 hours
8. **Tag v4.3.1** with production hardening

**Total Effort:** 76 hours (~2 weeks full-time)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-12 | Incremental migration over big bang | Maintain production releases while building SOP runtime |
| 2026-03-12 | Reuse existing 6 desks architecture | SOP runtime complements desk architecture, doesn't replace it |
| 2026-03-12 | Migration 009 instead of modifying 008 | Append-only principle — never modify existing migrations |

---

## Open Questions

1. **Should raw_events replace existing ops tables?**
   - **Recommendation:** No — keep both. raw_events for audit trail, ops tables for structured queries.

2. **Should Continue-As-New threshold be 5000 or 10000?**
   - **Recommendation:** 5000 (conservative, well below Temporal's 51,200 hard limit).

3. **Should Telegram file uploads go to disk or S3?**
   - **Recommendation:** Disk for dev, S3 for prod. Abstract behind `FileStorage` interface.

---

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Status:** Ready for implementation
