# Sarthi.ai — Phase Execution Plan

**Version:** 4.1.0-alpha
**Date:** 2026-03-12
**Status:** PHASE 2 IN PROGRESS

---

## Overview

This document defines the complete phase execution order for Sarthi v4.1. Each phase builds on the previous, with clear entry/exit criteria and test targets.

```
PHASE 0 → PHASE 1 → PHASE 2 → PHASE 3 → PHASE 4 → PHASE 5 → PHASE 6 → PHASE 7 → PHASE 8
  ✓          ✓         🔄         ⏳         ⏳         ⏳         ⏳         ⏳         ⏳
```

---

## PHASE 0: Foundation

**Status:** ✅ COMPLETE

**Objective:** Establish core infrastructure and development environment.

### Deliverables

| Component | Technology | Status |
|-----------|------------|--------|
| Go Core Service | Go 1.24, Fiber, sqlc | ✅ |
| Python AI Service | Python 3.13, LangGraph, Pydantic, DSPy | ✅ |
| PostgreSQL | Docker, sqlc generated code | ✅ |
| Qdrant | Docker, vector memory | ✅ |
| Neo4j | Docker, graph memory | ✅ |
| Temporal | Docker, workflow orchestration | ✅ |
| Redpanda | Docker, message queue | ✅ |
| Telegram Bot | Bot API, webhook integration | ✅ |
| Docker Compose | Service orchestration | ✅ |
| Makefile | Build/run commands | ✅ |

### Exit Criteria

- [x] All Docker services start successfully
- [x] Go server responds to health check
- [x] Python AI service imports successfully
- [x] PostgreSQL connection established
- [x] Qdrant connection established
- [x] Neo4j connection established
- [x] Temporal worker connects
- [x] Telegram webhook configured

---

## PHASE 1: Core Agents

**Status:** ✅ COMPLETE

**Objective:** Build foundational agents that form the system backbone.

### Deliverables

| Agent | Tier | Status |
|-------|------|--------|
| Chief of Staff Agent | Tier 1 | ✅ |
| ToneFilter (basic) | Tier 1 | ✅ |
| Memory Agent (Qdrant) | Tier 4 | ✅ |
| Memory Agent (Neo4j) | Tier 4 | ✅ |
| Graphiti Integration | Tier 4 | ✅ |
| Sandbox Service | Infrastructure | ✅ |
| Ingestion Agent (basic) | Tier 4 | ✅ |

### Key Features

- **Chief of Staff:** Routes findings, manages founder relationship
- **ToneFilter:** Removes jargon, ensures plain language output
- **Memory Agent:** Stores/retrieves company context (vector + graph)
- **Graphiti:** Temporal knowledge graph (events with timestamps)
- **Sandbox:** Isolated Python execution for agent actions
- **Ingestion:** Normalizes data from multiple sources

### Exit Criteria

- [x] Chief of Staff routes findings correctly (80%+ accuracy)
- [x] ToneFilter removes jargon (100% of banned words)
- [x] Memory Agent stores/retrieves correctly
- [x] Graphiti temporal queries work
- [x] Sandbox executes code safely
- [x] 106+ tests passing

---

## PHASE 2: LLM Unification + Graphiti

**Status:** 🔄 IN PROGRESS

**Objective:** Standardize LLM calls and complete Graphiti integration.

### Deliverables

| Component | Description | Status |
|-----------|-------------|--------|
| `get_llm_client()` | Unified LLM client factory | 🔄 |
| OpenAI SDK | Enforced across all agents | 🔄 |
| Retry logic | Tenacity, 3 retries, exponential backoff | 🔄 |
| Timeout enforcement | 30s default, 60s long ops | 🔄 |
| Circuit breaker | Fail fast after 5 failures | 🔄 |
| Graphiti client | Python wrapper for Neo4j | 🔄 |
| Entity types | Company, Founder, Transaction, Contract, Compliance | 🔄 |
| Relationship types | OWNS, TRANSACTS_WITH, DUE_ON, COMPLIANT_WITH | 🔄 |
| Hybrid search | Qdrant vector + Neo4j graph | 🔄 |

### Test Targets: 125 total

