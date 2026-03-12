# Sarthi.ai — TODO List

**Version:** 4.1.0-alpha
**Date:** 2026-03-12
**Status:** PHASE 2 IN PROGRESS

---

## Phase Execution Overview

| Phase | Status | Target | Description |
|-------|--------|--------|-------------|
| **PHASE 0** | ✅ COMPLETE | — | Foundation (Go core, Docker, Python AI) |
| **PHASE 1** | ✅ COMPLETE | — | Core Agents (Chief of Staff, Memory, Graphiti) |
| **PHASE 2** | 🔄 IN PROGRESS | 125 tests | LLM unification + Graphiti integration |
| **PHASE 3** | ⏳ PENDING | 160 tests | Tier 2 expansion + ToneFilter |
| **PHASE 4** | ⏳ PENDING | 195 tests | Full intelligence suite (8 Tier 2 agents) |
| **PHASE 5** | ⏳ PENDING | 20/20 E2E | Operations suite (9 Tier 3 agents) + workflows |
| **PHASE 6** | ⏳ PENDING | ≥13/15 evals | Production hardening |
| **PHASE 7** | ⏳ PENDING | 1 founder | v4.0.0 real milestone |
| **PHASE 8** | ⏳ PENDING | global | v4.1.0 global expansion |

---

## PHASE 2: LLM Unification + Graphiti (IN PROGRESS)

**Target:** 125 tests passing

### LLM Unification
- [ ] Audit all LLM calls across codebase
- [ ] Create `get_llm_client()` utility function
- [ ] Enforce OpenAI SDK everywhere (Azure, Groq, Ollama compatible)
- [ ] Remove direct API calls, use unified client
- [ ] Add retry logic with tenacity (3 retries, exponential backoff)
- [ ] Add timeout (30s default, 60s for long operations)
- [ ] Add circuit breaker (fail fast after 5 consecutive failures)
- [ ] Log all LLM calls with correlation IDs

### Graphiti + Neo4j Integration
- [ ] Install Graphiti Python package
- [ ] Configure Neo4j connection in `internal/config/neo4j.go`
- [ ] Create Graphiti client wrapper in `internal/memory/graphiti_client.py`
- [ ] Define entity types: Company, Founder, Transaction, Contract, Compliance
- [ ] Define relationship types: OWNS, TRANSACTS_WITH, DUE_ON, COMPLIANT_WITH
- [ ] Migrate existing Qdrant memories to Neo4j graph (where temporal matters)
- [ ] Implement hybrid search (Qdrant vector + Neo4j graph)
- [ ] Add Graphiti temporal indexing (events with timestamps)
- [ ] Test: Graph entity creation
- [ ] Test: Graph relationship creation
- [ ] Test: Temporal query (events in date range)
- [ ] Test: Hybrid search (vector + graph)

### Test Targets (125 total)
- [ ] Infrastructure health (6 tests)
- [ ] Memory Agent (15 tests) — Qdrant + Neo4j
- [ ] Chief of Staff (5 tests)
- [ ] Bank Parser (8 tests)
- [ ] CFO Agent (5 tests)
- [ ] Graphiti integration (10 tests)
- [ ] LLM client (6 tests)
- [ ] E2E flows (20 tests)
- [ ] LLM evals (15 evals)
- [ ] Tier 2 agents (20 tests) — partial
- [ ] Tier 3 agents (15 tests) — partial

---

## PHASE 3: Tier 2 Expansion

**Target:** 160 tests passing

### ToneFilter DSPy-Compiled
- [ ] Create DSPy signature for ToneFilter
- [ ] Collect 20 training examples (good news, bad news, neutral)
- [ ] Compile ToneFilter module with DSPy
- [ ] Cache compiled module (avoid recompilation)
- [ ] Test: Jargon removal (EBITDA → profit metric)
- [ ] Test: Tone adjustment (celebratory vs calm)
- [ ] Test: Hindi translation (Devanagari script)
- [ ] Test: Length constraint (under 4 sentences)

### DSPy Signatures (4 Total)
- [ ] CFOAnalysis signature
- [ ] ToneFilter signature
- [ ] TriggerClassification signature
- [ ] MemoryExtraction signature
- [ ] Training examples for each (20 per signature)
- [ ] Compile all modules
- [ ] Test compiled modules vs uncompiled (quality comparison)

### Telegram Notifier
- [ ] Implement inline keyboards for HITL gates
- [ ] Add callback query handlers
- [ ] Implement message threading (conversation continuity)
- [ ] Add rich formatting (bold, italic, code blocks)
- [ ] Add emoji support (status indicators)
- [ ] Test: Inline keyboard rendering
- [ ] Test: Callback handling
- [ ] Test: Message threading

