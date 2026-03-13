# Sarthi.ai — Canonical PRD v4.2

**Version:** 4.2
**Date:** March 2026
**Status:** Single Source of Truth

---

## 1. The One-Line Definition

```
Sarthi is the internal operations virtual office for Seed to Series A startups.

It does not find you customers.
It makes sure your company doesn't collapse while you do.

13 virtual employees. 6 desks. Zero external-facing work.
Finance. HR. Legal. Internal BI. IT & Tools. Admin.
All of it. Running continuously. In the background.
Delivered as a message — not a login.
```

---

## 2. The One Design Rule

**A virtual employee exists in Sarthi IF AND ONLY IF:**

1. The work happens **INSIDE** the company
2. It is repetitive, predictable, and operationally necessary
3. Missing it causes real pain (money lost, team blocked, founder stressed)
4. It does **NOT** require going outside the platform to generate, acquire, or influence external parties

### What We DO (Internal Ops)

✅ Finance (CFO, bookkeeping, AR/AP, payroll)
✅ HR (onboarding, leave, internal recruiting)
✅ Legal (contracts, compliance)
✅ Internal BI (unit economics, churn signals)
✅ IT & Tools (SaaS audits, cloud spend)
✅ Admin (meeting prep, SOPs, knowledge management)

### What We DO NOT Do (Forever Out of Scope)

❌ RevOps / GTM / CRM outreach
❌ Customer success / support
❌ External market intelligence (competitors, pricing)
❌ Content generation / marketing
❌ Cap table management (too complex)
❌ Tax filing (too jurisdiction-heavy)
❌ Grant applications (external)

**Why this boundary?**

Internal ops is painful enough. We solve that completely. Internal data is structured and controllable. We replace ₹3.5L–₹7.5L/month in admin costs immediately. Enterprise tools ignore Seed startups. Startup tools ignore ops depth. That's our moat.

---

## 3. The Problem

| What a Startup Needs | What They Actually Have |
|---------------------|------------------------|
| CFO | Founder checking a spreadsheet at 11pm |
| Head of HR | Founder copying an offer letter template |
| Legal counsel | Founder ignoring the contract renewal email |
| BI analyst | Founder not knowing what they don't know |
| COO | Founder doing everything manually |

**The result:** 15–20 hours/week of founder time eaten by back-office work that doesn't require their unique judgment. That is ~3 months/year of product and growth time permanently lost.

**The hidden cost:** ₹3.5L–₹7.5L/month in fractional admin services (CFO, bookkeeper, HR coordinator, legal retainer) that startups can't afford but desperately need.

---

## 4. The ICP

### Who Sarthi Is For

| Attribute | Value |
|-----------|-------|
| **Stage** | Pre-seed → Series A |
| **Team size** | 1–25 people |
| **Type** | Product/tech startup (B2B SaaS, D2C, marketplace, fintech, edtech) |
| **Geography** | India (beachhead) → US → UK → EU → SEA |

### What Defines Them

- Tech-literate — they know what an API is
- Already using tools (Notion, Linear, Razorpay, Google Workspace, Zoho Books/QuickBooks)
- Do NOT have dedicated ops/finance/HR/legal hires
- The founder IS the back-office right now

### What They Feel

- "I'm spending all my time on admin, not product"
- "I don't know if my numbers are okay"
- "I almost missed a GST deadline last month"
- "I have to write the same follow-up emails every single week"

### What They Need

- Not the best financial firm
- Not another dashboard
- Someone (something) to hold their hand, handle the grunt work, and tell them the one thing that matters right now

---

## 5. The Interface

### Primary: Telegram Bot

Free, no per-message cost, async, file-capable, inline keyboards for HITL approvals. Works globally.

### What Founders Send Sarthi

- **Text questions:** "What's my runway?"
- **CSV/Excel files:** Bank statement export from net banking
- **PDF files:** Contracts, notices, invoices
- **Photos:** Tax notices, receipts, whiteboards
- **/commands:** `/status` `/runway` `/decisions` `/weekly`

