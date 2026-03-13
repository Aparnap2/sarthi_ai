# Sarthi v4.2 — Internal Ops Virtual Office
## TODO List & Execution Plan

**Version:** 4.2.0-alpha  
**Date:** March 2026  
**Status:** Phase 1 COMPLETE ✅

---

## Phase 1 ✅ — LLM Factory & Config (COMPLETE)

**Target:** 125 tests passing  
**Status:** ✅ COMPLETE — 164 tests passing

### Completed Tasks

- [x] Create `apps/ai/src/config/llm.py` — AzureOpenAI factory
- [x] Create `apps/ai/src/config/llm_guard.py` — Import guard enforcement
- [x] Refactor all `AzureOpenAI()` calls → `get_llm_client()`
- [x] Add `tests/test_llm_connectivity.py` — 4/4 tests passing
- [x] Update `.env.example` with v4.2 LLM vars
- [x] Verify: Zero `AzureOpenAI(` in agent code

**Test Results:**
- LLM connectivity: 4/4 ✅
- Agent tests: 36/37 ✅ (97% pass rate)
- Full suite: 164 passed, 37 failed (pre-existing), 38 skipped

**Exit Criteria:** ✅ MET

---

## Phase 2 🔲 — Data Model Extensions

**Target:** 130 tests passing

### Tasks

- [ ] Create migration `008_sarthi_internal_ops.sql`
  - [ ] Table: `finance_ops` (AR/AP, payroll events)
  - [ ] Table: `people_ops` (onboarding, leave, appraisals)
  - [ ] Table: `legal_ops` (documents, eSign, expiry)
  - [ ] Table: `it_assets` (SaaS subscriptions, cloud spend)
  - [ ] Table: `admin_events` (meetings, action items, SOPs)
- [ ] Add Go unit tests for new tables
  - [ ] `apps/core/internal/db/internal_ops_test.go`
- [ ] Run: `cd apps/core && go test ./... -run TestInternalOps -v`

**Exit Criteria:**
- All 5 tables created
- Go tests passing (10+ tests)
- 130 tests total passing

---

## Phase 3 🔲 — Agent Layer: 6 Desks

**Target:** 150 tests passing

### Finance Desk

- [ ] Reuse/extend `CFOAgent` + `FinanceOpsAgent`
- [ ] Add methods: Bookkeeper, AR/AP Clerk, Payroll Clerk
- [ ] Pydantic contracts: `FinanceTask`, `FinanceTaskResult`
- [ ] Tests: `tests/test_finance_desk.py` (15 tests)

### People Desk

- [ ] Implement `HROpsAgent` (onboarding, leave, appraisals)
- [ ] Implement `InternalRecruiterAgent` (JD drafting, interview scheduling)
- [ ] Pydantic contracts: `PeopleOpsFinding`
- [ ] Tests: `tests/test_people_desk.py` (15 tests)

### Legal Desk

- [ ] Extend `LegalOpsAgent` (contracts, compliance)
- [ ] Add contract lifecycle tracking
- [ ] Pydantic contracts: `LegalOpsResult`
- [ ] Tests: `tests/test_legal_desk.py` (10 tests)

### Intelligence Desk

- [ ] Refine `BIAgent` (internal-only: unit economics, churn)
- [ ] Implement `PolicyWatcherAgent` (tax/grant/compliance changes)
- [ ] Pydantic contracts: `IntelligenceFinding`
- [ ] Tests: `tests/test_intelligence_desk.py` (15 tests)

### IT & Tools Desk

- [ ] Implement `ITAdminAgent` (SaaS audits, cloud spend alerts)
- [ ] Pydantic contracts: `ITRiskAlert`
- [ ] Tests: `tests/test_it_desk.py` (10 tests)

### Admin Desk

- [ ] Implement `EAAgent` (meeting prep, action extraction)
- [ ] Implement `KnowledgeManagerAgent` (SOP generation, Neo4j episodes)
- [ ] Pydantic contracts: `KnowledgeManagerResult`
- [ ] Tests: `tests/test_admin_desk.py` (15 tests)

### Schema Updates

- [ ] Create `apps/ai/src/schemas/ops_results.py`
  - [ ] `FinanceTask`, `FinanceTaskResult`
  - [ ] `PeopleOpsFinding`
  - [ ] `LegalOpsResult`
  - [ ] `IntelligenceFinding`
  - [ ] `ITRiskAlert`
  - [ ] `KnowledgeManagerResult`

**Exit Criteria:**
- All 6 desks implemented
- 80+ new agent tests passing
- 150 tests total passing

---

## Phase 4 🔲 — Chief of Staff Routing (Internal-Ops Only)

**Target:** 160 tests passing

### Tasks

- [ ] Update `chief_of_staff_agent.py`:
  - [ ] Remove external routing (RevOps/GTM/Market Intel)
  - [ ] Add routing rules:
    - Bank/Accounting → Finance Desk
    - HR events → People Desk
    - Contract uploads → Legal Desk
    - Subscription/IT events → IT Desk
    - Meeting notes → Admin Desk
- [ ] Add tests: `tests/test_chief_of_staff_routing_internal_only.py`
  - [ ] Test: `bank_statement_upload` → Finance Desk only
  - [ ] Test: `new_hire_joined` → People Desk only
  - [ ] Test: `contract_uploaded` → Legal Desk only
  - [ ] Test: `meeting_transcript` → Admin Desk only
- [ ] Verify: Zero references to RevOps/GTM in CoS code

**Exit Criteria:**
- CoS routes to internal desks only
- 10+ routing tests passing
- 160 tests total passing

---

