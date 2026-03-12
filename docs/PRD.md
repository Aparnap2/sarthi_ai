# Sarthi.ai — Product Requirements Document

**Version:** 4.1
**Date:** 2026-03-12
**Status:** PRODUCTION READY

---

## Executive Summary

**Sarthi.ai** is a virtual back-office OS for early-stage startups. Every operational task that doesn't require unique human judgment — Sarthi handles. Everything that does — Sarthi prepares perfectly and puts in front of you in 30 seconds, not 3 hours.

**Tagline:** *Your virtual back-office. Internal ops OS powered by self-correcting, context-aware, proactive, obedient vertical agentic AI.*

---

## The Problem: Back-Office Drag

Research-backed data on startup operational pain:

| Metric | Impact |
|--------|--------|
| **Tools fragmentation** | Average startup uses **15 different tools** across payroll, finance, HR, compliance |
| **Founder time waste** | **15–20 hours/week** on back-office tasks = **$9,000–$22,500/month** hidden cost |
| **Roadmap delay** | Back-office drag delays product roadmaps by **~3 months per year** |
| **Fundraising impact** | Ops chaos pushes fundraising timelines back by 1-2 quarters |

**The gap:** Not "startups don't have tools" — it's **15 disconnected tools with no intelligence layer connecting them**.

---

## Target ICP

### Who Sarthi Is For

```
Stage:      Pre-seed to Series A
Team size:  1–25 people
Type:       Product/tech startup (B2B/B2C SaaS, D2C, marketplace, fintech, edtech)
Location:   Global (US → UK → EU → SEA expansion path)
```

### What They Already Have

- ✅ Notion or Confluence (docs, SOPs, decisions)
- ✅ Linear or Jira (product/engineering tasks)
- ✅ Slack (communication)
- ✅ Razorpay / Stripe (payments)
- ✅ Google Workspace (email, sheets, drive)
- ✅ QuickBooks / Xero / Zoho Books (accounting)
- ✅ Some HR tool: Razorpay Payroll / Keka / Darwinbox / Gusto

### What They Don't Have

- ❌ A COO, CFO, Head of HR, Legal counsel, BI analyst
- ❌ Anyone whose job is to connect the dots across tools
- ❌ Any system that proactively catches ops problems
- ❌ Time — founders spend 25–40% of their week on back-office work

---

## The Complete Agent Architecture (v4.1)

### Hierarchy Map

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 0 — KERNEL (Go + Temporal + Graphiti)                     │
│  BusinessOSWorkflow: orchestrates all agents, manages state,    │
│  enforces HITL gates, audit trail, temporal knowledge graph     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1 — CHIEF OF STAFF (1 agent)                              │
│  The only agent that talks to the founder.                      │
│  Routes work, synthesizes intelligence, manages relationship.   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2 — INTELLIGENCE DEPT (observe + advise)                  │
│  CFO | BI | Risk | Market | Fundraise Readiness | Tax Intel    │
│  | Grant & Credit | Jurisdiction                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3 — OPERATIONS DEPT (execute, not advise)                 │
│  Finance Ops | Accounting Ops | Legal Ops | HR Ops | RevOps    │
│  | Admin Ops | Procurement Ops | Cap Table Ops | Grant Ops     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 4 — DATA LAYER (ingest + memory, never surfaces)          │
│  Ingestion | Memory (Qdrant + Neo4j) | Crawler | Connector      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### Tier 1: Chief of Staff Agent

**Role:** The face of Sarthi. The only agent the founder sees.

**What it does:**
- Receives all Tier 2/3 findings
- Scores urgency + relevance to current priorities
- Translates into plain founder language (no jargon)
- Manages conversation continuity (memory)
- Routes inbound requests to correct Tier 3 agent
- Escalates decisions that need the founder
- Weekly briefing: "Here's what happened, here's what I handled, here's what needs you"

**Tools (LangGraph):**
- `QueryMemoryTool` (Qdrant + Neo4j — full company context)
- `PrioritizationTool` (score + rank agent findings)
- `ToneFilterTool` (jargon → plain language, DSPy-compiled)
- `TelegramDeliveryTool` (inline keyboards, HITL gates)
- `WhatsAppDeliveryTool` (mobile-first founders)
- `HITL GateTool` (surface decision to founder)

**APIs:**
- Telegram Bot API (primary output)
- WhatsApp Business API (secondary)
- Temporal Signal API (trigger workflows)

**Output format:** Always one of:
- "Here's what I found + one action"
- "I handled X — here's what I did"
- "I need your decision on X — here's context"
- "Weekly briefing: X handled, Y needs you"

---

### Tier 2A: CFO Agent

**Role:** Watches the financial health of the company continuously. Proactive and diagnostic.