### Go Telegram Webhook
- [ ] Create `internal/api/telegram_webhook.go`
- [ ] Implement webhook handler (POST /telegram/webhook)
- [ ] Implement `sendDM()` function (Telegram Bot API)
- [ ] Add inline keyboard support in Go
- [ ] Add callback query routing to Python agents
- [ ] Test: Webhook receives update
- [ ] Test: sendDM delivers message
- [ ] Test: Inline keyboard callback routed correctly

### Pydantic Findings Schemas
- [ ] Create `CFOFinding` schema
- [ ] Create `BIFinding` schema
- [ ] Create `RiskAlert` schema
- [ ] Create `MarketFinding` schema
- [ ] Create `FundraiseFinding` schema
- [ ] Create `TaxFinding` schema
- [ ] Create `GrantFinding` schema
- [ ] Create `JurisdictionFinding` schema
- [ ] Create `FinanceOpsResult` schema
- [ ] Create `ChiefOfStaffOutput` schema
- [ ] All schemas inherit from `AgentFinding` base
- [ ] All schemas validated at graph boundary
- [ ] Test: Schema validation (valid input)
- [ ] Test: Schema validation (invalid input, fails gracefully)

### Chief of Staff Agent
- [ ] Implement routing logic (finding → correct Tier 3 agent)
- [ ] Implement prioritization scoring (urgency × relevance)
- [ ] Implement conversation memory (Qdrant + Neo4j)
- [ ] Implement weekly briefing generation
- [ ] Test: Correct routing (90%+ accuracy)
- [ ] Test: Prioritization scoring (matches human ranking)

### Ingestion Agent
- [ ] Create data source adapters (bank PDF, CSV, Excel)
- [ ] Create data source adapters (accounting export: QBO, Xero)
- [ ] Create data source adapters (Notion page, Slack message)
- [ ] Create data source adapters (Stripe webhook, HubSpot change)
- [ ] Normalize all data to standard schema
- [ ] Add data quality checks (missing fields, outliers)
- [ ] Test: CSV ingestion (HDFC, ICICI, SBI)
- [ ] Test: PDF ingestion (bank statement)
- [ ] Test: Webhook ingestion (Stripe, HubSpot)

### Bank Statement Parser
- [ ] Support HDFC CSV format
- [ ] Support ICICI CSV format
- [ ] Support SBI CSV format
- [ ] Support digital PDF (pdfplumber, no OCR)
- [ ] Support scanned PDF (Docling with OCR)
- [ ] Support Excel (.xlsx) format
- [ ] Auto-categorize transactions (LLM-based)
- [ ] Test: HDFC CSV parsed correctly
- [ ] Test: ICICI CSV parsed correctly
- [ ] Test: SBI CSV parsed correctly
- [ ] Test: Digital PDF routes to pdfplumber
- [ ] Test: Scanned PDF routes to Docling
- [ ] Test: Transaction categorization accurate

### Sandbox Service
- [ ] Harden sandbox isolation (no network, limited syscalls)
- [ ] Add timeout enforcement (max 30s execution)
- [ ] Add memory limit (max 256MB)
- [ ] Add output capture (stdout, stderr)
- [ ] Add error reporting (sandbox crash, timeout)
- [ ] Test: Code execution succeeds
- [ ] Test: Timeout enforced
- [ ] Test: Network blocked
- [ ] Test: Memory limit enforced

### Test Targets (160 total)
- [ ] All PHASE 2 tests (125)
- [ ] ToneFilter tests (8)
- [ ] DSPy signature tests (8)
- [ ] Telegram tests (8)
- [ ] Pydantic schema tests (10)
- [ ] Chief of Staff tests (5)
- [ ] Ingestion tests (8)
- [ ] Bank parser tests (8)
- [ ] Sandbox tests (6)

---

## PHASE 4: Full Intelligence Suite

**Target:** 195 tests passing

### CFO Agent
- [ ] 13-week rolling cash flow forecast
- [ ] Burn rate tracking + runway calculation
- [ ] Margin analysis per product/service line
- [ ] Unit economics: CAC, LTV, payback period
- [ ] Scenario modeling: "what if we hire in March?"
- [ ] Fundraising readiness scoring
- [ ] Vendor payment optimization
- [ ] Pricing power analysis
- [ ] Test: Runway calculation correct
- [ ] Test: Burn spike detection (>15%)
- [ ] Test: Scenario modeling accurate
- [ ] Test: Proactive alert fires on low runway

