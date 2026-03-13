# Sarthi v4.2 TODO List

**Version:** 4.2
**Date:** March 2026
**Pivot:** Internal Ops Virtual Office Only

---

## PHASE 1 (IN PROGRESS): LLM Factory & Config

**Target:** 125 tests passing

- [ ] Create `apps/ai/src/config/llm.py` (AzureOpenAI factory)
- [ ] Refactor all `AzureOpenAI()` calls to use factory
- [ ] Add `tests/test_llm_connectivity.py`
- [ ] `apps/ai/src/config/langfuse.py` — observability setup
- [ ] Grep-replace `AzureOpenAI` everywhere → `get_llm_client()`
- [ ] `graph_memory_agent.py` → use `OpenAIClient` (not `AzureOpenAIClient`)
- [ ] `docker-compose.yml`: append neo4j + langfuse + sandbox services
- [ ] `make up` → `make health` → all 12 containers green
- [ ] Migration 007 applied (Neo4j + Graphiti schema)
- [ ] `make test-unit` → 125 green
- [ ] `git tag v4.2.0-alpha`

---

## PHASE 2: Data Model Extensions

**Target:** 130 tests passing

- [ ] Create migration `008_sarthi_internal_ops.sql`
- [ ] Tables: `finance_ops`, `people_ops`, `legal_ops`, `it_assets`, `admin_events`
- [ ] Add Go unit tests for new tables
- [ ] Update sqlc queries for internal ops schema
- [ ] `apps/core/internal/database/` — connection utilities updated
- [ ] `make test-go` → Go tests passing
- [ ] `make test-unit` → 130 green

---

## PHASE 3: Agent Layer — 6 Desks

**Target:** 150 tests passing

### Finance Desk (4 agents)
- [ ] `apps/ai/src/agents/desks/finance/cfo_agent.py` (reuse + refine)
- [ ] `apps/ai/src/agents/desks/finance/bookkeeper_agent.py`
- [ ] `apps/ai/src/agents/desks/finance/ar_ap_clerk_agent.py`
- [ ] `apps/ai/src/agents/desks/finance/payroll_clerk_agent.py`
- [ ] `tests/test_finance_desk.py` (25 tests)

### People Desk (2 agents)
- [ ] `apps/ai/src/agents/desks/people/hr_coordinator_agent.py`
- [ ] `apps/ai/src/agents/desks/people/internal_recruiter_agent.py`
- [ ] `tests/test_people_desk.py` (12 tests)

### Legal Desk (2 agents)
- [ ] `apps/ai/src/agents/desks/legal/contracts_coordinator_agent.py` (extend LegalOpsAgent)
- [ ] `apps/ai/src/agents/desks/legal/compliance_tracker_agent.py`
- [ ] `tests/test_legal_desk.py` (12 tests)

### Intelligence Desk (2 agents)
- [ ] `apps/ai/src/agents/desks/intelligence/bi_analyst_agent.py` (internal-only)
- [ ] `apps/ai/src/agents/desks/intelligence/policy_watcher_agent.py`
- [ ] `tests/test_intelligence_desk.py` (15 tests)

### IT & Tools Desk (1 agent)
- [ ] `apps/ai/src/agents/desks/it/it_admin_agent.py`
- [ ] `tests/test_it_desk.py` (10 tests)

### Admin Desk (2 agents)
- [ ] `apps/ai/src/agents/desks/admin/ea_agent.py` (reuse EAAgent)
- [ ] `apps/ai/src/agents/desks/admin/knowledge_manager_agent.py`
- [ ] `tests/test_admin_desk.py` (12 tests)

### Pydantic Contracts
- [ ] `apps/ai/src/schemas/findings_v42.py` — all desk output contracts
- [ ] Jargon validator updated for internal ops
- [ ] HITL risk classification per desk

**Phase 3 Total:** 86 desk tests + 64 infra = 150 tests

---

## PHASE 4: Chief of Staff Routing

**Target:** 160 tests passing

- [ ] Remove external routing (RevOps/GTM/Market Intel/Grant)
- [ ] Add internal-only routing rules
- [ ] Update `chief_of_staff_agent.py` for 6-desk routing
- [ ] Update `tone_filter.py` for internal ops language
- [ ] DSPy signatures: DeskRouter, InternalToneFilter
- [ ] `tests/test_chief_of_staff_routing_internal_only.py`
- [ ] `tests/test_tone_filter_v42.py`
- [ ] `make test-unit` → 160 green

---

## PHASE 5: Go Workflow Wiring

**Target:** 170 tests passing

- [ ] Update `apps/core/internal/workflow/business_os_workflow.go` for internal-ops
- [ ] Add activities for each desk:
  - [ ] `finance_desk_activity.go`
  - [ ] `people_desk_activity.go`
  - [ ] `legal_desk_activity.go`
  - [ ] `intelligence_desk_activity.go`
  - [ ] `it_desk_activity.go`
  - [ ] `admin_desk_activity.go`
- [ ] HITL gate classification preserved (LOW/MEDIUM/HIGH)
- [ ] Update `apps/core/internal/api/telegram.go` for desk responses
- [ ] Go workflow tests: `internal/workflow/business_os_workflow_test.go`
- [ ] `make test-go` → Go tests passing
- [ ] `make test-unit` → 170 green

---

## PHASE 6: E2E Tests

**Target:** 20/20 E2E green