### What Sarthi Sends Founders

- **Proactive alerts** (unprompted, when score > threshold)
- **Task reports:** "Done: sent 3 payment reminders"
- **HITL requests:** "Send this to Raju? [Yes / Edit / No]"
- **Weekly briefing:** Every Monday 9am local time
- **Deadline alerts:** 14-day advance warning on all compliance

---

## 6. The Agent Architecture — 6 Desks, 13 Virtual Employees

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 0 — KERNEL (Go + Temporal + Graphiti)                     │
│  BusinessOSWorkflow: orchestrates all agents, manages state     │
│  enforces HITL gates, temporal knowledge graph                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1 — CHIEF OF STAFF (1 agent)                              │
│  The only agent that talks to the founder.                      │
│  Routes work to 6 desks. Synthesizes intelligence.              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2 — 6 DESKS (13 Virtual Employees)                        │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ Finance     │ │ People      │ │ Legal       │               │
│  │ Desk        │ │ Desk        │ │ Desk        │               │
│  │ • CFO       │ │ • HR Coord  │ │ • Contracts │               │
│  │ • Bookkeeper│ │ • Recruiter │ │ • Compliance│               │
│  │ • AR/AP     │ │             │ │             │               │
│  │ • Payroll   │ │             │ │             │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ Intelligence│ │ IT & Tools  │ │ Admin       │               │
│  │ Desk        │ │ Desk        │ │ Desk        │               │
│  │ • BI Analyst│ │ • IT Admin  │ │ • EA        │               │
│  │ • Policy    │ │             │ │ • Knowledge │               │
│  │  Watcher    │ │             │ │  Manager    │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3 — DATA LAYER (ingest + memory, never surfaces)          │
│  Ingestion | Memory (Qdrant + Neo4j) | Connector                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. The Complete Desk Hierarchy (v4.2)

### Tier 1: Chief of Staff Agent

**Role:** The face of Sarthi. Routes work to 6 desks, synthesizes intelligence, manages the relationship.

**Output:**
- "Here's what I found + one action"
- "I handled X — here's what I did"
- "I need your decision on X — here's context"
- "Weekly briefing: X handled, Y needs you"

**HITL Gate:**
- **LOW RISK** → auto-execute + notify after
- **MEDIUM RISK** → 1-tap Telegram inline keyboard
- **HIGH RISK** → explicit confirm with context

---

### Tier 2: The 6 Desks (13 Virtual Employees)

#### 📊 Finance Desk (4 employees)

**CFO Agent**
- 13-week rolling cash flow forecast
- Burn rate + runway calculation (alert < 90 days)
- Unit economics: CAC, LTV, payback
- Scenario modeling: "what if we hire in March?"
- **Fires when:** Runway < 6 months, burn spikes >15%, margin goes negative

**Bookkeeper Agent**
- Expense categorization (auto)
- Bank vs books reconciliation
- Monthly P&L narrative generation
- GST/VAT return data prep
- **HITL:** Auto-categorize, manual review for uncategorized

**AR/AP Clerk Agent**
- Invoice generation + payment reminders
- Accounts receivable aging report
- Vendor payment timing optimization
- **Fires when:** Invoice >30 days overdue, payment due in 7 days

**Payroll Clerk Agent**
- Payroll data preparation
- PF/ESIC/pension filing reminders
- Salary slip generation
- **Fires when:** Payroll deadline <7 days, new hire onboarded

---

#### 👥 People Desk (2 employees)

**HR Coordinator Agent**
- Onboarding checklist execution
- Offer letter generation (templates)
- Leave balance tracking
- Performance review scheduling
- **Fires when:** New hire start date, leave balance <5 days, review due

**Internal Recruiter Agent**
- Job description drafting
- Interview scheduling coordination
- Candidate communication templates
- Offer letter preparation
- **Fires when:** Requisition approved, interview scheduled

---