**What it does:**
- 13-week rolling cash flow forecast
- Burn rate tracking + runway calculation
- Margin analysis per product/service line
- Unit economics: CAC, LTV, payback period
- Scenario modeling: "what if we hire in March?"
- Fundraising readiness scoring
- Vendor payment optimization (cash flow timing)
- Pricing power analysis

**Tools:**
- `AccountingDataTool` (QuickBooks/Xero/Zoho API)
- `BankStatementParserTool` (PDF → structured data, Docling)
- `SpreadsheetTool` (Google Sheets API)
- `ScenarioModelingTool` (built-in financial engine)
- `ForecastingTool` (time-series over historical data)

**APIs:**
- QuickBooks Online API
- Xero API
- Razorpay API (revenue, payouts)
- Stripe API
- Google Sheets API v4
- RazorpayX / bank statement (PDF parse)

**Fires finding to Chief of Staff when:**
- Runway drops below 6 months
- Monthly burn increases >15% unexpectedly
- A product line margin goes negative
- Cash flow model shows shortfall in <30 days
- Fundraising readiness score changes significantly

---

### Tier 2B: BI Agent

**Role:** Finds the patterns in data that the founder would never have time to look for.

**What it does:**
- Customer cohort analysis (retention, churn)
- Revenue concentration risk (customer dependency)
- Product/feature usage vs revenue contribution
- Operational efficiency ratios
- Growth lever identification
- Anomaly detection across all data sources
- Benchmark vs sector (when data available)
- Cross-source pattern correlation

**Tools:**
- `CRMDataTool` (HubSpot/Notion CRM)
- `ProductAnalyticsTool` (Mixpanel/Amplitude API)
- `RevenueDataTool` (Stripe/Razorpay)
- `StatisticalAnalysisTool` (built-in, numpy/pandas)
- `PatternDetectionTool` (time-series, anomaly)
- `BenchmarkTool` (sector data via crawl)

**APIs:**
- Mixpanel API / Amplitude API
- Stripe API (cohort revenue data)
- HubSpot API (pipeline, customer data)
- Razorpay API

**Fires finding to Chief of Staff when:**
- Churn pattern detected before it's obvious
- One customer exceeds 30% revenue concentration
- A product line drives outsized profit (opportunity)
- Usage pattern predicts churn in specific segment

---

### Tier 2C: Risk & Compliance Agent

**Role:** Watches the legal, regulatory, and operational risk surface. Never lets a deadline slip.

**What it does:**
- GST, TDS, advance tax deadline tracking (India)
- VAT, Corporation Tax, PAYE (UK)
- VAT, Körperschaftsteuer (EU)
- PF, ESIC, PT compliance calendar
- Contract expiry and renewal tracking
- Regulatory change monitoring (sector-specific)
- IP protection status (trademark, patent)
- Data privacy compliance (DPDP Act India, GDPR UK/EU, PDPA SEA)
- Insurance gap identification
- Founder vesting schedule tracking
- Cap table basic health check

**Tools:**
- `ComplianceCalendarTool` (multi-jurisdiction tax + labor law)
- `ContractTrackerTool` (extracts dates from docs)
- `DocumentReaderTool` (Azure Document Intelligence)
- `RegulatoryMonitorTool` (crawl MCA, HMRC, EU portals)
- `DeadlineEngineTool` (calculated from context)

**APIs:**
- Azure Document Intelligence API
- MCA (Ministry of Corporate Affairs) — scrape
- HMRC API (UK)
- GST portal data (via CA/accountant integration)
- Leegality / Digio API (eSign documents)

**Fires finding to Chief of Staff when:**
- Any compliance deadline within 14 days
- A contract expires within 30 days
- A regulatory change affects their sector
- Single contractor > 40% of team (risk flag)

---

### Tier 2D: Market Intelligence Agent

**Role:** Continuous external awareness. Knows what's happening in the market so the founder doesn't have to monitor it themselves.

**What it does:**
- Competitor pricing + feature change tracking
- Funding announcements in their sector
- Customer sentiment in their market segment
- Hiring signals (what competitors are building)
- New regulation affecting their space
- Partnership/acquisition signals
- Emerging customer pain point detection

**Tools:**
- `Crawl4AiTool` (self-hosted, all web content)
- `FirecrawlTool` (structured extraction)
- `TwitterAPITool` (X search, sector trends)
- `LinkedInSignalsTool` (job posting scrape)
- `NewsAggregatorTool` (filtered by sector + ICP)
- `SemanticFilterTool` (relevance to this company)

**APIs:**
- Crawl4AI (Docker, self-hosted, $0)
- Firecrawl API (500 pages/mo free)
- Twitter/X API (Basic tier)
- NewsAPI or GNews API
- LinkedIn (scraping via Crawl4AI)

**Fires finding to Chief of Staff when:**
- Direct competitor changes pricing
- A major funding round in their space
- A regulation change directly affects them
- Hiring signal suggests competitor feature pivot