### Flow 1: Bank Statement → Finance Desk
- [ ] `tests/test_e2e_bank_to_finance.py`
  - Upload HDFC CSV → Telegram
  - IngestionAgent normalizes
  - BookkeeperAgent categorizes
  - CFOAgent analyzes cash position
  - ChiefOfStaff routes + ToneFilter applies
  - Founder receives: "Here's your cash position + one action"

### Flow 2: New Hire → People Desk
- [ ] `tests/test_e2e_new_hire_onboarding.py`
  - Founder: "Hiring new engineer, start date April 1"
  - ChiefOfStaff routes to People Desk
  - HRCoordinatorAgent creates onboarding checklist
  - InternalRecruiterAgent drafts offer letter
  - HITL: Founder approves offer letter via Telegram inline keyboard
  - Tasks created in PostgreSQL

### Flow 3: Contract Expiry → Legal Desk
- [ ] `tests/test_e2e_contract_renewal.py`
  - Contract expiry detected (90-day warning)
  - ContractsCoordinatorAgent flags renewal needed
  - ChiefOfStaff surfaces to founder
  - HITL: Founder confirms renewal process

### Flow 4: SaaS Audit → IT Desk
- [ ] `tests/test_e2e_saas_audit.py`
  - ITAdminAgent detects unused subscription
  - Recommends cancellation with ₹ savings
  - Founder approves via 1-tap

### Flow 5: Compliance Deadline → Legal Desk
- [ ] `tests/test_e2e_compliance_deadline.py`
  - ComplianceTrackerAgent detects GST deadline <14 days
  - Prepares filing data
  - HIGH RISK HITL: explicit confirm before filing

### Update Test Scripts
- [ ] Update `scripts/test_sarthi.sh` for v4.2
- [ ] Update `.github/workflows/e2e.yml` for internal ops
- [ ] `make test-e2e` → 20/20 green

---

## PHASE 7: Production Hardening

**Target:** ≥13/15 LLM evals green

- [ ] DSPy eval suite — 15 evals, ≥13/15 must pass
- [ ] Circuit breaker — all external calls (LLM, Telegram, integrations)
- [ ] Rate limiter — Telegram, Zoho Books, Razorpay
- [ ] `.github/workflows/ci.yml` — unit + lint (no LLM)
- [ ] `.github/workflows/e2e.yml` — manual trigger, full stack
- [ ] All Langfuse traces < 8s p95 latency
- [ ] `make test-llm` → ≥13/15 green
- [ ] `git tag v4.2.0-beta`

---

## PHASE 8: v4.2.0 REAL MILESTONE

**Target:** One real founder uses internal ops features

- [ ] One real founder signs up via Telegram
- [ ] Completes onboarding (6 questions, < 10 minutes)
- [ ] Uploads a real bank statement (any Indian bank)
- [ ] Uses at least 2 desks (Finance + one other)
- [ ] Receives a real finding (no jargon, ₹ amounts)
- [ ] Approves one action via Telegram inline keyboard
- [ ] Reports: "This saved me admin time"
- [ ] `git tag -a v4.2.0 -m "Sarthi v4.2.0 — Internal Ops Virtual Office"`

**THAT is v4.2.0. Not before.**

---

## Test Count Summary

| Phase | Target | Cumulative |
|-------|--------|------------|
| Phase 1 | 125 tests | 125 |
| Phase 2 | +5 Go tests | 130 |
| Phase 3 | +20 desk tests | 150 |
| Phase 4 | +10 routing tests | 160 |
| Phase 5 | +10 workflow tests | 170 |
| Phase 6 | 20/20 E2E | 20/20 |
| Phase 7 | ≥13/15 LLM evals | 189 total |
| Phase 8 | 1 real founder | 1 |

---

## Current Status

**Phase:** 1 (IN PROGRESS)

**Completed:**
- ✅ v4.1 documentation archived
- ✅ v4.2 pivot defined (Internal Ops Only)
- ✅ PRD.md updated for v4.2
- ✅ README.md updated for v4.2
- ✅ INTERNAL_OPS_SCOPE.md created

**Next:**
- LLM unification (`get_llm_client()` everywhere)
- Graphiti + Neo4j integration complete
- 125 tests target

---

## DELETED FROM v4.1 (No Longer in Scope)

The following agents and features have been **removed** from the roadmap:

### Agents Removed
- ❌ Market Intelligence Agent (external-facing)
- ❌ Grant & Credit Agent (external applications)
- ❌ Jurisdiction Agent (too complex for v4.2)
- ❌ Fundraise Readiness Agent (external-facing)
- ❌ Tax Intelligence Agent (jurisdiction-heavy)
- ❌ Accounting Ops Agent (merged into Bookkeeper)
- ❌ Procurement Ops Agent (merged into IT Admin)
- ❌ Cap Table Ops Agent (too complex)
- ❌ Grant Ops Agent (external applications)
- ❌ RevOps Agent (external-facing)

### Tests Removed
- ❌ `test_tier2_external_agents.py` (40 tests)
- ❌ `test_grant_ops.py`
- ❌ `test_cap_table.py`
- ❌ `test_market_intel.py`

### Roadmap Items Removed
- ❌ Phase 8: Global Expansion (v4.1.0)
- ❌ SBIR/STTR, Innovate UK, Horizon Europe grants
- ❌ QSBS tracking, R&D credits
- ❌ Multi-jurisdiction compliance

---

**Document Version:** 4.2
**Last Updated:** March 2026