#### ⚖️ Legal Desk (2 employees)

**Contracts Coordinator Agent**
- NDA generation (templates)
- Contract review summary (plain language)
- Contract expiry tracking (90-day warning)
- eSign workflow management
- **Fires when:** Contract expires <30 days, new contract needs drafting

**Compliance Tracker Agent**
- GST, TDS, advance tax deadlines (India)
- VAT, Corporation Tax, PAYE (UK)
- PF, ESIC, PT compliance
- DPDP Act / GDPR compliance checklist
- MCA/Companies House filing reminders
- **Fires when:** Deadline <14 days, regulatory change detected

---

#### 📈 Intelligence Desk (2 employees)

**BI Analyst Agent (Internal-Only)**
- Customer cohort analysis (retention, churn)
- Revenue concentration risk (single customer >30%)
- Anomaly detection across all data sources
- Cross-source pattern correlation
- Unit economics tracking
- **Fires when:** Churn pattern detected, one customer >30% revenue, usage predicts churn

**Policy Watcher Agent**
- Regulatory change monitoring (jurisdiction-specific)
- Tax law updates affecting THIS company
- Compliance requirement changes
- **Fires when:** New regulation affects company, deadline changes

---

#### 🖥️ IT & Tools Desk (1 employee)

**IT Admin Agent**
- SaaS subscription audit + optimization
- Cloud spend analysis (AWS/GCP/Azure)
- Tool access provisioning/deprovisioning
- Software license tracking
- Vendor contract renewal tracking
- **Fires when:** Unused subscription detected, renewal due <60 days, spend anomaly

---

#### 📋 Admin Desk (2 employees)

**Executive Assistant Agent**
- Meeting prep (pulls context, agenda)
- Action item extraction from meeting notes
- Internal announcement drafts
- Calendar coordination
- **Fires when:** Meeting scheduled, action items extracted

**Knowledge Manager Agent**
- SOP documentation from observed workflows
- Internal wiki organization
- Process improvement suggestions
- Company handbook maintenance
- **Fires when:** New process observed, SOP outdated >90 days

---

### Tier 3: Data Layer (Invisible)

**Ingestion Agent**
- **CSV/Excel:** pandas + openpyxl (Bank detection: HDFC/ICICI/SBI/Axis/Kotak)
- **PDF (digital):** pdfplumber
- **PDF (scanned):** Docling accurate mode
- **PDF (fallback):** Azure Document Intelligence (500 pages/mo free tier)
- **Photos:** Docling vision mode
- All normalised → standard transaction schema
- PostgreSQL write + Qdrant embed + Neo4j episode

**Memory Agent (Qdrant — semantic)**
- Manages Qdrant collection: `sarthi-founder-memory`
- Embeddings: text-embedding-3-small (1536d)
- Founder isolation enforced at filter level
- Conflict detection on contradicting writes
- Stale memory compression after 90 days
- Pattern detection: archetype classification

**Graph Memory Agent (Neo4j + Graphiti — relational)**
- Temporal knowledge graph via Graphiti (Zep)
- Every reflection, commitment, signal, decision is an episode
- Answers questions Qdrant cannot:
  - "Has this founder broken this commitment 3 weeks running?"
  - "What happened to revenue AFTER missed customer calls?"
  - "Which interventions did this founder respond to?"
- Hybrid search: semantic + graph traversal (RRF)

**Connector Agent**
- Manages OAuth token health for all integrations
- Token refresh, sync schedule
- Falls back to polling if webhook fails
- Alerts CoS if integration goes dark

---

## 8. The Self-Correcting Loop

```
1. Agent acts      (e.g. Bookkeeper categorizes AWS expense)
2. Outcome seen    (Founder confirms category is correct)
3. MemoryAgent writes to Qdrant:
   "AWS expenses: categorized as 'Cloud Infrastructure'"
4. GraphMemoryAgent writes episode to Neo4j:
   Entity: AWS → RELATION: category → Cloud Infrastructure
5. Future: Auto-categorize similar expenses, flag anomalies
6. Context drift:  CoS detects macro pattern across
   all memory and surfaces unprompted:
   "Cloud spend up 40% MoM. New deployment or pricing change?"

The system gets smarter about THIS company specifically.
Not generic AI. Company-specific intelligence that compounds.
```