| Category | Count | Status |
|----------|-------|--------|
| Infrastructure Health | 6 | 🔄 |
| Memory Agent (Qdrant + Neo4j) | 15 | 🔄 |
| Chief of Staff | 5 | 🔄 |
| Bank Parser | 8 | 🔄 |
| CFO Agent | 5 | 🔄 |
| Graphiti Integration | 10 | 🔄 |
| LLM Client | 6 | 🔄 |
| E2E Flows | 20 | 🔄 |
| LLM Evals | 15 | 🔄 |
| Tier 2 Agents (partial) | 20 | 🔄 |
| Tier 3 Agents (partial) | 15 | 🔄 |

### Exit Criteria

- [ ] All LLM calls use `get_llm_client()`
- [ ] Retry logic tested (3 retries observed)
- [ ] Circuit breaker opens after 5 failures
- [ ] Graphiti entities created correctly
- [ ] Graphiti relationships created correctly
- [ ] Hybrid search returns relevant results
- [ ] 125+ tests passing

---

## PHASE 3: Tier 2 Expansion

**Status:** ⏳ PENDING

**Objective:** Complete Tier 2 intelligence agents with DSPy optimization.

### Deliverables

| Component | Description | Status |
|-----------|-------------|--------|
| ToneFilter DSPy | DSPy-compiled, 4 signatures | ⏳ |
| Telegram inline keyboards | HITL gates, callbacks | ⏳ |
| Go telegram.go | Webhook handler, sendDM() | ⏳ |
| Pydantic schemas | All agent findings (10 schemas) | ⏳ |
| Chief of Staff v2 | Routing + prioritization | ⏳ |
| Ingestion Agent v2 | Multi-format support | ⏳ |
| Bank Parser v2 | HDFC, ICICI, SBI, PDF, Excel | ⏳ |
| Sandbox v2 | Hardened isolation | ⏳ |

### DSPy Signatures (4 Total)

1. **CFOAnalysis:** Financial analysis with plain language output
2. **ToneFilter:** Jargon removal + tone adjustment
3. **TriggerClassification:** Classify incoming triggers
4. **MemoryExtraction:** Extract memories from conversations

### Test Targets: 160 total

| Category | Count | Status |
|----------|-------|--------|
| All PHASE 2 tests | 125 | ⏳ |
| ToneFilter tests | 8 | ⏳ |
| DSPy signature tests | 8 | ⏳ |
| Telegram tests | 8 | ⏳ |
| Pydantic schema tests | 10 | ⏳ |
| Chief of Staff tests | 5 | ⏳ |
| Ingestion tests | 8 | ⏳ |
| Bank parser tests | 8 | ⏳ |
| Sandbox tests | 6 | ⏳ |

### Exit Criteria

- [ ] ToneFilter DSPy-compiled (not raw prompts)
- [ ] Telegram inline keyboards render correctly
- [ ] Go webhook receives Telegram updates
- [ ] All Pydantic schemas validate correctly
- [ ] Bank parser handles all formats
- [ ] 160+ tests passing

---

## PHASE 4: Full Intelligence Suite

**Status:** ⏳ PENDING

**Objective:** Complete all 8 Tier 2 intelligence agents.

### Deliverables

| Agent | Type | Status |
|-------|------|--------|
| CFO Agent | Existing, complete | ⏳ |
| BI Agent | Existing, complete | ⏳ |
| Risk Agent | Multi-jurisdiction | ⏳ |
| Market Agent | With crawler | ⏳ |
| **Fundraise Readiness Agent** | **NEW v4.1** | ⏳ |
| **Tax Intelligence Agent** | **NEW v4.1** | ⏳ |
| **Grant & Credit Agent** | **NEW v4.1** | ⏳ |
| **Jurisdiction Agent** | **NEW v4.1** | ⏳ |

### New Agent Capabilities (v4.1)

**Fundraise Readiness Agent:**
- Fundraising readiness score (0-100)
- Data room completeness audit
- Financial model review
- Cap table health check
- Pitch deck gap analysis

**Tax Intelligence Agent:**
- R&D tax credit identification (US, UK, EU)
- QSBS tracking (US Section 1202)
- Patent box optimization (UK, EU)
- GST input credit optimization (India)
- Transfer pricing risk assessment

**Grant & Credit Agent:**
- SBIR/STTR grant matching (US)
- Innovate UK grant matching
- Horizon Europe grant matching
- State-level incentive tracking
- Application deadline tracking

**Jurisdiction Agent:**
- Entity formation recommendation
- Tax residency optimization
- Permanent establishment risk
- Local compliance matrix
- Banking/payroll recommendations

### Test Targets: 195 total