### Risk Agent + Compliance Calendar
- [ ] Multi-jurisdiction compliance (India, US, UK, EU)
- [ ] GST, TDS, advance tax (India)
- [ ] VAT, Corporation Tax, PAYE (UK)
- [ ] Sales tax, 1099 (US)
- [ ] VAT MOSS (EU)
- [ ] Contract expiry tracking
- [ ] Regulatory change monitoring
- [ ] DPDP Act / GDPR / CCPA compliance
- [ ] Test: Deadline calculation correct
- [ ] Test: Multi-jurisdiction support
- [ ] Test: Alert fires <14 days before deadline

### BI Agent
- [ ] Customer cohort analysis (retention, churn)
- [ ] Revenue concentration risk
- [ ] Product/feature usage vs revenue
- [ ] Anomaly detection
- [ ] Cross-source pattern correlation
- [ ] Test: Cohort analysis correct
- [ ] Test: Concentration risk detected (>30%)
- [ ] Test: Anomaly detection accurate

### Market Intel Agent + Crawler
- [ ] Crawl4AI integration (self-hosted)
- [ ] Firecrawl integration (structured extraction)
- [ ] Competitor pricing tracking
- [ ] Funding announcement monitoring
- [ ] Hiring signal detection
- [ ] Test: Crawler extracts correct data
- [ ] Test: Competitor change detected
- [ ] Test: Funding announcement parsed

### Jurisdiction Agent (NEW v4.1)
- [ ] Entity formation recommendation (Delaware, UK Ltd, Singapore Pte)
- [ ] Tax residency optimization
- [ ] Permanent establishment risk assessment
- [ ] Local compliance matrix (by country)
- [ ] Banking/payroll recommendations
- [ ] Data localization requirements
- [ ] Test: Entity recommendation correct (US startup)
- [ ] Test: Entity recommendation correct (UK startup)
- [ ] Test: PE risk detected
- [ ] Test: Compliance matrix accurate

### Fundraise Readiness Agent (NEW v4.1)
- [ ] Fundraising readiness score (0-100)
- [ ] Data room completeness audit
- [ ] Financial model review (assumptions)
- [ ] Cap table health check
- [ ] Pitch deck gap analysis
- [ ] Valuation benchmarking
- [ ] Test: Readiness score accurate
- [ ] Test: Data room gaps identified
- [ ] Test: Cap table red flags detected

### Tax Intelligence Agent (NEW v4.1)
- [ ] R&D tax credit identification (US, UK, EU)
- [ ] QSBS tracking (US Section 1202)
- [ ] Patent box optimization (UK, EU)
- [ ] GST input credit optimization (India)
- [ ] Transfer pricing risk assessment
- [ ] Test: R&D credit eligibility detected
- [ ] Test: QSBS eligibility window warning
- [ ] Test: Transfer pricing risk flagged

### Grant & Credit Agent (NEW v4.1)
- [ ] SBIR/STTR grant matching (US)
- [ ] Innovate UK grant matching
- [ ] Horizon Europe grant matching
- [ ] State-level incentive tracking
- [ ] Application deadline tracking
- [ ] Test: Grant match score >80%
- [ ] Test: Deadline alert <30 days
- [ ] Test: Eligibility assessment accurate

### Test Targets (195 total)
- [ ] All PHASE 3 tests (160)
- [ ] CFO agent tests (5)
- [ ] Risk agent tests (5)
- [ ] BI agent tests (5)
- [ ] Market agent tests (5)
- [ ] Jurisdiction agent tests (5)
- [ ] Fundraise agent tests (5)
- [ ] Tax agent tests (5)
- [ ] Grant agent tests (5)

---

## PHASE 5: Operations Suite + Workflows

**Target:** 20/20 E2E tests green

### Finance Ops Agent
- [ ] Expense categorization (auto)
- [ ] Invoice generation
- [ ] Payment reminder drafts
- [ ] GST/VAT return data prep
- [ ] Bank vs books reconciliation
- [ ] Test: Expense categorized correctly
- [ ] Test: Invoice generated
- [ ] Test: Payment reminder drafted

### Accounting Ops Agent (NEW v4.1)
- [ ] Month-end close checklist
- [ ] Accrual calculations
- [ ] Depreciation schedules
- [ ] Prepaid expense amortization
- [ ] Consolidated financial statements
- [ ] Audit prep workpapers
- [ ] Test: Month-end close completed
- [ ] Test: Accruals calculated correctly
- [ ] Test: Depreciation schedule accurate

### Legal Ops Agent
- [ ] NDA generation (templates)
- [ ] Contract review summary
- [ ] MCA/Companies House filing reminders
- [ ] DPDP/GDPR compliance checklist
- [ ] Test: NDA generated correctly
- [ ] Test: Contract summary accurate
- [ ] Test: Filing deadline tracked