---

## 9. The Technology Stack

### Infrastructure ($0 — Docker, self-hosted)

| Component | Technology | Port | Purpose |
|-----------|------------|------|---------|
| Workflow engine | Temporal | 7233/8088 | Durable execution |
| Message queue | Redpanda | 19092 | Event bus |
| Primary DB | PostgreSQL | 5432 | State, founders |
| Vector DB | Qdrant | 6333 | Semantic memory |
| Graph DB | Neo4j | 7687 | Relational memory |
| LLM observability | Langfuse | 3001 | Tracing + evals |
| Isolated exec | Sandbox (alpine) | 5001 | CFO charts/math |

### Go Core (`apps/core`)

| Technology | Purpose |
|------------|---------|
| Go 1.24 + Fiber | API gateway, webhook hub |
| Temporal Go SDK | BusinessOSWorkflow definition |
| franz-go | Redpanda producer/consumer |
| sqlc | Type-safe PostgreSQL queries |
| htmx + Go tmpl | Ops dashboard (internal) |
| go-telegram-bot | Telegram webhook + send DM |

### Python AI Worker (`apps/ai`)

| Technology | Purpose |
|------------|---------|
| Python 3.11 + uv | Package management |
| LangGraph | Agent state machines (all tiers) |
| DSPy | Prompt optimization per agent node |
| Pydantic v2 | Output contracts + jargon validator |
| Langfuse SDK | Auto-trace every LangGraph node |
| Temporal Python | Activity worker |
| Qdrant Client | Semantic memory read/write |
| Graphiti (Zep) | Neo4j temporal knowledge graph |
| neo4j | Neo4j Python driver |

### THE ONE SDK RULE — ABSOLUTE

```python
# apps/ai/src/config/llm.py
# THE ONLY FILE WHERE THE LLM CLIENT IS CREATED.
# Every agent imports from here. No exceptions. Ever.

from openai import AzureOpenAI   # ← ALWAYS for Azure. Use factory pattern.

def get_llm_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )

# Provider Configuration:
# Set environment variables:
#   - AZURE_OPENAI_ENDPOINT: https://{resource}.openai.azure.com/
#   - AZURE_OPENAI_KEY: Your Azure OpenAI API key
#   - AZURE_OPENAI_API_VERSION: API version (default: 2024-02-01)
#   - AZURE_OPENAI_CHAT_DEPLOYMENT: Chat model deployment name
#   - EMBEDDING_MODEL: Embedding model name (optional)
```

### Document Processing ($0 OSS)

| Tool | When Used |
|------|-----------|
| pandas + openpyxl | CSV/Excel bank statements |
| pdfplumber | Digital PDFs (text-selectable) |
| Docling (IBM OSS, accurate) | Scanned PDFs (image-based OCR) |
| Azure Document Intelligence | Fallback only (500 pages/mo free) |

### External Integrations (all free for dev)

| Service | API | Cost |
|---------|-----|------|
| Telegram Bot | python-telegram-bot | $0 forever |
| Zoho Books | REST API | $0 free tier |
| QuickBooks Online | Sandbox API | $0 dev |
| Razorpay | Webhooks + API | $0 setup |
| HubSpot CRM | API | $0 free tier |
| Leegality / Digio | eSign API | $0 sandbox |

---

## 10. The Tone Contract

### BANNED IN ALL OUTPUT (every agent, every message)

```
EBITDA, DSO, bps, YoY, MoM, liquidity,
working capital, CAGR, accounts receivable,
burn multiple, runway compression, NWC,
cash conversion cycle, churn cohort delta,
basis points, net margin, gross margin,
accounts payable, amortization, depreciation,
optimize, leverage, synergy, streamline,
actionable insights, KPIs, metrics, data-driven
```