## Phase 5 🔲 — Go Workflow Wiring

**Target:** 170 tests passing

### Tasks

- [ ] Update `apps/core/internal/workflow/business_os_workflow.go`:
  - [ ] Add event handlers for each desk
  - [ ] Preserve HITL gate classification (LOW/MEDIUM/HIGH)
- [ ] Extend `activities.go`:
  - [ ] `ProcessFinanceOps` (gRPC call to Python)
  - [ ] `ProcessPeopleOps`
  - [ ] `ProcessLegalOps`
  - [ ] `ProcessIntelligenceOps`
  - [ ] `ProcessITOps`
  - [ ] `ProcessAdminOps`
- [ ] Add Temporal workflow tests:
  - [ ] `workflow_internal_ops_test.go`
  - [ ] Test: `bank_statement_upload` → correct activities invoked
  - [ ] Test: `new_hire_joined` → correct activities invoked
- [ ] Persist results to new DB tables (Phase 2)

**Exit Criteria:**
- All 6 desks wired into Temporal workflow
- HITL gates preserved
- 10+ Go workflow tests passing
- 170 tests total passing

---

## Phase 6 🔲 — E2E Tests

**Target:** 20/20 E2E green

### Tasks

- [ ] Create `apps/ai/tests/test_e2e_internal_ops.py`:
  - [ ] Flow 1: Bank CSV → Finance Desk → CFOFinding → Telegram message
  - [ ] Flow 2: New hire → People Desk → tasks created → weekly briefing
- [ ] Extend `scripts/test_sarthi.sh`:
  - [ ] Add E2E test execution
  - [ ] Maintain sequence: infra → Azure → Python → Go
- [ ] Run full suite: `bash scripts/test_sarthi.sh`

**Exit Criteria:**
- 20/20 E2E flows green
- Full suite runs in <10 minutes

---

## Phase 7 🔲 — Production Hardening

**Target:** ≥13/15 LLM evals green

### Tasks

- [ ] DSPy eval suite (15 evals):
  - [ ] ToneFilter fidelity (jargon-free)
  - [ ] Action specificity (single action, not list)
  - [ ] Desk routing accuracy
  - [ ] HITL classification accuracy
- [ ] Circuit breaker (all external calls):
  - [ ] Azure OpenAI
  - [ ] Telegram API
  - [ ] gRPC calls
- [ ] Rate limiter:
  - [ ] Telegram (5 req/s)
  - [ ] Azure OpenAI (per deployment limits)
- [ ] GitHub Actions CI:
  - [ ] `.github/workflows/ci.yml` (unit + lint, no LLM)
  - [ ] `.github/workflows/e2e.yml` (manual trigger, full stack)
- [ ] Langfuse tracing:
  - [ ] All agent calls traced
  - [ ] p95 latency < 8s

**Exit Criteria:**
- ≥13/15 LLM evals passing
- Circuit breaker active
- CI/CD pipelines green
- v4.2.0-alpha tagged

---

## Phase 8 🔲 — v4.2.0 REAL MILESTONE

**Target:** One real founder using internal ops features

### Tasks

- [ ] One real founder signs up via Telegram
- [ ] Completes onboarding (6 questions, <10 minutes)
- [ ] Uploads first bank statement
- [ ] Receives first CFO finding (no jargon, ₹ amounts)
- [ ] Approves one action via Telegram inline keyboard
- [ ] Reports: "This saved me admin time"
- [ ] Tag: `git tag -a v4.2.0 -m "Sarthi v4.2.0 — Internal Ops Virtual Office"`

**THAT is v4.2.0. Not before.**

---

## Test Count Summary

| Phase | Target | Cumulative | Status |
|-------|--------|------------|--------|
| Phase 1 | 125 tests | 164 passed | ✅ COMPLETE |
| Phase 2 | 130 tests | 130 | 🔲 Pending |
| Phase 3 | 150 tests | 150 | 🔲 Pending |
| Phase 4 | 160 tests | 160 | 🔲 Pending |
| Phase 5 | 170 tests | 170 | 🔲 Pending |
| Phase 6 | 20 E2E | 20/20 | 🔲 Pending |
| Phase 7 | ≥13/15 evals | ≥13/15 | 🔲 Pending |
| Phase 8 | 1 real founder | 1 | 🔲 Pending |

---

## Current Status

**Phase:** 1 (COMPLETE ✅)

**Completed:**
- ✅ LLM factory (`get_llm_client()`)
- ✅ Import guard (`llm_guard.py`)
- ✅ Zero `AzureOpenAI(` in agent code
- ✅ 164 tests passing (4 new LLM connectivity tests)
- ✅ `.env` updated with v4.2 vars

**Next:**
- Phase 2: Data model extensions (5 new tables)
- Target: 130 tests passing

---

## Key v4.2 Changes (v4.1 → v4.2)

| Aspect | v4.1 | v4.2 |
|--------|------|------|
| **Definition** | Full-service AI back-office | Internal Ops Virtual Office Only |
| **Agents** | 17 vertical agents | 13 virtual employees |
| **Structure** | 4 Tiers | 6 Desks |
| **External-facing** | ✅ RevOps, Market Intel, Grants | ❌ None |
| **Test target** | 151+ tests | ~170 tests |
| **Value prop** | "AI back-office" | "We don't find customers. We prevent collapse." |
| **ROI** | Not quantified | 20x–50x (₹3.5L–₹7.5L → ₹5K–₹15K) |

---

**Document Version:** 4.2  
**Last Updated:** March 2026  
**Status:** Phase 1 COMPLETE ✅ — Ready for Phase 2