---

### Tier 2E: Fundraise Readiness Agent (NEW v4.1)

**Role:** Prepares the startup for fundraising. Ensures they are investor-ready at all times.

**What it does:**
- Fundraising readiness score (0-100)
- Data room completeness audit
- Financial model review (assumptions, unit economics)
- Cap table health check
- Pitch deck gap analysis
- Investor outreach tracking
- Term sheet comparison (when received)
- Due diligence prep checklist
- Valuation benchmarking (sector, stage)

**Tools:**
- `DataRoomAuditTool` (checks completeness)
- `FinancialModelReviewTool` (assumption validation)
- `CapTableAnalyzerTool` (health scoring)
- `PitchDeckAnalyzerTool` (gap detection)
- `ValuationBenchmarkTool` (sector comps)

**APIs:**
- DocSend API (pitch deck tracking)
- Carta API (cap table data)
- Crunchbase API (funding comps)
- PitchBook API (valuation benchmarks)

**Fires finding to Chief of Staff when:**
- Fundraising readiness score drops below 70
- Data room missing critical documents
- Financial model has unrealistic assumptions
- Cap table has red flags (founder dilution, option pool issues)

---

### Tier 2F: Tax Intelligence Agent (NEW v4.1)

**Role:** Maximizes tax efficiency. Finds every credit, deduction, and incentive the startup is eligible for.

**What it does:**
- R&D tax credit identification (US, UK, EU)
- QSBS (Qualified Small Business Stock) tracking (US)
- Patent box regime optimization (UK, EU)
- GST input credit optimization (India)
- Transfer pricing risk assessment
- Tax treaty benefit analysis
- Employee stock option tax planning
- Sales tax / VAT nexus monitoring