### REQUIRED IN ALL OUTPUT

- Lead with human reality, not the metric
- Max 3 sentences of explanation
- End with exactly ONE action
- Warm, direct — trusted friend, not consultant
- If bad news: acknowledge before data
- If good news: celebrate explicitly first

### Example

**BAD:** "Your EBITDA margin compressed 340bps MoM due to elevated SG&A spend."

**GOOD:** "You kept less money from every rupee you earned this month — costs grew faster than revenue. The main culprit is [specific line]. This week: cut or pause [specific item]."

**Enforced via:**
1. Pydantic validator on every output model
2. DSPy-compiled ToneFilter (compiled weights in git)
3. Langfuse scores every output — <0.7 is flagged

---

## 11. The HITL Gate Model

| Risk Level | Examples | Approval Flow |
|------------|----------|--------------|
| **LOW RISK** (auto-execute + notify after) | Categorize a transaction, Update a record, Log a compliance deadline, Generate a draft document (not yet sent) | Auto |
| **MEDIUM RISK** (1-tap Telegram inline keyboard) | Send a message to a client, Send a payment reminder, Book a meeting, Share a document externally | 1-tap |
| **HIGH RISK** (explicit confirm + reason shown) | File a GST return, Send a legal document, Make a payment, Delete or archive data | Explicit confirm |

**PRINCIPLE:** Powerful but never autonomous where it matters. The founder always controls the wheel. They just don't have to steer on empty roads.

---

## 12. The Data Flow

```
EVENT: Founder sends HDFC CSV to Telegram bot
         │
         ▼
[Go Fiber] TelegramWebhookHandler
  → Validates, authenticates founder
  → Produces to Redpanda: "sarthi.business.events"
         │
         ▼
[Temporal] BusinessOSWorkflow (long-running, never stops)
  → Classifies event: "bank_statement_upload"
  → Spawns: IngestionAgent
         │
         ├──▶ IngestionAgent: detects HDFC format
         │    → pandas normalize → standard schema
         │    → PostgreSQL write (transactions table)
         │    → Qdrant upsert (memory + embedding)
         │    → Neo4j episode via Graphiti
         │    → Signals: "ingestion_complete"
         │
         ├──▶ Finance Desk agents fire:
         │    BookkeeperAgent.categorize(new_transactions)
         │    CFOAgent.analyze(cash_position)
         │    AR APAgent.check_receivables()
         │
         ├──▶ Each agent → typed Pydantic finding
         │    (validated at output boundary)
         │    (Langfuse traces every node)
         │
         └──▶ ChiefOfStaffAgent receives ALL findings
              → Queries Qdrant: semantic context
              → Queries Neo4j: relational patterns
              → Scores: what to surface right now?
              → ToneFilter: jargon → plain language
              → Drafts ONE Telegram message
              → HITL gate: medium/high risk queued
              → Go activity: send via Telegram Bot API
                         │
                         ▼
              Founder's Telegram:
              "Got your HDFC statement (March 1–15).
               Money in: ₹2,34,000 | Out: ₹1,87,000
               One thing I noticed: AWS costs up ₹23k
               vs last month. Anything new deployed?
               [It's fine] [Let me check]"
```

---

## 13. Pydantic Output Contracts