### HR Ops Agent
- [ ] Onboarding checklist execution
- [ ] Offer letter generation
- [ ] Payroll data prep
- [ ] PF/ESIC/pension filing
- [ ] Test: Onboarding completed
- [ ] Test: Offer letter generated
- [ ] Test: Payroll data accurate

### RevOps Agent
- [ ] CRM hygiene (auto-update)
- [ ] Pipeline velocity tracking
- [ ] Follow-up sequence execution
- [ ] Proposal generation
- [ ] Test: CRM updated correctly
- [ ] Test: Pipeline stall detected
- [ ] Test: Follow-up drafted

### Admin Ops Agent
- [ ] Meeting prep (context, agenda)
- [ ] Action item extraction
- [ ] SOP documentation
- [ ] Tool stack audit
- [ ] Test: Meeting prep complete
- [ ] Test: Action items extracted
- [ ] Test: Tool audit accurate

### Procurement Ops Agent (NEW v4.1)
- [ ] Vendor quote comparison
- [ ] Contract renewal tracking (90-day)
- [ ] Spend analysis by category
- [ ] Negotiation prep (benchmarks)
- [ ] Test: Quote comparison accurate
- [ ] Test: Renewal alert <90 days
- [ ] Test: Spend analysis correct

### Cap Table Ops Agent (NEW v4.1)
- [ ] Cap table maintenance
- [ ] Option pool tracking
- [ ] Dilution scenario modeling
- [ ] SAFE/convertible tracking
- [ ] Exit waterfall analysis
- [ ] Test: Cap table accurate
- [ ] Test: Dilution scenario correct
- [ ] Test: Exit waterfall accurate

### Grant Ops Agent (NEW v4.1)
- [ ] Grant application drafting
- [ ] Supporting document collection
- [ ] Milestone tracking (post-award)
- [ ] Reporting compliance
- [ ] Test: Application drafted
- [ ] Test: Documents collected
- [ ] Test: Milestone tracked

### BusinessOS Workflow (Go)
- [ ] Implement `BusinessOSWorkflow` in Go
- [ ] Orchestrate all agents via Temporal
- [ ] Enforce HITL gates
- [ ] Maintain audit trail
- [ ] Test: Workflow executes all agents
- [ ] Test: HITL gate pauses workflow
- [ ] Test: Audit trail complete

### Onboarding Workflow (Go)
- [ ] Implement 6-question onboarding
- [ ] Store responses in PostgreSQL
- [ ] Create founder memory in Qdrant + Neo4j
- [ ] Trigger initial analysis
- [ ] Test: Onboarding completes <10 min
- [ ] Test: Memory created correctly
- [ ] Test: Initial analysis triggered

### Weekly Checkin Workflow (Go)
- [ ] Implement weekly briefing generation
- [ ] Schedule every Monday 9am (founder timezone)
- [ ] Aggregate all agent findings from week
- [ ] Prioritize + summarize
- [ ] Test: Briefing generated correctly
- [ ] Test: Schedule respects timezone
- [ ] Test: Findings aggregated

### HITL Gate E2E Test
- [ ] Test: Agent fires finding
- [ ] Test: Chief of Staff routes to founder
- [ ] Test: Telegram inline keyboard rendered
- [ ] Test: Founder approves action
- [ ] Test: Action executed
- [ ] Test: Outcome recorded in memory

### E2E Test Suite (20/20 Green)
- [ ] Flow 1: First-time founder onboarding (6 tests)
- [ ] Flow 2: Weekly reflection → trigger → Telegram (5 tests)
- [ ] Flow 3: Market signal → intervention (3 tests)
- [ ] Flow 4: Sandbox execution (3 tests)
- [ ] Flow 5: Calibration loop (3 tests)

---

## PHASE 6: Production Hardening

**Target:** ≥13/15 LLM evals pass

### DSPy Eval Suite
- [ ] Create 15 evals (LLM-as-judge)
- [ ] EVAL 1-5: TriggerAgent output quality
  - Message under 4 sentences
  - Contains ₹/$/£ amounts
  - No jargon words
  - Ends with one action
  - Suppression reason specific
- [ ] EVAL 6-9: ToneFilter fidelity
  - EBITDA replaced
  - Good news celebratory
  - Bad news calm
  - Hindi contains Devanagari
- [ ] EVAL 10-12: ContextInterviewAgent
  - Extracted context matches intent
  - Confidence <0.8 for vague answers
  - ICP context_type correct