| Category | Count | Status |
|----------|-------|--------|
| All PHASE 3 tests | 160 | ⏳ |
| CFO agent tests | 5 | ⏳ |
| Risk agent tests | 5 | ⏳ |
| BI agent tests | 5 | ⏳ |
| Market agent tests | 5 | ⏳ |
| Jurisdiction agent tests | 5 | ⏳ |
| Fundraise agent tests | 5 | ⏳ |
| Tax agent tests | 5 | ⏳ |
| Grant agent tests | 5 | ⏳ |

### Exit Criteria

- [ ] All 8 Tier 2 agents operational
- [ ] Each agent fires findings correctly
- [ ] Multi-jurisdiction compliance works (India, US, UK, EU)
- [ ] 195+ tests passing

---

## PHASE 5: Operations Suite + Workflows

**Status:** ⏳ PENDING

**Objective:** Complete all 9 Tier 3 operations agents and Go workflows.

### Deliverables

| Agent | Type | Status |
|-------|------|--------|
| Finance Ops Agent | Existing | ⏳ |
| **Accounting Ops Agent** | **NEW v4.1** | ⏳ |
| HR Ops Agent | Existing | ⏳ |
| Legal Ops Agent | Existing | ⏳ |
| RevOps Agent | Existing | ⏳ |
| Admin Ops Agent | Existing | ⏳ |
| **Procurement Ops Agent** | **NEW v4.1** | ⏳ |
| **Cap Table Ops Agent** | **NEW v4.1** | ⏳ |
| **Grant Ops Agent** | **NEW v4.1** | ⏳ |

### Go Workflows (Temporal)

| Workflow | Purpose | Status |
|----------|---------|--------|
| BusinessOSWorkflow | Orchestrates all agents | ⏳ |
| OnboardingWorkflow | 6-question founder onboarding | ⏳ |
| WeeklyCheckinWorkflow | Monday 9am briefing | ⏳ |

### New Agent Capabilities (v4.1)

**Accounting Ops Agent:**
- Month-end close checklist
- Accrual calculations
- Depreciation schedules
- Consolidated financial statements
- Audit prep workpapers

**Procurement Ops Agent:**
- Vendor quote comparison
- Contract renewal tracking (90-day warning)
- Spend analysis by category
- Negotiation prep (benchmarks)

**Cap Table Ops Agent:**
- Cap table maintenance
- Option pool tracking
- Dilution scenario modeling
- SAFE/convertible tracking
- Exit waterfall analysis

**Grant Ops Agent:**
- Grant application drafting
- Supporting document collection
- Milestone tracking (post-award)
- Reporting compliance

### Test Targets: 20/20 E2E tests green

| E2E Flow | Tests | Status |
|----------|-------|--------|
| Flow 1: First-time founder onboarding | 6 | ⏳ |
| Flow 2: Weekly reflection → trigger → Telegram | 5 | ⏳ |
| Flow 3: Market signal → intervention | 3 | ⏳ |
| Flow 4: Sandbox execution | 3 | ⏳ |
| Flow 5: Calibration loop | 3 | ⏳ |

### Exit Criteria

- [ ] All 9 Tier 3 agents operational
- [ ] BusinessOSWorkflow orchestrates correctly
- [ ] Onboarding completes <10 min
- [ ] Weekly briefing delivered Monday 9am
- [ ] HITL gates pause/resume workflows
- [ ] 20/20 E2E tests green

---

## PHASE 6: Production Hardening

**Status:** ⏳ PENDING

**Objective:** Harden system for production with reliability features.

### Deliverables

| Component | Description | Status |
|-----------|-------------|--------|
| DSPy Eval Suite | 15 evals, LLM-as-judge | ⏳ |
| Circuit Breaker | All external calls | ⏳ |
| Rate Limiter | Telegram, Razorpay, Stripe, etc. | ⏳ |
| GitHub Actions CI | Unit tests + lint on PR | ⏳ |
| GitHub Actions E2E | Manual trigger, full suite | ⏳ |
| Langfuse Integration | Trace every call | ⏳ |

### DSPy Eval Suite (15 Evals)

**EVAL 1-5: TriggerAgent Output Quality**
- Message under 4 sentences
- Contains ₹/$/£ amounts
- No jargon words
- Ends with one action
- Suppression reason specific

**EVAL 6-9: ToneFilter Fidelity**
- EBITDA replaced
- Good news celebratory
- Bad news calm
- Hindi contains Devanagari