**Tools:**
- `TaxCreditFinderTool` (R&D, innovation credits)
- `QSBS TrackerTool` (US Section 1202)
- `TransferPricingTool` (arm's length analysis)
- `VATOptimizerTool` (input credit, nexus)
- `ESOPTaxTool` (employee option planning)

**APIs:**
- IRS API (US tax data)
- HMRC API (UK tax data)
- GSTN API (India)
- Orbis / Bureau van Dijk (transfer pricing comps)

**Fires finding to Chief of Staff when:**
- R&D credit eligibility detected (₹/$/£50k+ value)
- QSBS eligibility window closing (6-month warning)
- Transfer pricing documentation required
- VAT registration threshold crossed in new jurisdiction

---

### Tier 2G: Grant & Credit Agent (NEW v4.1)

**Role:** Identifies and secures non-dilutive funding. Free money the startup is eligible for.

**What it does:**
- SBIR/STTR grant matching (US)
- Innovate UK grant matching
- Horizon Europe grant matching
- State-level incentive tracking (India, US, EU)
- Carbon credit eligibility assessment
- Export incentive tracking
- Patent subsidy identification
- Application deadline tracking
- Grant reporting compliance

**Tools:**
- `GrantMatcherTool` (SBIR, Innovate UK, Horizon Europe)
- `EligibilityScorerTool` (fit scoring)
- `ApplicationTrackerTool` (deadline management)
- `ComplianceCheckerTool` (reporting requirements)
- `CarbonCreditTool` (eligibility assessment)

**APIs:**
- Grants.gov API (US)
- Innovate UK API
- EU Funding & Tenders Portal API
- DST India API (patent subsidies)

**Fires finding to Chief of Staff when:**
- Grant match score >80% (high priority apply)
- Application deadline within 30 days
- Reporting deadline approaching
- New grant program launched (sector-specific)

---

### Tier 2H: Jurisdiction Agent (NEW v4.1)

**Role:** Guides global expansion. Ensures compliance and optimization in every new market.

**What it does:**
- Entity formation recommendation (Delaware C-Corp, UK Ltd, Singapore Pte)
- Tax residency optimization
- Permanent establishment risk assessment
- Local compliance requirements (labor, tax, corporate)
- Banking recommendations (Mercury, Brex, Wise Business)
- Payroll provider recommendations (Deel, Remote, Local)
- Data localization requirements (GDPR, PDPA)
- IP protection strategy by jurisdiction

**Tools:**
- `EntityFormationTool` (jurisdiction comparison)
- `TaxResidencyTool` (optimization analysis)
- `PERiskTool` (permanent establishment)
- `ComplianceMatrixTool` (by country)
- `BankingAdvisorTool` (recommendations)

**APIs:**
- Stripe Atlas API (entity formation)
- Deel API (global payroll)
- Wise Business API (international banking)
- Local compliance databases (scraped)

**Fires finding to Chief of Staff when:**
- Expansion signal detected (hiring, revenue in new country)
- Permanent establishment risk triggered
- Data localization violation risk
- Better jurisdiction structure available

---

### Tier 3A: Finance Ops Agent

**Role:** Does the actual finance work. Not analysis — execution.

**What it EXECUTES (not advises):**
- Expense categorization (auto, every transaction)
- Invoice generation from deal data
- Payment reminder drafts (sends with approval)
- Monthly P&L narrative (draft for review)
- GST/VAT return data preparation (ready to file)
- Accounts receivable aging report + follow-up
- Vendor payment schedule optimization
- Reconciliation of bank vs books

**Tools:**
- `InvoiceGeneratorTool` (PDF generation)
- `ReconciliationTool` (bank vs accounting)
- `EmailDraftTool` (payment reminders)
- `GSTPreparationTool` (Indian tax calculations)
- `VATPreparationTool` (UK/EU tax calculations)
- `ExpenseCategorizerTool` (ML classification)
- `AccountingWriteTool` (QuickBooks/Xero API write access)

**HITL Gates:**
- **LOW RISK** → auto-execute: Categorize expense, update books
- **MEDIUM** → 1-tap approve: "Send this payment reminder to Client X?"
- **HIGH** → explicit confirm: "GST return ready: ₹23,400 payable. Confirm?"

---

### Tier 3B: Accounting Ops Agent (NEW v4.1)

**Role:** Handles the accounting close process. Month-end, quarter-end, year-end automation.

**What it EXECUTES:**
- Month-end close checklist execution
- Accrual calculations (expenses, revenue)
- Depreciation schedules
- Prepaid expense amortization
- Intercompany reconciliation (multi-entity)
- Consolidated financial statements
- Audit prep workpapers
- Fixed asset register maintenance
- Chart of accounts hygiene

**Tools:**
- `CloseChecklistTool` (month-end, quarter-end)
- `AccrualCalculatorTool` (auto-accruals)
- `DepreciationTool` (straight-line, declining)
- `ConsolidationTool` (multi-entity)
- `AuditPrepTool` (workpaper generation)

**APIs:**
- QuickBooks Online API
- Xero API
- Google Sheets API (workpapers)
- DocuSign API (audit confirmations)

---

### Tier 3C: HR Ops Agent

**Role:** Handles the people operations that startups consistently neglect until it becomes a crisis.

**What it EXECUTES:**
- Onboarding checklist execution for new hires
- Offer letter generation (templated, customizable)
- Leave tracking and balance calculation
- Payroll data preparation (hours, deductions)
- PF/ESIC registration and filing reminders (India)
- Pension auto-enrollment (UK)
- Performance review scheduling + reminder
- Exit process checklist management
- Policy document generation + versioning
- Employment contract generation

**Tools:**
- `DocumentGeneratorTool` (offer letters, contracts)
- `PayrollDataTool` (Razorpay Payroll / Keka / Gusto API)
- `OnboardingChecklistTool` (Linear/Notion tasks)
- `ComplianceTool` (PF, ESIC, PT, pension calculations)
- `CalendarTool` (Google Calendar — schedule reviews)
- `NotionWriteTool` (update HR docs)

**APIs:**
- Razorpay Payroll API (India)
- Gusto API (US)
- Keka HR API / Darwinbox API (India)
- Notion API (document store)
- Google Calendar API
- DigiLocker API (document verification, India)

---

### Tier 3D: Legal Ops Agent

**Role:** Handles routine legal operations. Does NOT give legal advice. Handles the administrative work around legal.

**What it EXECUTES:**
- NDA generation (standard templates)
- Service agreement drafts (from deal context)
- Contract review summary (plain language)
- Vendor agreement tracking
- MCA annual filing reminders and data prep (India)
- Companies House filing (UK)
- DPDP Act / GDPR compliance checklist
- IP filing deadline tracking
- Term sheet summary and comparison

**Tools:**
- `ContractDraftTool` (template engine + LLM)
- `DocumentSummaryTool` (Azure DI + LLM)
- `ComplianceChecklistTool` (DPDP, GDPR, MCA)
- `ESignTool` (Leegality / Digio / DocuSign API)
- `DeadlineTrackerTool`

**APIs:**
- Leegality API (eSign, India)
- Digio API (KYC + eSign, India)
- DocuSign API (global)
- Azure Document Intelligence
- MCA portal (scrape, India)
- Companies House API (UK)

---

### Tier 3E: RevOps Agent

**Role:** Handles the revenue operations layer — the bridge between sales activity and financial outcomes.

**What it EXECUTES:**
- CRM hygiene (auto-update stale deals)
- Pipeline velocity tracking + stall detection
- Follow-up sequence execution
- Proposal / quote generation from deal data
- Win/loss pattern analysis
- Revenue forecast from pipeline data
- Customer health scoring (churn prediction)
- Renewal reminders for subscription customers

**Tools:**
- `CRMReadWriteTool` (HubSpot API)
- `PipelineAnalysisTool`
- `EmailSequenceTool` (follow-up drafts)
- `ProposalGeneratorTool`
- `ForecastingTool`

**APIs:**
- HubSpot CRM API
- Razorpay / Stripe subscription API
- Google Workspace (Gmail API — send follow-ups)
- Notion API (deal notes)

---

### Tier 3F: Admin Ops Agent

**Role:** All the miscellaneous operational tasks that fall through the cracks because they're too small for anyone to own.

**What it EXECUTES:**
- Meeting prep: pulls context, agenda, action items
- Action item extraction from meeting notes
- SOP documentation from observed workflows
- Tool stack audit (what you're paying for, usage)
- Subscription management (renewals, unused tools)
- Vendor quote comparison
- Travel and expense pre-approval workflow
- Internal announcement drafts

**Tools:**
- `CalendarTool` (Google Calendar)
- `MeetingNotesTool` (Otter.ai / Fireflies API)
- `NotionWriteTool`
- `SubscriptionTrackerTool` (bank statement parse)
- `EmailDraftTool`

**APIs:**
- Google Calendar API
- Fireflies.ai API / Otter.ai API
- Notion API
- Gmail API

---

### Tier 3G: Procurement Ops Agent (NEW v4.1)

**Role:** Manages vendor relationships and procurement. Ensures best terms, tracks renewals, prevents overspending.

**What it EXECUTES:**
- Vendor quote comparison (apples-to-apples)
- Contract renewal tracking (90-day warning)
- Spend analysis by category
- Negotiation prep (market benchmarks)
- Purchase order generation
- Vendor onboarding checklist
- SLA compliance monitoring
- Vendor risk assessment

**Tools:**
- `QuoteComparisonTool` (normalized comparison)
- `RenewalTrackerTool` (contract dates)
- `SpendAnalyzerTool` (category analysis)
- `NegotiationPrepTool` (benchmarks)
- `POGeneratorTool` (purchase orders)

**APIs:**
- Vendor portals (scraped)
- Email API (vendor communication)
- Accounting API (spend data)

---

### Tier 3H: Cap Table Ops Agent (NEW v4.1)

**Role:** Manages the cap table. Tracks ownership, option pools, dilution scenarios.

**What it EXECUTES:**
- Cap table maintenance (post-money updates)
- Option pool tracking (grants, vesting, exercises)
- 409A valuation tracking (US)
- Dilution scenario modeling
- SAFE/convertible note tracking
- Vesting schedule monitoring
- Exit waterfall analysis
- Investor reporting (ownership summaries)

**Tools:**
- `CapTableManagerTool` (ownership tracking)
- `OptionPoolTool` (grants, vesting)
- `DilutionModelerTool` (scenario analysis)
- `SAFETrackerTool` (convertible instruments)
- `WaterfallTool` (exit analysis)

**APIs:**
- Carta API (cap table management)
- AngelList API (investor data)
- Google Sheets API (reporting)

---

### Tier 3I: Grant Ops Agent (NEW v4.1)

**Role:** Executes grant applications. Manages reporting compliance.

**What it EXECUTES:**
- Grant application drafting (from company context)
- Supporting document collection
- Application submission tracking
- Milestone tracking (post-award)
- Reporting compliance (quarterly, annual)
- Fund utilization tracking
- Audit trail maintenance

**Tools:**
- `GrantApplicationTool` (drafting)
- `DocumentCollectorTool` (supporting docs)
- `MilestoneTrackerTool` (post-award)
- `ReportingTool` (compliance reports)
- `FundTrackerTool` (utilization)

**APIs:**
- Grants.gov API
- Innovate UK API
- EU Funding Portal API
- Email API (submission confirmations)

---

### Tier 4: Data + Memory Layer (Invisible)

**IngestionAgent:**
- Normalizes all data sources to standard schema
- Bank PDF, accounting export, Notion page, Slack msg, Stripe webhook, HubSpot change, file upload

**MemoryAgent (Qdrant + Neo4j + Graphiti):**
- Manages Qdrant — the company's long-term brain (vector search)
- Manages Neo4j with Graphiti — temporal knowledge graph (event relationships)
- Company context, goals, decisions, patterns
- Conflict detection, staleness management
- Confidence scoring on all stored memory
- Event sourcing: every fact has a timestamp + source

**CrawlerAgent:**
- Runs Crawl4AI (Docker) + Firecrawl for all external intelligence gathering
- Scheduled crawls (competitors, regulatory, news)
- On-demand deep crawl when signal detected

**ConnectorAgent:**
- Manages OAuth + API connections to all tools
- Health checks, token refresh, sync scheduling
- Error handling, fallback to polling if webhook fails

---

## The Self-Correcting Context-Aware System

**Self-correction loop:**

1. **AGENT ACTS** → Finance Ops Agent sends payment reminder to Client X
2. **OUTCOME OBSERVED** → Client X pays within 24 hours
3. **MEMORY UPDATED** → "Client X responds to payment reminders within 24 hours. High relationship quality." (Qdrant + Neo4j)
4. **FUTURE BEHAVIOR ADJUSTED** → Next time: warmer tone with Client X, less formal follow-up timing
5. **CONTEXT DRIFT DETECTED** → Chief of Staff notices: "You've raised prices twice this quarter but win rate is unchanged. Your pricing model may have headroom."

**The system gets smarter about THIS SPECIFIC COMPANY over time. Not generic AI. Company-specific intelligence.**

---

## v4.1 Scope (What to Build)

### v4.1 Agents (Complete Stack)

**Tier 0:**
- BusinessOSWorkflow (Go + Temporal + Graphiti)

**Tier 1:**
- Chief of Staff Agent (LangGraph + DSPy-compiled ToneFilter)

**Tier 2:**
- CFO Agent
- BI Agent
- Risk & Compliance Agent (multi-jurisdiction)
- Market Intelligence Agent
- Fundraise Readiness Agent (NEW)
- Tax Intelligence Agent (NEW)
- Grant & Credit Agent (NEW)
- Jurisdiction Agent (NEW)

**Tier 3:**
- Finance Ops Agent
- Accounting Ops Agent (NEW)
- HR Ops Agent
- Legal Ops Agent
- RevOps Agent
- Admin Ops Agent
- Procurement Ops Agent (NEW)
- Cap Table Ops Agent (NEW)
- Grant Ops Agent (NEW)

**Tier 4:**
- Ingestion Agent
- Memory Agent (Qdrant + Neo4j + Graphiti)
- Crawler Agent
- Connector Agent

### v4.1 Integrations (data in)

- Razorpay webhook (revenue signals)
- Stripe webhook (global)
- QuickBooks Online API (accounting data)
- Xero API (UK/EU)
- Google Sheets (financial tracking)
- Bank statement PDF upload (Docling parse)
- HubSpot CRM API
- Telegram Bot API (primary interface)

### v4.1 Output

- Telegram (primary) — inline keyboards, HITL gates
- WhatsApp Business API (secondary)
- Email (formal reports)

### v4.1 Proof of Value

What a founder can say after Phase 5:

> "Sarthi saved me 18 hours this week:
> - Prepared my GST + VAT filing data automatically (India + UK)
> - Sent payment reminders to 5 overdue clients
> - Told me my runway dropped from 9 to 7 months and showed me exactly why
> - Drafted the offer letter for my new UK hire (compliant with UK law)
> - Found an R&D tax credit I didn't know about (£35k value)
> - Applied to an Innovate UK grant on my behalf"

**That's not a feature list. That's a Wednesday.**

---

## Technical Architecture

### Mapping to Existing Codebase

| IterateSwarm | Sarthi OS |
|--------------|-----------|
| `Supervisor Agent` | Chief of Staff Agent |
| `Researcher Agent` | Market Intelligence Agent |
| `SRE Agent` | Risk & Compliance Agent |
| `SWE Agent` | Finance Ops / HR Ops Agent |
| `Reviewer Agent` | Legal Ops Agent |
| Temporal Go workflow | `BusinessOSWorkflow` |
| Redpanda topics | `sarthi.ops.events`, `sarthi.intelligence`, `sarthi.actions` |
| Qdrant + Neo4j + Graphiti | Company Knowledge Graph (vector + temporal) |
| PostgreSQL + sqlc | New business schema |
| Go Fiber API | Webhook hub (Telegram, WhatsApp, all SaaS tools) |
| Circuit breaker / retry | Unchanged, directly reused |
| htmx dashboard | Founder ops dashboard + audit trail |

### Testing Architecture

**Multi-layer testing strategy:**

| Layer | Tool | Purpose |
|-------|------|---------|
| **E2E Orchestration** | pytest-asyncio | Async test runner |
| **Agent Graphs** | LangGraph | State machine enforcement |
| **Structured I/O** | Pydantic v2 | Type contracts at boundaries |
| **Prompt Optimization** | DSPy | Auto-optimize prompts with training examples |
| **LLM** | Azure OpenAI (gpt-4o-mini, gpt-4) | Real inference (no mocks) |
| **Workflow** | Temporal Docker | Durable execution |
| **Memory** | Qdrant + Neo4j + Graphiti | Vector + temporal knowledge graph |
| **DB** | PostgreSQL + sqlc | State |

**Test Categories:**
1. **Infrastructure Health** (6 tests) — Azure LLM, Qdrant, Neo4j, PostgreSQL reachable
2. **Memory Agent** (15 tests) — Embeddings, Qdrant upsert, Neo4j graph, semantic search, isolation
3. **Chief of Staff** (5 tests) — Plain language, correct routing, ToneFilter fidelity
4. **Bank Parser** (8 tests) — HDFC/ICICI/SBI CSV, Docling accurate mode, multi-format
5. **CFO Agent** (5 tests) — Runway calculation, proactive alert, scenario modeling
6. **Tier 2 Agents** (40 tests) — BI, Risk, Market, Fundraise, Tax, Grant, Jurisdiction
7. **Tier 3 Agents** (45 tests) — Finance, Accounting, HR, Legal, RevOps, Admin, Procurement, Cap Table, Grant Ops
8. **E2E Flows** (20 tests) — Full stack: onboarding, reflection, market signal, sandbox, calibration
9. **LLM Evals** (15 evals) — LLM-as-judge for tone, jargon, actionability

**Test Status Target:** 151+ tests passing

**v4.1.0 Status:** v4.1.0-alpha — Global expansion, Neo4j + Graphiti locked in.

See [`docs/TESTING_ARCHITECTURE.md`](./TESTING_ARCHITECTURE.md) for complete testing docs.

### Infrastructure Stack ($0/month)

| Layer | Tool | Cost |
|-------|------|------|
| **Interface** | Telegram Bot API | $0 forever |
| **LLM** | Azure OpenAI (existing) | $0 (existing credits) |
| **Orchestration** | Temporal (self-hosted) | $0 |
| **Message Queue** | Redpanda (self-hosted) | $0 |
| **Databases** | PostgreSQL + Qdrant + Neo4j (Docker) | $0 |
| **Graph** | Graphiti (Neo4j plugin) | $0 OSS |
| **Accounting** | QuickBooks Online Sandbox | $0 (dev forever) |
| **Bank Parsing** | Docling + pdfplumber (OSS) | $0 |
| **Document Processing** | Azure DI (500 pages/mo free) | $0 |
| **Market Crawling** | Crawl4AI (Docker, OSS) | $0 |
| **Payments** | Razorpay/Stripe (2% per txn, post-revenue) | $0 setup |
| **Observability** | Langfuse (optional, Cloud free tier) | $0 |

**Total monthly cost for MVP: $0**

---

## Success Metrics

### Week 4 (v4.0.0 Launch)

- ✅ 4 agents operational (Chief of Staff, CFO, Finance Ops, Risk)
- ✅ 3 integrations live (Razorpay, QuickBooks, Google Sheets)
- ✅ 10+ founders using daily
- ✅ 10+ hours saved per founder per week
- ✅ 106+ tests passing

### Month 3 (v4.1.0)

- ✅ All 17 agents operational
- ✅ 50+ founders using daily (US, UK, EU, India, SEA)
- ✅ 18+ hours saved per founder per week
- ✅ First paying customers ($99–$299/month)
- ✅ 151+ tests passing
- ✅ Jurisdiction agent live for US + UK + EU
- ✅ First non-India founder onboarded

### Month 6 (v4.2.0)

- ✅ 200+ founders using daily
- ✅ 20+ hours saved per founder per week
- ✅ $10k+ MRR
- ✅ Self-correcting system demonstrably smarter about each company over time
- ✅ 200+ tests passing

---

## Phase Execution Order

### PHASE 0: Foundation (COMPLETE)
- ✅ Go core service (Fiber, sqlc, Temporal)
- ✅ Docker infrastructure (PostgreSQL, Qdrant, Neo4j, Temporal, Redpanda)
- ✅ Python AI service (LangGraph, Pydantic, DSPy)
- ✅ Telegram bot integration
- ✅ Basic test infrastructure

### PHASE 1: Core Agents (COMPLETE)
- ✅ Chief of Staff Agent
- ✅ ToneFilter (DSPy-compiled)
- ✅ Memory Agent (Qdrant + Neo4j)
- ✅ Graphiti integration (temporal knowledge graph)
- ✅ Sandbox Service (isolated Python execution)

### PHASE 2: LLM Unification + Graphiti (IN PROGRESS)
- [ ] LLM unification (`get_llm_client` everywhere, OpenAI SDK)
- [ ] Graphiti + Neo4j full integration (temporal events)
- [ ] 125 tests passing target

### PHASE 3: Tier 2 Expansion
- [ ] ToneFilter DSPy-compiled (4 signatures total)
- [ ] Telegram notifier with inline keyboards
- [ ] Go telegram.go webhook + sendDM
- [ ] Pydantic findings schemas (all agents)
- [ ] Ingestion agent
- [ ] Bank statement parser (multi-format)
- [ ] Sandbox service hardening
- [ ] 160 tests passing target

### PHASE 4: Full Intelligence Suite
- [ ] CFO agent (complete)
- [ ] Risk agent + compliance calendar (multi-jurisdiction)
- [ ] BI agent
- [ ] Market intel agent + crawler
- [ ] **Jurisdiction agent** (NEW v4.1)
- [ ] **Fundraise readiness agent** (NEW v4.1)
- [ ] **Tax intelligence agent** (NEW v4.1)
- [ ] **Grant & credit agent** (NEW v4.1)
- [ ] 195 tests passing target

### PHASE 5: Operations Suite + Workflows
- [ ] Finance ops agent
- [ ] **Accounting ops agent** (NEW v4.1)
- [ ] Legal ops agent
- [ ] HR ops agent
- [ ] RevOps agent
- [ ] Admin ops agent
- [ ] **Procurement ops agent** (NEW v4.1)
- [ ] **Cap table ops agent** (NEW v4.1)
- [ ] **Grant ops agent** (NEW v4.1)
- [ ] BusinessOS workflow (Go + Temporal + Graphiti)
- [ ] Onboarding workflow (Go)
- [ ] Weekly checkin workflow (Go)
- [ ] HITL gate E2E test
- [ ] 20/20 E2E tests green

### PHASE 6: Production Hardening
- [ ] DSPy eval suite (15 evals, ≥13/15 pass)
- [ ] Circuit breaker (all external calls)
- [ ] Rate limiter (Telegram, Razorpay, Stripe, etc.)
- [ ] GitHub Actions CI (unit + lint)
- [ ] GitHub Actions E2E (manual trigger)
- [ ] Langfuse traces < 8s p95
- [ ] ≥13/15 LLM evals green

### PHASE 7: v4.0.0 REAL MILESTONE
- [ ] One real founder signs up via Telegram
- [ ] Completes onboarding (< 10 min)
- [ ] Uploads real bank statement
- [ ] Receives real CFO finding
- [ ] Approves one action via Telegram
- [ ] Reports "This saved me time"
- → **TAG v4.0.0**

### PHASE 8: v4.1.0 Global Expansion
- [ ] Jurisdiction agent live for US + UK + EU
- [ ] Grant agent: SBIR, Innovate UK, Horizon Europe
- [ ] Tax intelligence: QSBS, R&D credits
- [ ] Fundraise readiness agent live
- [ ] First non-India founder onboarded
- → **TAG v4.1.0**

---

## Global Expansion Strategy

### Market Entry Order

1. **India** (Home market, regulatory familiarity)
   - GST, TDS, PF, ESIC compliance
   - Razorpay, Zoho Books, Keka integrations
   - DPDP Act compliance

2. **United States** (Largest startup market)
   - Delaware C-Corp formation guidance
   - Sales tax nexus monitoring
   - QSBS, R&D tax credits
   - Stripe, QuickBooks, Gusto integrations
   - SEC compliance (fundraising)

3. **United Kingdom** (Gateway to Europe)
   - UK Ltd formation guidance
   - VAT, Corporation Tax, PAYE compliance
   - Innovate UK grants
   - Xero, Wise Business integrations
   - GDPR (UK) compliance

4. **European Union** (Single market access)
   - EU VAT MOSS
   - Horizon Europe grants
   - GDPR (EU) compliance
   - Stripe, Deel integrations
   - Country-specific: Körperschaftsteuer (DE), IS (FR)

5. **Southeast Asia** (High-growth emerging)
   - Singapore Pte Ltd formation
   - PDPA compliance
   - Local payroll providers
   - Stripe, Xero integrations

### Jurisdiction-Specific Features

| Feature | India | US | UK | EU | SEA |
|---------|-------|----|----|----|----|
| **Tax Compliance** | GST, TDS | Sales tax, 1099 | VAT, PAYE | VAT MOSS | GST (SG) |
| **Grants** | DST, BIRAC | SBIR/STTR | Innovate UK | Horizon Europe | EDB (SG) |
| **Tax Credits** | R&D (limited) | R&D, QSBS | R&D, Patent Box | R&D, Patent Box | PIC+ (SG) |
| **Payroll** | PF, ESIC, PT | 401(k), benefits | Pension auto-enroll | Country-specific | CPF (SG) |
| **Data Privacy** | DPDP Act | CCPA, state laws | UK GDPR | EU GDPR | PDPA |

---

## Definition of Done

**v4.1.0 is done when:**

- [ ] All 17 agents pass 100% of TDD tests
- [ ] Real founder can onboard in <10 minutes (any jurisdiction)
- [ ] Bank statement CSV upload → categorized transactions in <30 seconds
- [ ] Multi-jurisdiction compliance data preparation fully automated
- [ ] Payment reminders sent with 1-tap approval
- [ ] Weekly briefing delivered every Monday 9am
- [ ] Jurisdiction agent recommends optimal structure for US/UK/EU expansion
- [ ] Grant agent identifies and applies to at least one grant
- [ ] Tax intelligence agent identifies at least one tax credit
- [ ] 50+ founders using daily for 2+ weeks
- [ ] NPS score > 50
- [ ] 151+ tests passing

---

**Document Version:** 4.1
**Last Updated:** 2026-03-12
**Status:** ✅ PRODUCTION READY