- [ ] EVAL 13-15: MemoryAgent pattern detection
  - Builder archetype from coding reflections
  - Avoidance pattern detected
  - Commitment completion rate estimated
- [ ] Target: ≥13/15 evals pass

### Circuit Breaker
- [ ] Implement circuit breaker for all external calls
- [ ] LLM calls (Azure OpenAI)
- [ ] Telegram API
- [ ] Razorpay/Stripe API
- [ ] QuickBooks/Xero API
- [ ] Qdrant API
- [ ] Neo4j API
- [ ] Test: Circuit opens after 5 failures
- [ ] Test: Circuit half-opens after timeout
- [ ] Test: Circuit closes on success

### Rate Limiter
- [ ] Telegram API (30 msg/sec)
- [ ] Razorpay API (as per plan)
- [ ] Stripe API (as per plan)
- [ ] QuickBooks API (as per plan)
- [ ] LLM API (token budget)
- [ ] Test: Rate limit enforced
- [ ] Test: Queue builds up correctly
- [ ] Test: Error returned when queue full

### GitHub Actions CI
- [ ] Create `.github/workflows/ci.yml`
- [ ] Run unit tests on every PR
- [ ] Run lint (go lint, black, mypy)
- [ ] Run type check (tsc --noEmit)
- [ ] Block merge if tests fail
- [ ] Test: CI runs on PR
- [ ] Test: Tests block merge

### GitHub Actions E2E
- [ ] Create `.github/workflows/e2e.yml`
- [ ] Manual trigger (workflow_dispatch)
- [ ] Spin up Docker services
- [ ] Run E2E test suite
- [ ] Upload test artifacts (video, logs)
- [ ] Test: E2E runs on trigger
- [ ] Test: Artifacts uploaded

### Langfuse Traces
- [ ] Integrate Langfuse (Cloud free tier)
- [ ] Trace every LLM call
- [ ] Trace every agent graph
- [ ] Trace every Temporal workflow
- [ ] Target: p95 latency < 8s
- [ ] Test: Traces appear in Langfuse
- [ ] Test: Latency < 8s p95

---

## PHASE 7: v4.0.0 REAL MILESTONE

**Target:** One real founder signs up and reports value

### Human Onboarding Test
- [ ] One real founder signs up via Telegram
- [ ] Completes onboarding (< 10 min)
- [ ] Uploads real bank statement
- [ ] Receives real CFO finding
- [ ] Approves one action via Telegram
- [ ] Reports "This saved me time"
- [ ] → **TAG v4.0.0**

---

## PHASE 8: v4.1.0 Global Expansion

**Target:** First non-India founder onboarded

### Jurisdiction Agent Live
- [ ] US entity formation guidance (Delaware C-Corp)
- [ ] UK entity formation guidance (UK Ltd)
- [ ] EU entity formation guidance (GmbH, SAS)
- [ ] Tax residency optimization (all jurisdictions)
- [ ] Permanent establishment risk (all jurisdictions)

### Grant Agent Live
- [ ] SBIR/STTR grants (US)
- [ ] Innovate UK grants
- [ ] Horizon Europe grants
- [ ] Application support (drafting, submission)

### Tax Intelligence Live
- [ ] QSBS tracking (US Section 1202)
- [ ] R&D tax credits (US, UK, EU)
- [ ] Patent box optimization (UK, EU)

### Fundraise Readiness Live
- [ ] Data room audit
- [ ] Financial model review
- [ ] Cap table health check
- [ ] Pitch deck analysis

### Global Founder Onboarding
- [ ] First US founder onboarded
- [ ] First UK founder onboarded
- [ ] First EU founder onboarded
- [ ] All report "This saved me time"
- [ ] → **TAG v4.1.0**

---

## Summary

| Phase | Tests | Key Deliverables | Status |
|-------|-------|------------------|--------|
| **PHASE 2** | 125 | LLM unification, Graphiti | 🔄 IN PROGRESS |
| **PHASE 3** | 160 | ToneFilter, Pydantic schemas, Telegram | ⏳ PENDING |
| **PHASE 4** | 195 | 8 Tier 2 agents (incl. 4 new) | ⏳ PENDING |
| **PHASE 5** | 20/20 E2E | 9 Tier 3 agents, Go workflows | ⏳ PENDING |
| **PHASE 6** | ≥13/15 evals | Circuit breaker, rate limiter, CI | ⏳ PENDING |
| **PHASE 7** | 1 founder | v4.0.0 real milestone | ⏳ PENDING |
| **PHASE 8** | global | v4.1.0 global expansion | ⏳ PENDING |

---

**Last Updated:** 2026-03-12
**Next Review:** After PHASE 2 completion