**EVAL 10-12: ContextInterviewAgent**
- Extracted context matches intent
- Confidence <0.8 for vague answers
- ICP context_type correct

**EVAL 13-15: MemoryAgent Pattern Detection**
- Builder archetype from coding reflections
- Avoidance pattern detected
- Commitment completion rate estimated

**Target:** ≥13/15 evals pass

### Exit Criteria

- [ ] ≥13/15 LLM evals pass
- [ ] Circuit breaker opens after 5 failures
- [ ] Rate limiter enforces limits
- [ ] CI runs on every PR
- [ ] E2E runs on manual trigger
- [ ] Langfuse traces < 8s p95

---

## PHASE 7: v4.0.0 REAL MILESTONE

**Status:** ⏳ PENDING

**Objective:** One real founder uses Sarthi and reports value.

### Deliverables

| Milestone | Status |
|-----------|--------|
| One real founder signs up via Telegram | ⏳ |
| Completes onboarding (< 10 min) | ⏳ |
| Uploads real bank statement | ⏳ |
| Receives real CFO finding | ⏳ |
| Approves one action via Telegram | ⏳ |
| Reports "This saved me time" | ⏳ |
| **→ TAG v4.0.0** | ⏳ |

### Exit Criteria

- [ ] One real founder (not team member) signs up
- [ ] Onboarding completes in <10 min
- [ ] Bank statement parsed correctly
- [ ] CFO finding delivered via Telegram
- [ ] Founder approves action via inline keyboard
- [ ] Founder reports time saved (qualitative feedback)
- [ ] **TAG v4.0.0 released**

---

## PHASE 8: v4.1.0 Global Expansion

**Status:** ⏳ PENDING

**Objective:** First non-India founder onboarded, global features live.

### Deliverables

| Component | Jurisdictions | Status |
|-----------|---------------|--------|
| Jurisdiction Agent | US + UK + EU | ⏳ |
| Grant Agent | SBIR, Innovate UK, Horizon Europe | ⏳ |
| Tax Intelligence | QSBS, R&D credits | ⏳ |
| Fundraise Readiness | All jurisdictions | ⏳ |
| First non-India founder | US or UK or EU | ⏳ |
| **→ TAG v4.1.0** | ⏳ |

### Jurisdiction Coverage

| Jurisdiction | Entity Type | Tax Compliance | Grants | Tax Credits |
|--------------|-------------|----------------|--------|-------------|
| **India** | Pvt Ltd | GST, TDS, PF, ESIC | DST, BIRAC | Limited |
| **US** | Delaware C-Corp | Sales tax, 1099 | SBIR/STTR | R&D, QSBS |
| **UK** | UK Ltd | VAT, Corporation Tax, PAYE | Innovate UK | R&D, Patent Box |
| **EU** | GmbH, SAS | VAT MOSS, local tax | Horizon Europe | R&D, Patent Box |

### Exit Criteria

- [ ] Jurisdiction agent recommends correct entity (US, UK, EU)
- [ ] Grant agent identifies SBIR, Innovate UK, Horizon Europe grants
- [ ] Tax intelligence identifies QSBS, R&D credits
- [ ] Fundraise readiness agent live for all jurisdictions
- [ ] First US founder onboarded OR
- [ ] First UK founder onboarded OR
- [ ] First EU founder onboarded
- [ ] **→ TAG v4.1.0 released**

---

## Summary

| Phase | Target | Key Deliverable | Status |
|-------|--------|-----------------|--------|
| **PHASE 0** | Foundation | Infrastructure | ✅ COMPLETE |
| **PHASE 1** | Core Agents | Chief of Staff, Memory | ✅ COMPLETE |
| **PHASE 2** | 125 tests | LLM unification, Graphiti | 🔄 IN PROGRESS |
| **PHASE 3** | 160 tests | DSPy, Telegram, Pydantic | ⏳ PENDING |
| **PHASE 4** | 195 tests | 8 Tier 2 agents (4 new) | ⏳ PENDING |
| **PHASE 5** | 20/20 E2E | 9 Tier 3 agents, Go workflows | ⏳ PENDING |
| **PHASE 6** | ≥13/15 evals | Production hardening | ⏳ PENDING |
| **PHASE 7** | 1 founder | v4.0.0 real milestone | ⏳ PENDING |
| **PHASE 8** | global | v4.1.0 global expansion | ⏳ PENDING |

---

**Last Updated:** 2026-03-12
**Current Phase:** PHASE 2
**Next Milestone:** 125 tests passing