```python
# apps/ai/src/schemas/findings.py

BANNED_JARGON = {
    "EBITDA","DSO","bps","YoY","MoM","liquidity",
    "working capital","CAGR","accounts receivable",
    "burn multiple","runway compression","NWC",
    "cash conversion cycle","churn cohort delta",
    "basis points","net margin","gross margin",
    "accounts payable","amortization","depreciation",
}

def validate_no_jargon(text: str) -> str:
    for term in BANNED_JARGON:
        if re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
            raise ValueError(f"Jargon violation: '{term}'")
    return text

class HitlRisk(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"

class CFOFinding(BaseModel):
    headline:     str    # max 10 words, plain language
    what_is_true: str    # 2-3 sentences, ₹ amounts, no jargon
    do_this:      str    # exactly ONE action
    urgency:      str    # "today" | "this week" | "this month"
    rupee_impact: Optional[int]
    hitl_risk:    HitlRisk
    trigger_type: str
    is_good_news: bool = False

    @validator("headline", "what_is_true", "do_this")
    def no_jargon(cls, v): return validate_no_jargon(v)

    @validator("do_this")
    def single_action(cls, v):
        if any(c in v for c in ["\n-", "\n•", "\n1.", "\n2."]):
            raise ValueError("do_this must be a single action")
        return v

class BIFinding(BaseModel):
    headline:     str
    pattern:      str
    evidence:     str
    do_this:      str
    hitl_risk:    HitlRisk
    is_good_news: bool = False

class RiskAlert(BaseModel):
    title:       str
    deadline:    str    # "March 28 — 16 days away"
    consequence: str    # plain language: "₹X penalty if missed"
    do_this:     str
    days_until:  int
    hitl_risk:   HitlRisk = HitlRisk.HIGH

class FinanceFinding(BaseModel):
    category:      str
    amount:        float
    anomaly:       bool
    do_this:       Optional[str]
    hitl_risk:     HitlRisk = HitlRisk.LOW

class HRFinding(BaseModel):
    action_type:   str    # "onboarding" | "leave" | "payroll"
    employee:      str
    deadline:      Optional[str]
    do_this:       str
    hitl_risk:     HitlRisk

class LegalFinding(BaseModel):
    document_type: str
    deadline:      Optional[str]
    risk_level:    str    # "low" | "medium" | "high"
    do_this:       str
    hitl_risk:     HitlRisk

class ITFinding(BaseModel):
    category:      str    # "unused_subscription" | "renewal" | "spike"
    vendor:        str
    amount:        Optional[float]
    do_this:       str
    hitl_risk:     HitlRisk
```

---

## 14. Testing Architecture

**PRINCIPLE:** Real Docker. Real LLM. No mocks. Always.

| Layer | Tool | What Is Tested |
|-------|------|---------------|
| **Infra** | conftest.py poison pill | All 12 Docker containers reachable before any test. LLM confirmed live. Mock patches on LLM BLOCKED |
| **Agent graphs** | LangGraph + pytest-asyncio | Graph completes all nodes. State transitions valid. Error nodes reachable |
| **Output contracts** | Pydantic v2 | Every finding typed. Jargon validator fires. Structure enforced at boundary |
| **Prompt quality** | DSPy + BootstrapFewShot + compiled JSON | Score ≥ 0.7 on holdout examples. CFO runway within ±15 days. ToneFilter jargon-free |
| **Observability** | Langfuse self-hosted | Every LangGraph node traced. Scores logged per run. Trace visible in UI |
| **E2E flows** | Full stack | Telegram → Go → Redpanda → Temporal → Python agent → Pydantic output → Langfuse trace → Telegram delivery |

### Test Count Targets

| Suite | Tests | Type |
|-------|-------|------|
| Infrastructure health | 6 | Docker + LLM connectivity |
| Memory agent (Qdrant) | 10 | write/read/isolation |
| Graph memory agent (Neo4j) | 12 | episodes/search/patterns |
| Chief of Staff | 8 | routing + tone |
| Bank parser | 8 | HDFC/ICICI/SBI/scanned PDF |
| Finance Desk (4 agents) | 25 | LangGraph E2E + Pydantic |
| People Desk (2 agents) | 12 | onboarding + HR flows |
| Legal Desk (2 agents) | 12 | contracts + compliance |
| Intelligence Desk (2 agents) | 15 | BI + policy watching |
| IT & Tools Desk (1 agent) | 10 | SaaS audit + spend |
| Admin Desk (2 agents) | 12 | EA + knowledge mgmt |
| Tone filter | 14 | jargon + DSPy + Hindi |
| Sandbox client | 10 | isolated exec + charts |
| E2E flows | 20 | full stack Telegram → output |
| LLM evals (DSPy) | 15 | scoring + LLM-as-judge |
| **Total** | **~189** | **Real LLM, real Docker** |

---

## 15. Infrastructure — All Containers

```yaml
# docker-compose.yml — 12 containers total
services:
  # Core Infrastructure
  temporal:          # Workflow orchestration
  postgres:          # Primary database
  redpanda:          # Event streaming
  
  # Memory Layer
  qdrant:            # Vector embeddings
  neo4j:             # Knowledge graph
  
  # Observability
  langfuse:          # LLM tracing
  
  # Application
  sarthi-core:       # Go service (Fiber + Temporal worker)
  sarthi-ai:         # Python AI worker (LangGraph agents)
  
  # Utilities
  sandbox:           # Isolated code execution
```

---

## 16. ROI & Pricing

### What Sarthi Replaces

| Role | Fractional Cost (₹/month) | Sarthi Desk |
|------|--------------------------|-------------|
| Fractional CFO | ₹75,000–₹1,50,000 | Finance Desk |
| Bookkeeper | ₹25,000–₹40,000 | Finance Desk |
| HR Coordinator | ₹30,000–₹50,000 | People Desk |
| Legal Retainer | ₹50,000–₹1,00,000 | Legal Desk |
| EA/Admin | ₹20,000–₹35,000 | Admin Desk |
| **Total** | **₹2,00,000–₹3,75,000** | **6 Desks** |

### Sarthi Pricing

| Tier | Price (₹/month) | Desks Included |
|------|-----------------|----------------|
| Starter | ₹5,000 | Finance + Admin |
| Growth | ₹10,000 | All 6 Desks |
| Scale | ₹15,000 | All 6 Desks + Priority |

**ROI:** 20x–50x return. Replace ₹3.5L–₹7.5L/month in fractional admin costs with ₹5K–₹15K/month.

### The Moat

After 6 months with a founder:
- We know their approval patterns
- We know their vendor relationships
- We know their team dynamics
- We have institutional memory in Neo4j

A competitor starting fresh cannot replicate this.

---

## 17. v4.2 Roadmap

### Phase 1 (IN PROGRESS)
- [ ] LLM unification (`get_llm_client` everywhere)
- [ ] Graphiti + Neo4j full integration
- [ ] 125 tests passing

### Phase 2
- [ ] Finance Desk (CFO + Bookkeeper + AR/AP + Payroll)
- [ ] People Desk (HR + Internal Recruiter)
- [ ] Legal Desk (Contracts + Compliance)
- [ ] 150 tests passing

### Phase 3
- [ ] Intelligence Desk (BI + Policy Watcher)
- [ ] IT & Tools Desk (IT Admin)
- [ ] Admin Desk (EA + Knowledge Manager)
- [ ] 175 tests passing

### Phase 4
- [ ] Chief of Staff routing (internal-only)
- [ ] BusinessOS workflow (Go + Temporal)
- [ ] HITL gate E2E test
- [ ] 20/20 E2E tests green

### Phase 5: v4.2.0
- [ ] One real founder onboards
- [ ] Uses at least 2 desks
- [ ] Reports "This saved me admin time"
- → **TAG v4.2.0**

---

## 18. Documentation

| Doc | Purpose |
|-----|---------|
| [PRD](./PRD.md) | Complete product requirements, agent specs (v4.2) |
| [INTERNAL_OPS_SCOPE](./INTERNAL_OPS_SCOPE.md) | What we do / don't do boundary |
| [TESTING](./TESTING_ARCHITECTURE.md) | Testing strategy, ~189 test targets |
| [Architecture](./architecture/) | System design, data flow |
| [API Docs](./api/) | All endpoints, request/response schemas |

---

**Last Updated:** 2026-03-13
**Version:** 4.2.0-alpha — Internal Ops Virtual Office Only
