Here are all four documents.

------

# SARTHI V2.0 — PRODUCT REQUIREMENTS DOCUMENT

```
textVersion:  2.0 (Final)
Date:     April 12, 2026
Status:   Approved for Build
ICP:      Solo technical SaaS founder, seed stage, 6–18 months to Series A
Stack:    Python · Go · LangGraph · Temporal · Qdrant · PostgreSQL · Slack
```

------

## 1. Product Truth

Sarthi is a **guardian**, not an assistant.

Every tool ever built for founders operates in the known-knowns quadrant — they answer questions the founder already knows to ask. A first-time solo technical founder doesn't know what they don't know. They don't know that 3% monthly churn is fatal at Series A. They don't know that their AWS costs growing faster than their users is a structural unit economics problem. They don't know that inconsistent investor updates signal operational discipline problems to the next investor.

**An assistant waits to be asked. A guardian knows to watch before you know to look.**

Sarthi watches continuously, detects patterns from a curated watchlist of seed-stage failure modes, and surfaces insights the founder could not have surfaced themselves — before those patterns become crises.

**Core tagline:** *"First-time founders don't know what they don't know. Sarthi does."*

------

## 2. ICP — Locked

> **Sarthi V1 is for the solo technical founder building a SaaS product on Stripe + Postgres, at seed stage, who is 6–18 months from their first institutional raise — and who doesn't yet know what's about to go wrong.**

| Qualifier            | Why It Matters                                               |
| -------------------- | ------------------------------------------------------------ |
| Solo                 | No delegation buffer — every alert hits the decision-maker directly |
| Technical            | Can self-serve onboarding; no CS layer required              |
| SaaS                 | Instrumentation already exists (Stripe, DB, Sentry)          |
| Seed stage           | Failure patterns are well-documented and watchlist-able      |
| 6–18 months to raise | Urgency horizons are calculable and meaningful               |

**Explicitly out of V1:**

- D2C / ecommerce founders
- Agency / services founders
- Non-technical SaaS founders
- Mobile-first app founders (Firebase/Amplitude schema variance)
- Pre-product founders (nothing to watch)
- Multi-founder teams > 2

------

## 3. V1.0 → V2.0 Delta

**V1.0 complete (119 tests passing):**

- 4 agents: Pulse, Anomaly, Investor, QA
- 3 Temporal workflows + 5 activities
- Qdrant memory: 3 collections (768-dim)
- DSPy prompts: examples + signatures
- Integrations: Stripe, Plaid, ProductDB, Slack

**V2.0 adds:**

- Guardian watchlist (16 seed-stage failure patterns)
- 5-layer memory spine: Redis → Qdrant Episodic → Kuzu Semantic → PG Procedural → Qdrant Compressed
- RAG kernel (≤800 token context assembly)
- 3-tier HITL system
- LLMOps: Langfuse tracing wrapper + weekly eval loop + agent self-analysis
- 4 new Temporal workflows
- Guardian tone baked into every DSPy signature

------

## 4. Data Contract — Fixed for V1

**Required (minimum viable guardian):**

```
textStripe      → MRR, churn events, new customers, failed payments,
              plan distribution, customer concentration
PostgreSQL  → users, sessions/events, feature_usage, cohorts
              (founder-supplied, read-only)
```

**Optional (upgrades guardian quality):**

```
textPlaid / Mercury  → bank balance, burn calculation
Sentry           → error rate, user segment correlation
IterateSwarm     → classified feedback, severity distribution
```

**Out of V1 data contract (closed):**
Firebase, Amplitude, Mixpanel, Segment, Intercom events, HubSpot, QuickBooks, MySQL, anything requiring custom schema mapping.

------

## 5. The Guardian Watchlist — V1 Complete

## Finance Guardian

| ID    | Pattern                           | Trigger                                 |
| ----- | --------------------------------- | --------------------------------------- |
| FG-01 | `silent_churn_death`              | Monthly churn > 3% (→ 36% annual)       |
| FG-02 | `burn_multiple_creep`             | Net burn / new ARR > 2.0x               |
| FG-03 | `customer_concentration_risk`     | Top customer > 30% of MRR               |
| FG-04 | `runway_compression_acceleration` | Burn growing faster than runway shrinks |
| FG-05 | `failed_payment_cluster`          | 3+ failed payments in 7 days            |
| FG-06 | `payroll_revenue_ratio_breach`    | Payroll > 60% of revenue                |

## BI Guardian

| ID    | Pattern                             | Trigger                                         |
| ----- | ----------------------------------- | ----------------------------------------------- |
| BG-01 | `leaky_bucket_activation`           | Signups growing, activation flat or falling     |
| BG-02 | `power_user_mrr_masking`            | Top 10% users hiding declining avg MRR/customer |
| BG-03 | `feature_adoption_post_deploy_drop` | Feature usage drops after deploy                |
| BG-04 | `cohort_retention_degradation`      | New cohorts retaining 10%+ worse than prior     |
| BG-05 | `nrr_below_100_seed`                | NRR < 100% (losing more than expanding)         |
| BG-06 | `trial_activation_wall`             | Users abandoning at same step repeatedly        |

## Ops Guardian

| ID    | Pattern                                    | Trigger                                   |
| ----- | ------------------------------------------ | ----------------------------------------- |
| OG-01 | `error_rate_user_segment_correlation`      | Errors concentrated in one user segment   |
| OG-02 | `support_volume_outpacing_growth`          | Support tickets growing faster than users |
| OG-03 | `cross_channel_bug_convergence`            | Same bug in 3+ channels simultaneously    |
| OG-04 | `deploy_frequency_collapse`                | Deploy frequency drops >50% MoM           |
| OG-05 | `infrastructure_unit_economics_divergence` | AWS cost growth > 2x user growth          |

------

## 6. Guardian Message Protocol

Every alert must follow this structure. No exceptions.

```
text1. PATTERN NAME (not metric name)
2. The number — injected, never LLM-generated
3. What it implies at scale / at Series A
4. What the founder doesn't know yet
5. Urgency horizon (specific to 6–18 month raise timeline)
6. What typically happens to founders who miss this
7. ONE concrete action this week

Max 200 words. Starts with pattern. Ends with action.
Sounds like a trusted colleague who has seen this before.
Never sounds like a notification. Never starts with a number.
```

**The difference:**

```
textNOTIFICATION (wrong):
  "⚠️ Monthly churn is 3.2%. Above warning threshold."

GUARDIAN INSIGHT (correct):
  "Silent Churn Death — your monthly churn is 3.2%.
  That sounds manageable. It isn't. At this rate, you'll
  replace your entire customer base every 26 months. When
  you walk into a Series A pitch in 8 months, the first
  question will be annual churn. You won't have a good answer.

  Most founders who hit this had a pricing or ICP fit problem
  they didn't see until month 14. You're at month 6. The root
  cause is still fixable.

  This week: call one churned customer. Don't ask what went
  wrong. Ask what they expected the product to do that it didn't."
```

------

## 7. Onboarding Success Metric — Revised

**Old metric:** Stripe connected → first brief in 10 minutes.

**Correct metric:** Founder acknowledged an insight they didn't already know within 48 hours of setup.

**New DB columns:**

```
sqlALTER TABLE agent_alerts ADD COLUMN insight_acknowledged BOOLEAN DEFAULT FALSE;
ALTER TABLE agent_alerts ADD COLUMN insight_already_knew BOOLEAN DEFAULT FALSE;
ALTER TABLE agent_alerts ADD COLUMN insight_not_relevant BOOLEAN DEFAULT FALSE;
```

The first alert must come from the watchlist, not a healthy-state pulse. If the first alert is "your runway is X days" and the founder already knew that — Sarthi failed its first test.

------

## 8. Pricing

| Tier         | Price          | Seats   | Features                                           |
| ------------ | -------------- | ------- | -------------------------------------------------- |
| Beta         | Free (60 days) | 1       | All 3 guardian agents, all alerts, investor update |
| Solo Founder | $79/month      | 1       | Full guardian, all watchlist, weekly eval          |
| Seed Team    | $199/month     | Up to 5 | Above + custom thresholds, team channels           |

Beta → Paid conversion offer at Day 45.

------

## 9. Open Questions (Resolved)

1. **Neo4j vs Kuzu** → Kuzu. Embedded, no container, same Cypher syntax.
2. **OpenRouter vs fine-tuned Qwen3** → OpenRouter GPT-4o-mini for beta. Swap Phase 2.
3. **Single vs multi-tenant Qdrant** → tenant_id in all payloads from Day 1.
4. **Minimum onboarding for first alert** → Stripe only. Everything else optional.
5. **Slack vs WhatsApp** → Slack only for V1.

------

------

# SARTHI V2.0 — HIGH-LEVEL DESIGN

------

## System Architecture

```
text┌─────────────────────────────────────────────────────────────────┐
│                    SARTHI V2.0 PLATFORM                         │
│                                                                 │
│  EXTERNAL DATA SOURCES                                          │
│  Stripe API · Plaid/Mercury · PostgreSQL · Sentry · IterateSwarm│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  GO API GATEWAY (Fiber)                                 │   │
│  │  Webhook ingestion · OAuth callbacks · Health checks    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                    REDPANDA EVENT BUS                           │
│            stripe.events · sentry.events · ops.events          │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  TEMPORAL ORCHESTRATOR                                  │   │
│  │  FinanceMonitorWorkflow  (every 6h)                     │   │
│  │  BIPulseWorkflow         (daily 8am)                    │   │
│  │  OpsWatchWorkflow        (every 4h)                     │   │
│  │  InvestorUpdateWorkflow  (Monday 7am)                   │   │
│  │  WeeklyBusinessPulse     (Monday 7:05am)                │   │
│  │  SelfAnalysisWorkflow    (weekly)           [NEW]       │   │
│  │  EvalLoopWorkflow        (weekly)           [NEW]       │   │
│  │  CompressionWorkflow     (trigger-based)    [NEW]       │   │
│  │  WeightDecayWorkflow     (weekly)           [NEW]       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PYTHON AI WORKER (FastAPI + LangGraph)                 │   │
│  │                                                         │   │
│  │  GUARDIAN AGENTS                                        │   │
│  │  Finance Guardian · BI Guardian · Ops Guardian          │   │
│  │                                                         │   │
│  │  GUARDIAN WATCHLIST (16 seed-stage failure patterns)    │   │
│  │                                                         │   │
│  │  5-LAYER MEMORY SPINE                                   │   │
│  │  L1 Redis (working) → L2 Qdrant (episodic)             │   │
│  │  → L3 Kuzu (semantic) → L4 PG (procedural)             │   │
│  │  → L5 Qdrant (compressed)                              │   │
│  │                                                         │   │
│  │  RAG KERNEL (≤800 token context assembly)               │   │
│  │                                                         │   │
│  │  LLMOPS                                                 │   │
│  │  Langfuse tracing · Weekly eval · Self-analysis         │   │
│  │                                                         │   │
│  │  HITL (3-tier)                                          │   │
│  │  Auto → Slack review → Human override                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SLACK DELIVERY LAYER                                   │   │
│  │  Guardian alerts · Investor drafts · NL QA              │   │
│  │  Block Kit · Action buttons · Feedback collection       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  OBSERVABILITY: Langfuse (LLM) · SigNoz (infra)               │
└─────────────────────────────────────────────────────────────────┘
```

------

## Component Responsibilities

| Component          | Language | Responsibility                                     |
| ------------------ | -------- | -------------------------------------------------- |
| Go API Gateway     | Go/Fiber | Webhook ingestion, OAuth, health checks            |
| Redpanda           | Infra    | Event bus between webhook layer and workers        |
| Temporal Server    | Infra    | Workflow state machine, scheduling, retries        |
| Python AI Worker   | Python   | LangGraph agents, memory spine, LLM calls          |
| Guardian Watchlist | Python   | 16 seed-stage failure pattern detectors            |
| Memory Spine       | Python   | 5-layer memory: Redis/Qdrant/Kuzu/PG/Qdrant        |
| RAG Kernel         | Python   | Context assembly ≤800 tokens before every LLM call |
| HITL Manager       | Python   | 3-tier human-in-the-loop routing                   |
| LLMOps             | Python   | Langfuse tracing, eval scoring, self-analysis      |
| Qdrant             | Infra    | Episodic + compressed vector memory                |
| Kuzu               | Embedded | Semantic graph memory (replaces Neo4j)             |
| PostgreSQL         | Infra    | Structured data, procedural memory, agent outputs  |
| Redis              | Infra    | Working memory (L1), session state                 |
| Slack Bot          | Python   | Delivery, NL QA, onboarding, Block Kit             |
| Langfuse           | Infra    | LLM tracing, eval scoring, cost tracking           |

------

## Data Flow — Guardian Alert

```
textStripe Webhook
    → Go API Gateway
    → Redpanda (stripe.events)
    → Temporal Worker picks up event
    → FinanceMonitorWorkflow starts
        Activity: fetch_stripe_data
        Activity: fetch_bank_data
        Activity: compute_runway
        Activity: run_guardian_watchlist      ← NEW (16 patterns)
        Activity: query_rag_kernel            ← NEW (≤800 token context)
        Activity: generate_guardian_insight   ← NEW (pattern-aware DSPy)
        Activity: hitl_routing                ← NEW (auto vs review)
        Activity: send_slack_alert
        Activity: write_memory_spine          ← NEW (all 5 layers)
    → Slack guardian alert delivered
    → Memory spine updated
    → Langfuse trace recorded
```

------

## 5-Layer Memory Spine

```
text┌─────────────────────────────────────────────────────┐
│              5-LAYER MEMORY SPINE                   │
│                                                     │
│  L1  REDIS (working)                                │
│      TTL: 1 hour                                    │
│      Purpose: Current workflow context              │
│      Existing code: none — new                      │
│                                                     │
│  L2  QDRANT episodic (financial_events,             │
│                        metric_events, ops_events)   │
│      TTL: 90 days then compressed                   │
│      Purpose: Raw event history                     │
│      Existing code: ✅ qdrant_client.py — REUSE    │
│                                                     │
│  L3  KUZU (semantic graph)                          │
│      TTL: permanent                                 │
│      Purpose: Relationships between patterns        │
│      Existing code: none — replaces Neo4j (unused) │
│                                                     │
│  L4  POSTGRESQL procedural                          │
│      TTL: permanent                                 │
│      Purpose: Learned agent behavior, resolved      │
│               blindspots, founder feedback          │
│      Existing code: ✅ DB already running — REUSE  │
│                                                     │
│  L5  QDRANT compressed                              │
│      TTL: permanent                                 │
│      Purpose: Compressed episodic summaries         │
│      Existing code: new collection in existing      │
│               Qdrant — ADDITIVE                     │
└─────────────────────────────────────────────────────┘
```

**Compression trigger:** Every 50 episodic writes → `CompressionWorkflow` compresses oldest 30 into a single L5 vector.

**Weight decay:** Weekly `WeightDecayWorkflow` applies decay to L2 events older than 60 days. Weight < 0.3 → eligible for compression.

------

## 3-Tier HITL

```
textTier 1 — AUTO (no human needed):
  Severity: info
  Confidence: > 0.85
  Pattern: seen before in memory
  Action: send immediately

Tier 2 — SLACK REVIEW (founder approves):
  Severity: warning
  Confidence: 0.60–0.85
  OR: new pattern, no historical precedent
  Action: send draft to #sarthi-review channel
          with [Send Now] [Edit] [Dismiss] buttons

Tier 3 — HUMAN OVERRIDE (blocks send):
  Severity: critical
  Confidence: < 0.60
  OR: investor update drafts (always)
  OR: HITL flag set by eval loop
  Action: require explicit human approval before any send
```

------

------

# SARTHI V2.0 — LOW-LEVEL DESIGN

------

## File Structure — Complete

```
textapps/
  ai/
    src/
      agents/
        finance/
          graph.py          ← v1.0 ✅ KEEP — wrap with RAG kernel
          signatures.py     ← v1.0 ✅ EXTEND — add GuardianInsight
          thresholds.py     ← v1.0 ✅ KEEP — complement with watchlist
        bi/
          graph.py          ← v1.0 ✅ KEEP
          nl_to_sql.py      ← v1.0 ✅ KEEP
          signatures.py     ← v1.0 ✅ EXTEND
        ops/
          graph.py          ← v1.0 ✅ KEEP
          signatures.py     ← v1.0 ✅ EXTEND

      guardian/             ← NEW directory
        watchlist.py        ← 16 SeedStageBlindspot objects
        detector.py         ← runs all watchlist items, returns matches
        insight_builder.py  ← builds context for GuardianInsight DSPy call

      memory/               ← NEW directory
        spine.py            ← entry point, orchestrates all 5 layers
        working.py          ← L1 Redis
        episodic.py         ← L2 Qdrant (thin wrapper over existing qdrant_client.py)
        semantic.py         ← L3 Kuzu
        procedural.py       ← L4 PostgreSQL
        compressed.py       ← L5 Qdrant (new collection)
        rag_kernel.py       ← context assembly ≤800 tokens
        compressor.py       ← 50-write trigger compression
        state_manager.py    ← belief state manager

      hitl/                 ← NEW directory
        manager.py          ← 3-tier routing logic
        confidence.py       ← confidence scoring per alert

      llmops/               ← NEW directory
        tracer.py           ← Langfuse @traced decorator
        eval_loop.py        ← weekly eval scoring
        self_analysis.py    ← agent self-analysis

      integrations/
        stripe_client.py    ← v1.0 ✅ KEEP
        plaid_client.py     ← v1.0 ✅ KEEP
        qdrant_client.py    ← v1.0 ✅ KEEP — episodic.py wraps this
        slack_client.py     ← v1.0 ✅ KEEP
        langfuse_client.py  ← v1.0 ✅ EXTEND — tracer.py wraps this
        db_client.py        ← v1.0 ✅ KEEP

      workflows/
        finance_monitor.py  ← v1.0 ✅ EXTEND — add guardian + memory activities
        bi_pulse.py         ← v1.0 ✅ EXTEND
        ops_watch.py        ← v1.0 ✅ EXTEND
        investor_update.py  ← v1.0 ✅ KEEP
        weekly_pulse.py     ← v1.0 ✅ KEEP
        self_analysis.py    ← NEW
        eval_loop.py        ← NEW
        compression.py      ← NEW
        weight_decay.py     ← NEW

  go/
    api/
      webhooks.go           ← v1.0 ✅ KEEP
      oauth.go              ← v1.0 ✅ KEEP
      health.go             ← v1.0 ✅ KEEP

tests/
  unit/
    test_agents/            ← v1.0 ✅ 119 PASSING — DO NOT TOUCH
    test_guardian/          ← NEW (target: 20 tests)
    test_memory/            ← NEW (target: 30 tests)
    test_hitl/              ← NEW (target: 10 tests)
    test_llmops/            ← NEW (target: 15 tests)
  integration/
    test_workflows/         ← NEW (target: 16 tests)
  e2e/
    playwright/             ← NEW
    go/                     ← NEW
    python/                 ← NEW
```

------

## Guardian Watchlist — Full Implementation

```
python# apps/ai/src/guardian/watchlist.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class SeedStageBlindspot:
    id: str
    name: str
    domain: str                       # finance | bi | ops
    signals_required: list[str]
    detection_logic: Callable
    why_it_matters: str
    what_founder_doesnt_know: str
    urgency_horizon: str
    historical_precedent: str
    one_action: str

SEED_STAGE_WATCHLIST = [

    SeedStageBlindspot(
        id="FG-01",
        name="Silent Churn Death",
        domain="finance",
        signals_required=["monthly_churn_pct"],
        detection_logic=lambda s: s.get("monthly_churn_pct", 0) > 0.03,
        why_it_matters=(
            "3% monthly churn is 36% annual churn. "
            "Series A investors look at annual churn. "
            "You will not be able to explain this away."
        ),
        what_founder_doesnt_know=(
            "Monthly churn that 'seems fine' is almost always fatal "
            "at scale. Most founders realize this at month 16, not month 6."
        ),
        urgency_horizon=(
            "You have ~8 months before this is unfixable before "
            "your Series A attempt."
        ),
        historical_precedent=(
            "The typical pattern: churn starts at 2%, founders focus on "
            "acquisition, churn reaches 4%, too late to fix the root "
            "cause before fundraising."
        ),
        one_action=(
            "Call one churned customer this week. Don't ask what went "
            "wrong. Ask what they expected the product to do that it didn't."
        )
    ),

    SeedStageBlindspot(
        id="FG-02",
        name="Burn Multiple Creep",
        domain="finance",
        signals_required=["net_new_arr", "net_burn"],
        detection_logic=lambda s: (
            s.get("net_burn", 0) > 0 and
            s.get("net_new_arr", 1) > 0 and
            (s["net_burn"] / s["net_new_arr"]) > 2.0
        ),
        why_it_matters=(
            "Burn multiple > 2x: you're spending $2 to make $1 of new ARR. "
            "Series A benchmark: < 1.5x."
        ),
        what_founder_doesnt_know=(
            "Most founders track absolute burn. Almost none track burn "
            "multiple. Investors calculate it in the first 10 minutes."
        ),
        urgency_horizon="Series A investors will catch this immediately.",
        historical_precedent=(
            "High burn multiple is the most common reason founders get "
            "caught off-guard in Series A diligence."
        ),
        one_action=(
            "Calculate your burn multiple right now: net burn / net new ARR. "
            "If it's above 2, find one non-headcount cost to cut this month."
        )
    ),

    SeedStageBlindspot(
        id="FG-03",
        name="Customer Concentration Risk",
        domain="finance",
        signals_required=["top_customer_mrr", "total_mrr"],
        detection_logic=lambda s: (
            s.get("total_mrr", 0) > 0 and
            (s.get("top_customer_mrr", 0) / s["total_mrr"]) > 0.30
        ),
        why_it_matters=(
            "One customer is >30% of MRR. If they churn, you lose more "
            "than a third of revenue overnight."
        ),
        what_founder_doesnt_know=(
            "This looks fine until the day it doesn't. Investors will "
            "immediately ask what happens if that customer leaves."
        ),
        urgency_horizon="Diversification takes 3–6 months minimum. Start now.",
        historical_precedent=(
            "The most common version: the big customer was also the design "
            "partner whose requirements shaped the product in ways that "
            "don't generalize."
        ),
        one_action=(
            "Identify two prospects in your pipeline who are NOT similar "
            "to your top customer. Prioritize closing one this month."
        )
    ),

    SeedStageBlindspot(
        id="FG-04",
        name="Runway Compression Acceleration",
        domain="finance",
        signals_required=["burn_rate", "prev_burn_rate", "runway_days"],
        detection_logic=lambda s: (
            s.get("prev_burn_rate", 0) > 0 and
            (s.get("burn_rate", 0) / s["prev_burn_rate"]) > 1.20 and
            s.get("runway_days", 999) < 270
        ),
        why_it_matters=(
            "Burn is accelerating while runway is already under 9 months. "
            "You are compressing your fundraising window faster than you think."
        ),
        what_founder_doesnt_know=(
            "9 months runway feels long. 3 months are spent fundraising. "
            "You actually have 6 months of operating time left."
        ),
        urgency_horizon="Effective runway is ~6 months from today.",
        historical_precedent=(
            "Founders who hit this usually hired one month too early "
            "while revenue growth lagged behind plan."
        ),
        one_action="Freeze all non-essential spend for 30 days. Review every recurring charge."
    ),

    SeedStageBlindspot(
        id="FG-05",
        name="Failed Payment Cluster",
        domain="finance",
        signals_required=["failed_payments_7d"],
        detection_logic=lambda s: s.get("failed_payments_7d", 0) >= 3,
        why_it_matters=(
            "3+ failed payments in 7 days is involuntary churn in progress. "
            "Most of these customers won't update their card — they'll just leave."
        ),
        what_founder_doesnt_know=(
            "Involuntary churn is typically 20–40% of total churn at seed. "
            "It's almost entirely preventable with a dunning sequence."
        ),
        urgency_horizon="Every day without a dunning email loses ~30% of recoverable revenue.",
        historical_precedent=(
            "Founders discover involuntary churn in their annual review "
            "when the number is already material. It's been losing them "
            "money for months."
        ),
        one_action=(
            "Turn on Stripe's built-in Smart Retries today. "
            "Send a personal email to each failed payment customer this week."
        )
    ),

    SeedStageBlindspot(
        id="FG-06",
        name="Payroll Revenue Ratio Breach",
        domain="finance",
        signals_required=["payroll_monthly", "mrr"],
        detection_logic=lambda s: (
            s.get("mrr", 0) > 0 and
            (s.get("payroll_monthly", 0) / s["mrr"]) > 0.60
        ),
        why_it_matters=(
            "Payroll is >60% of MRR. Classic seed-stage overhire signal. "
            "You hired ahead of revenue, not behind it."
        ),
        what_founder_doesnt_know=(
            "This ratio is invisible until burn suddenly spikes. "
            "By then, the only fix is painful."
        ),
        urgency_horizon="Hire freeze until MRR catches up to payroll trajectory.",
        historical_precedent=(
            "The most common version: founder hired a head of sales before "
            "having repeatable sales motion. "
            "Salary ran 6 months with no pipeline."
        ),
        one_action="No new hires until MRR covers current payroll at 50% ratio."
    ),

    SeedStageBlindspot(
        id="BG-01",
        name="Leaky Bucket Activation",
        domain="bi",
        signals_required=["new_signups", "activation_rate", "mrr_growth_pct"],
        detection_logic=lambda s: (
            s.get("new_signups", 0) > 0 and
            s.get("activation_rate", 1) < 0.40 and
            s.get("mrr_growth_pct", 0) > 0
        ),
        why_it_matters=(
            "MRR is growing but activation is failing. You are buying growth "
            "with acquisition spend while leaking users before they see value."
        ),
        what_founder_doesnt_know=(
            "A growing MRR number masks an activation wall. "
            "The acquisition channel is working. The product is not. "
            "These require completely different fixes."
        ),
        urgency_horizon="Every week of delayed fix costs more CAC payback time.",
        historical_precedent=(
            "Founders who hit this discover it when they try to scale paid "
            "acquisition and unit economics collapse."
        ),
        one_action=(
            "Watch 3 session recordings of users who signed up and never "
            "activated. Find the drop-off step. Fix that one thing."
        )
    ),

    SeedStageBlindspot(
        id="BG-02",
        name="Power User MRR Masking",
        domain="bi",
        signals_required=["top_10pct_mrr", "total_mrr", "avg_mrr_new_customers"],
        detection_logic=lambda s: (
            s.get("top_10pct_mrr", 0) / max(s.get("total_mrr", 1), 1) > 0.60 and
            s.get("avg_mrr_new_customers", 0) <
            s.get("avg_mrr_all_customers", 1) * 0.80
        ),
        why_it_matters=(
            "Your top 10% of users generate 60%+ of MRR. "
            "New customers are worth materially less. "
            "Your growth story is weaker than your MRR chart shows."
        ),
        what_founder_doesnt_know=(
            "Aggregate MRR growth looks healthy. Per-customer economics "
            "are deteriorating. Investors will find this in diligence."
        ),
        urgency_horizon="This compounds with every lower-value customer you add.",
        historical_precedent=(
            "Founders present MRR growth charts to investors. "
            "Investors ask for MRR per customer over time. "
            "The conversation gets uncomfortable."
        ),
        one_action="Segment your MRR by cohort month. Calculate average MRR per customer for each cohort."
    ),

    SeedStageBlindspot(
        id="BG-03",
        name="Feature Adoption Post-Deploy Drop",
        domain="bi",
        signals_required=["feature_name", "adoption_pre_deploy", "adoption_post_deploy"],
        detection_logic=lambda s: (
            s.get("adoption_post_deploy", 1) <
            s.get("adoption_pre_deploy", 0) * 0.70
        ),
        why_it_matters=(
            "You shipped something and usage dropped. "
            "Either you broke something, or you shipped the wrong thing."
        ),
        what_founder_doesnt_know=(
            "Feature adoption drop after deploy is almost always invisible "
            "without cohort-level tracking. Founders assume the deploy worked."
        ),
        urgency_horizon="Every week of delay means more users habituating to the broken state.",
        historical_precedent=(
            "Founders find out about this during user interviews, "
            "weeks after the deploy, when the damage is done."
        ),
        one_action="Talk to one user who used this feature before the deploy and hasn't since."
    ),

    SeedStageBlindspot(
        id="BG-04",
        name="Cohort Retention Degradation",
        domain="bi",
        signals_required=["cohort_retention_30d_recent", "cohort_retention_30d_prior"],
        detection_logic=lambda s: (
            s.get("cohort_retention_30d_recent", 1) <
            s.get("cohort_retention_30d_prior", 0) * 0.90
        ),
        why_it_matters=(
            "New cohorts are retaining 10%+ worse than prior cohorts. "
            "PMF is not holding as you grow. "
            "This is the earliest signal of ICP drift."
        ),
        what_founder_doesnt_know=(
            "Most founders look at blended retention. "
            "Cohort-by-cohort degradation is invisible in aggregate numbers "
            "until it's very bad."
        ),
        urgency_horizon="ICP drift is reversible early. Almost impossible to reverse late.",
        historical_precedent=(
            "Early customers self-selected perfectly. Newer customers came "
            "from broader acquisition. The product doesn't fit as well. "
            "Founders realize this when they're already 3 cohorts deep."
        ),
        one_action="Interview 2 customers from your most recent cohort. "
                   "Find one thing different about how they use the product vs. early customers."
    ),

    SeedStageBlindspot(
        id="BG-05",
        name="NRR Below 100 at Seed",
        domain="bi",
        signals_required=["nrr"],
        detection_logic=lambda s: s.get("nrr", 100) < 100,
        why_it_matters=(
            "NRR < 100% means you're losing more than you're expanding. "
            "You have no land-and-expand motion. "
            "Every new customer partially replaces a churned one."
        ),
        what_founder_doesnt_know=(
            "NRR below 100% at seed is fixable. NRR below 100% "
            "presented at Series A is a red flag that's hard to explain away."
        ),
        urgency_horizon="Fix the expansion motion before fundraising.",
        historical_precedent=(
            "Founders pitch growth by acquisition. Investors ask about "
            "NRR. Sub-100 NRR with no explanation kills term sheets."
        ),
        one_action="Identify one upsell or expansion trigger in your product. "
                   "Build the Slack alert or email for it this week."
    ),

    SeedStageBlindspot(
        id="BG-06",
        name="Trial Activation Wall",
        domain="bi",
        signals_required=["trial_step_dropoffs"],
        detection_logic=lambda s: (
            any(step["drop_pct"] > 0.50 for step in
                s.get("trial_step_dropoffs", []))
        ),
        why_it_matters=(
            "More than 50% of trial users are abandoning at one specific step. "
            "You have an activation wall, not a funnel."
        ),
        what_founder_doesnt_know=(
            "Activation walls are rarely obvious. Founders assume users "
            "drop off for general reasons. The wall is almost always one "
            "specific friction point."
        ),
        urgency_horizon="Every day this exists, you're wasting your acquisition spend.",
        historical_precedent=(
            "Almost always solvable in one sprint once identified. "
            "Founders who track it improve trial-to-paid 2–3x in 30 days."
        ),
        one_action="Watch 5 session recordings of users who hit that step and bounced."
    ),

    SeedStageBlindspot(
        id="OG-01",
        name="Error Rate User Segment Correlation",
        domain="ops",
        signals_required=["errors_by_segment"],
        detection_logic=lambda s: (
            any(seg["error_pct"] > 0.10 for seg in
                s.get("errors_by_segment", []))
        ),
        why_it_matters=(
            "Errors are concentrated in one user segment. "
            "This isn't random noise — it's a systematic failure "
            "for a specific type of user."
        ),
        what_founder_doesnt_know=(
            "Aggregate error rates hide segment-specific failures. "
            "One user type might be having a completely broken experience "
            "while your aggregate error rate looks fine."
        ),
        urgency_horizon="Every hour this runs, that user segment loses trust.",
        historical_precedent=(
            "This is usually traced to a missing edge case for a specific "
            "plan tier, geography, or usage pattern."
        ),
        one_action="Identify the segment. Find one user in it. Ask them what's broken."
    ),

    SeedStageBlindspot(
        id="OG-02",
        name="Support Volume Outpacing Growth",
        domain="ops",
        signals_required=["support_tickets_growth_pct", "user_growth_pct"],
        detection_logic=lambda s: (
            s.get("support_tickets_growth_pct", 0) >
            s.get("user_growth_pct", 0) * 1.5
        ),
        why_it_matters=(
            "Support is growing 1.5x faster than users. "
            "Your product is getting harder to use as it grows, not easier."
        ),
        what_founder_doesnt_know=(
            "This ratio is almost never tracked. Founders track absolute "
            "support volume, not relative to users. "
            "The ratio reveals the trend."
        ),
        urgency_horizon="At scale, this ratio makes you unsupportable.",
        historical_precedent=(
            "Usually caused by accumulating UX debt that founders "
            "deprioritize in favor of new features."
        ),
        one_action="Find the top 3 support ticket categories this month. "
                   "Pick one. Add it to next sprint as a product fix, not a support response."
    ),

    SeedStageBlindspot(
        id="OG-03",
        name="Cross-Channel Bug Convergence",
        domain="ops",
        signals_required=["bug_mentions_by_channel"],
        detection_logic=lambda s: (
            sum(1 for ch in s.get("bug_mentions_by_channel", {}).values()
                if ch > 0) >= 3
        ),
        why_it_matters=(
            "The same bug is being reported across 3+ channels simultaneously. "
            "This is no longer an edge case. It's a product incident."
        ),
        what_founder_doesnt_know=(
            "Multi-channel bug convergence means your user base is actively "
            "experiencing the issue. The blast radius is larger than any "
            "single channel shows."
        ),
        urgency_horizon="Treat this as an incident. Drop what you're doing.",
        historical_precedent=(
            "Founders who miss cross-channel convergence find out "
            "when a user posts publicly. By then it's a reputation problem."
        ),
        one_action="Stop. Fix this now. Post a status update in Slack to users."
    ),

    SeedStageBlindspot(
        id="OG-04",
        name="Deploy Frequency Collapse",
        domain="ops",
        signals_required=["deploys_this_month", "deploys_last_month"],
        detection_logic=lambda s: (
            s.get("deploys_last_month", 1) > 0 and
            s.get("deploys_this_month", 0) <
            s.get("deploys_last_month", 1) * 0.50
        ),
        why_it_matters=(
            "Deploy frequency dropped >50% MoM. "
            "This is almost always the first measurable signal of "
            "technical debt paralysis."
        ),
        what_founder_doesnt_know=(
            "Founders feel the slowdown subjectively but rarely measure it. "
            "When it's measurable, the debt is already significant."
        ),
        urgency_horizon="Technical debt compounds. The longer this runs, the worse it gets.",
        historical_precedent=(
            "Founders at month 18 wish they had spent one sprint on "
            "test coverage at month 6. They never find time to go back."
        ),
        one_action="Schedule a 1-week debt sprint in the next 30 days. "
                   "Don't ship features that week. Just clean."
    ),

    SeedStageBlindspot(
        id="OG-05",
        name="Infrastructure Unit Economics Divergence",
        domain="ops",
        signals_required=["aws_cost_growth_pct", "user_growth_pct"],
        detection_logic=lambda s: (
            s.get("aws_cost_growth_pct", 0) >
            s.get("user_growth_pct", 0) * 2
        ),
        why_it_matters=(
            "AWS is growing 2x faster than users. "
            "You have a unit economics structural problem, not a DevOps problem."
        ),
        what_founder_doesnt_know=(
            "Easy to dismiss as 'we'll optimize later.' The pattern "
            "usually indicates an architectural decision that gets harder "
            "to fix the longer you wait."
        ),
        urgency_horizon="Cheapest to fix now. Exponentially expensive at 10x users.",
        historical_precedent=(
            "Almost always traced to a specific architectural choice made "
            "in the first 90 days. Usually an N+1 query, a polling loop, "
            "or an unindexed table."
        ),
        one_action=(
            "You built this. You know where to look. "
            "Run EXPLAIN ANALYZE on your three most frequent queries this week."
        )
    ),
]
```

------

## DSPy Signature — Guardian Insight

```
python# apps/ai/src/agents/anomaly/signatures.py

class GuardianInsight(dspy.Signature):
    """
    You are a guardian who has seen dozens of seed-stage startups fail.
    You have just detected a pattern the founder hasn't noticed.
    You are NOT an assistant returning data. You are telling them
    something they need to know BEFORE it becomes a crisis.

    Rules (non-negotiable):
    - Start with the PATTERN NAME, never a number
    - Numbers are evidence. The pattern is the insight.
    - Give the urgency horizon specific to their fundraise timeline
    - Reference what typically happens to founders who miss this
    - End with ONE concrete action this week
    - Max 200 words
    - Sound like a trusted colleague. Never a dashboard notification.
    - Never use phrases like: "consider monitoring", "you may want to",
      "it seems like", "great job". You are a guardian, not a chatbot.
    """

    # Memory context (from RAG kernel — ≤800 tokens)
    context: str = dspy.InputField(
        desc="Prior events, patterns, company context assembled by "
             "RAG kernel. Use this to make the insight specific to "
             "this founder's history with Sarthi.")

    # The detected blindspot fields
    blindspot_name:           str = dspy.InputField()
    why_it_matters:           str = dspy.InputField()
    what_founder_doesnt_know: str = dspy.InputField()
    urgency_horizon:          str = dspy.InputField()
    historical_precedent:     str = dspy.InputField()
    one_action:               str = dspy.InputField()

    # Injected numbers (never LLM-generated)
    current_metric:    str = dspy.InputField(
        desc="The exact triggering metric with value. LLM must use "
             "this verbatim. Never generate or modify financial numbers.")
    implied_at_scale:  str = dspy.InputField(
        desc="What this implies annually or at Series A.")

    # Output
    guardian_message: str = dspy.OutputField(
        desc="The guardian insight. Pattern first. Action last. "
             "200 words max. No bullet lists. Prose only. "
             "Reads like a message from someone who has been "
             "through this before and wants you to not make "
             "the same mistake.")
```

------

## Memory Spine Implementation

```
python# apps/ai/src/memory/spine.py
from typing import Protocol
import logging

logger = logging.getLogger(__name__)

class MemoryLayer(Protocol):
    def read(self, tenant_id: str, query: str, limit: int) -> list[dict]: ...
    def write(self, tenant_id: str, payload: dict) -> str: ...
    def available(self) -> bool: ...   # returns False if backing service unreachable

class MemorySpine:
    def __init__(self, layers: list[MemoryLayer], rag_kernel):
        self.layers = layers
        self.rag_kernel = rag_kernel

    def load_context(self, tenant_id: str, task: str,
                     signal: dict, max_tokens: int = 800) -> str:
        results = []
        for layer in self.layers:
            if not layer.available():          # NEVER crash on unavailable layer
                logger.warning(f"Memory layer {layer.__class__.__name__} unavailable")
                continue
            try:
                results.extend(layer.read(tenant_id, task, limit=5))
            except Exception as e:
                logger.error(f"Memory read failed: {e}")  # log and continue
        return self.rag_kernel.assemble(results, max_tokens=max_tokens)

    def write_all(self, tenant_id: str, payload: dict) -> None:
        for layer in self.layers:
            if not layer.available():
                continue
            try:
                layer.write(tenant_id, payload)
            except Exception as e:
                logger.error(f"Memory write failed on {layer.__class__.__name__}: {e}")
```

------

## Langfuse Tracer — Zero Test Impact

```
python# apps/ai/src/llmops/tracer.py
import os
import functools
import langfuse

_client = None

def _get_client():
    global _client
    if _client is None and os.environ.get("LANGFUSE_SECRET_KEY"):
        _client = langfuse.Langfuse(
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
        )
    return _client

def traced(agent: str, signature: str):
    """Decorator. No-op if LANGFUSE_SECRET_KEY not in env (unit tests pass through)."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            client = _get_client()
            if client is None:
                return fn(*args, **kwargs)     # tracing disabled → pure pass-through
            trace = client.trace(name=f"{agent}.{signature}")
            try:
                result = fn(*args, **kwargs)
                trace.generation(output=str(result))
                return result
            except Exception as e:
                trace.event(name="error", metadata={"error": str(e)})
                raise
        return wrapper
    return decorator

# Usage on any existing agent function — one line addition:
# @traced(agent="finance", signature="GuardianInsight")
# def generate_guardian_message(state): ...
```

------

## RAG Kernel

```
python# apps/ai/src/memory/rag_kernel.py
import tiktoken

ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")

class RAGKernel:
    def assemble(self, results: list[dict], max_tokens: int = 800) -> str:
        if not results:
            return ""

        # Priority order: compressed (L5) > episodic (L2) > working (L1)
        sorted_results = sorted(
            results,
            key=lambda r: (r.get("weight", 0.5), r.get("recency_score", 0)),
            reverse=True
        )

        assembled = []
        token_count = 0

        for result in sorted_results:
            text = result.get("content", "")
            tokens = len(ENCODING.encode(text))
            if token_count + tokens > max_tokens:
                break
            assembled.append(text)
            token_count += tokens

        return "\n\n".join(assembled)
```

------

## Schema Aliases — Handles Real-World Column Variance

```
python# apps/ai/src/integrations/db_client.py (EXTEND existing file)

KNOWN_COLUMN_ALIASES = {
    "created_at":     ["created_at", "createdat", "signup_date",
                       "joined_at", "registered_at"],
    "last_active_at": ["last_active_at", "last_seen", "last_login",
                       "lastseen", "last_activity"],
    "plan":           ["plan", "subscription_plan", "tier",
                       "billing_plan", "account_type"],
    "mrr":            ["mrr", "monthly_revenue", "subscription_amount",
                       "monthly_mrr"],
    "user_id":        ["user_id", "userid", "id", "customer_id"],
}

SUPPORTED_DIALECTS = ["postgresql", "cockroachdb", "supabase"]
UNSUPPORTED_DIALECTS = ["mysql", "planetscale", "sqlite"]

def validate_connection(conn_string: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    for unsupported in UNSUPPORTED_DIALECTS:
        if unsupported in conn_string.lower():
            return False, (
                f"Sarthi V1 supports PostgreSQL only. "
                f"{unsupported.title()} support is coming in V2. "
                f"If you're on PlanetScale, you can connect via "
                f"their MySQL-compatible endpoint — not supported yet."
            )
    return True, ""
```

------

## PostgreSQL Migration — New Tables

```
sql-- V2.0 migration additions (DO NOT modify existing tables)

-- Guardian insight acknowledgement
ALTER TABLE agent_alerts
  ADD COLUMN IF NOT EXISTS insight_acknowledged  BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS insight_already_knew  BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS insight_not_relevant  BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS blindspot_id          TEXT,
  ADD COLUMN IF NOT EXISTS guardian_pattern_name TEXT;

-- Resolved blindspots (procedural memory L4)
CREATE TABLE IF NOT EXISTS resolved_blindspots (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID REFERENCES tenants(id),
  blindspot_id    TEXT NOT NULL,
  detected_at     TIMESTAMPTZ NOT NULL,
  resolved_at     TIMESTAMPTZ,
  metric_at_detection NUMERIC,
  metric_at_resolution NUMERIC,
  founder_action  TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- LLMOps eval scores
CREATE TABLE IF NOT EXISTS eval_scores (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID REFERENCES tenants(id),
  agent_type      TEXT NOT NULL,
  week_of         DATE NOT NULL,
  guardian_score  NUMERIC,     -- 0–1: was insight genuinely new?
  accuracy_score  NUMERIC,     -- 0–1: were numbers correct?
  tone_score      NUMERIC,     -- 0–1: guardian vs assistant tone?
  action_score    NUMERIC,     -- 0–1: was action specific and doable?
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Onboarding success tracking
CREATE TABLE IF NOT EXISTS onboarding_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID REFERENCES tenants(id),
  event_type      TEXT NOT NULL,  -- setup_complete | first_insight_acknowledged
  occurred_at     TIMESTAMPTZ DEFAULT NOW()
);
```

------

## New Qdrant Collections

```
python# Add to existing qdrant_client.py setup (ADDITIVE — no changes to existing 3 collections)

NEW_COLLECTIONS = {
    "compressed_memory": {
        "vector_size": 768,
        "distance": "Cosine",
        "payload_schema": {
            "tenant_id": "keyword",
            "compression_date": "datetime",
            "source_event_ids": "text",       # comma-separated original IDs
            "summary": "text",
            "weight": "float",
            "domain": "keyword",              # finance | bi | ops
        }
    },
    "founder_blindspots": {
        "vector_size": 768,
        "distance": "Cosine",
        "payload_schema": {
            "tenant_id": "keyword",
            "blindspot_id": "keyword",
            "blindspot_name": "text",
            "detected_at": "datetime",
            "metric_at_detection": "float",
            "founder_response": "keyword",    # acknowledged | already_knew | dismissed
            "resolved": "bool",
        }
    }
}
```

------

## docker-compose Changes

```
text# Remove Neo4j (unused). Add Redis. Kuzu is embedded — no service needed.

# REMOVE:
#  neo4j:
#    image: neo4j:5
#    ...

# ADD:
  redis:
    image: redis:7-alpine
    container_name: sarthi-redis
    ports:
      - "6379:6379"
    restart: unless-stopped
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
```

------

## requirements.txt Changes

```
text# Remove:
neo4j

# Add:
kuzu==0.4.2
redis==5.0.3
tiktoken==0.7.0
```

------

------

# SARTHI V2.0 — CODING AGENT INSTRUCTIONS

------

## Part 0: Your Prime Directive

```
textEXTEND. DO NOT REWRITE.

119 tests are passing. They must still be passing when you finish.
Every line of new code is NEW code — in new files, new directories.
You do not modify existing agent graphs.
You do not modify existing workflow definitions.
You do not modify existing signatures (you ADD new signatures).
You do not modify existing DB tables (you ADD new columns and tables).
You do not modify existing Qdrant collections (you ADD new ones).

When in doubt: write new code. Leave existing code alone.
```

------

## Part 1: Build Order (Strict — Do Not Deviate)

```
textStep 1: Infrastructure swap
  [ ] Remove neo4j from docker-compose.yml
  [ ] Add redis service to docker-compose.yml
  [ ] Remove neo4j from requirements.txt
  [ ] Add kuzu, redis, tiktoken to requirements.txt
  [ ] Run: docker-compose up -d redis
  [ ] Verify: docker ps shows sarthi-redis healthy
  [ ] Run existing 119 tests → must still pass

Step 2: Guardian watchlist (pure Python, zero dependencies on new infra)
  [ ] Create apps/ai/src/guardian/ directory
  [ ] Write guardian/watchlist.py — 16 SeedStageBlindspot objects
  [ ] Write guardian/detector.py — runs all watchlist items against signals
  [ ] Write guardian/insight_builder.py — prepares DSPy inputs
  [ ] Write tests/unit/test_guardian/ (target: 20 tests)
      - test each detection_logic predicate independently
      - test no false positives on healthy signal sets
      - test all 16 watchlist items have required fields
  [ ] Run all tests → 139 passing, 0 regressions

Step 3: Memory spine (new directory, no existing code touched)
  [ ] Write memory/working.py (Redis L1)
  [ ] Write memory/episodic.py (thin wrapper over existing qdrant_client.py)
  [ ] Write memory/semantic.py (Kuzu L3)
  [ ] Write memory/procedural.py (PostgreSQL L4)
  [ ] Write memory/compressed.py (new Qdrant collection)
  [ ] Write memory/compressor.py (50-write trigger)
  [ ] Write memory/rag_kernel.py (≤800 token assembly)
  [ ] Write memory/state_manager.py
  [ ] Write memory/spine.py (orchestrates all layers)
  [ ] Write tests/unit/test_memory/ (target: 30 tests)
      - every layer must be independently testable with mocked backing service
      - test available() returns False gracefully when service is down
      - test spine.load_context() returns "" (not crash) when all layers unavailable
      - test RAG kernel never exceeds 800 tokens
      - test tenant isolation (tenant B never sees tenant A data)
  [ ] Run all tests → 169 passing, 0 regressions

Step 4: LLMOps tracer (decorator pattern — zero impact on existing calls)
  [ ] Write llmops/tracer.py
  [ ] Write llmops/eval_loop.py
  [ ] Write llmops/self_analysis.py
  [ ] Write tests/unit/test_llmops/ (target: 15 tests)
      - test @traced decorator is pure pass-through when LANGFUSE_SECRET_KEY not set
      - this is critical: unit tests must NEVER require Langfuse running
  [ ] Run all tests → 184 passing, 0 regressions

Step 5: HITL manager
  [ ] Write hitl/manager.py
  [ ] Write hitl/confidence.py
  [ ] Write tests/unit/test_hitl/ (target: 10 tests)
  [ ] Run all tests → 194 passing, 0 regressions

Step 6: GuardianInsight DSPy signature (ADDITIVE to existing signatures.py)
  [ ] In each agents/*/signatures.py, ADD GuardianInsight class
  [ ] Do NOT modify existing signature classes
  [ ] Do NOT change any existing function signatures
  [ ] Run all tests → 194 passing, 0 regressions

Step 7: Wire RAG kernel into agents (HIGHEST RISK STEP — be careful)
  [ ] In each agent's main execution function, ADD this pattern:
      try:
          context = memory_spine.load_context(...)
      except Exception:
          context = ""    # ALWAYS fall back to empty string, never crash
  [ ] The context="" fallback means all 119 existing tests continue to pass
      without a running memory spine
  [ ] Run all 119 existing tests with memory spine NOT initialized → must pass
  [ ] Run all tests with memory spine initialized → must pass

Step 8: New DB migrations (ADDITIVE only)
  [ ] Run new SQL migrations (ALTER TABLE ... ADD COLUMN IF NOT EXISTS)
  [ ] Add new tables (resolved_blindspots, eval_scores, onboarding_events)
  [ ] Run all tests → 194 passing, 0 regressions

Step 9: New Qdrant collections (ADDITIVE only)
  [ ] Create compressed_memory collection
  [ ] Create founder_blindspots collection
  [ ] Existing 3 collections untouched
  [ ] Run all tests → 194 passing, 0 regressions

Step 10: New Temporal workflows
  [ ] Write workflows/self_analysis.py
  [ ] Write workflows/eval_loop.py
  [ ] Write workflows/compression.py
  [ ] Write workflows/weight_decay.py
  [ ] Register in WORKFLOW_SCHEDULES
  [ ] Write tests/integration/test_workflows/ (target: 16 tests)
  [ ] Run all tests → 210 passing, 0 regressions

Step 11: Extend existing Temporal workflows (CAREFUL)
  [ ] In finance_monitor.py: add guardian watchlist activity + memory write activity
      AFTER existing activities, not replacing them
  [ ] In bi_pulse.py: same pattern
  [ ] In ops_watch.py: same pattern
  [ ] Run all 119 original tests → must still pass
  [ ] Run full suite → 210+ passing, 0 regressions
```

------

## Part 2: The Fallback Contract (Non-Negotiable)

Every new system you build must degrade gracefully. The guardian only fails if the agent fails. The agent must never fail because of a guardian component.

```python

# THIS PATTERN IS MANDATORY in every agent node that calls new systems:

def any_agent_node(state: AgentState) -> AgentState:

    # Memory spine — optional, graceful fallback
    context = ""
    try:
        if memory_spine and memory_spine.is_initialized():
            context = memory_spine.load_context(
                tenant_id=state["tenant_id"],
                task="...",
                signal={...},
                max_tokens=800
            )
    except Exception:
        context = ""    # spine down → empty context → agent still runs

    # Guardian watchlist — optional, graceful fallback
    watchlist_results = []
    try:
        watchlist_results = detector.run(state)
    except Exception:
        watchlist_results = []    # watchlist down → no patterns → agent still runs

    # HITL — optional, graceful fallback
    tier = "auto"
    try:
        tier = hitl_manager.route(watchlist_results, confidence)
    except Exception:
        tier = "auto"    # HITL down → auto-send → agent still runs

    # Tracer — ALWAYS a pass-through if not configured
    # @traced decorator handles this automatically
```

------

## Part 3: Guardian Alert Rules (Enforce in Every Output)

```
textRULE 1: Numbers are NEVER generated by LLM.
  All financial numbers, metrics, dates, and percentages are
  fetched from data sources and injected into DSPy inputs.
  The LLM writes narrative. It never invents quantities.
  Violation of this rule destroys founder trust permanently.

RULE 2: Guardian message structure is always:
  Pattern name (not metric name) → Number (injected) →
  Why it matters at seed → Urgency horizon → Historical precedent →
  One concrete action. Always in this order. Always prose. Never bullets.

RULE 3: First alert to any tenant must come from the watchlist.
  A healthy-state pulse as the first alert is a product failure.
  Gate the first delivery: if no watchlist items triggered,
  wait for the next cycle. Do not send "everything looks good."

RULE 4: Max 3 alerts per day per tenant.
  Dedup: same blindspot_id cannot fire again within 48 hours.
  Prioritize: critical > warning > info.
  Digest mode: info alerts accumulate into weekly digest.

RULE 5: Tenant isolation is absolute.
  Every Qdrant query must filter by tenant_id payload.
  Every DB query must WHERE tenant_id = %s.
  Every Redis key must be prefixed: f"tenant:{tenant_id}:{key}".
  Write a test for this. Run it. Make it pass.
```

------

## Part 4: The Onboarding Snippet (Ship This Verbatim)

Include this in the Slack DM setup flow for DB connection:

```
textTo connect your database, I need read-only access.
Run this in your database console:

CREATE USER sarthi_readonly WITH PASSWORD 'choose_a_password';
GRANT CONNECT ON DATABASE your_db_name TO sarthi_readonly;
GRANT USAGE ON SCHEMA public TO sarthi_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sarthi_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO sarthi_readonly;

Then paste your connection string:
postgresql://sarthi_readonly:your_password@your_host:5432/your_db_name

I will never write, delete, or modify your data.
Only SELECT queries. Ever.
```

------

## Part 5: Test Targets by Phase

| Phase                | New Tests  | Cumulative | Regressions |
| -------------------- | ---------- | ---------- | ----------- |
| Baseline             | —          | 119        | —           |
| + Guardian watchlist | 20         | 139        | 0           |
| + Memory spine       | 30         | 169        | 0           |
| + LLMOps             | 15         | 184        | 0           |
| + HITL               | 10         | 194        | 0           |
| + New workflows      | 16         | 210        | 0           |
| + Wired into agents  | 0 new      | 210        | 0           |
| **V2.0 complete**    | **91 new** | **210**    | **0**       |

------

Good challenge. Let me be honest about each one rather than just validating the existing stack.

------

## The Real Question: Need vs. Nice-to-Have vs. Wrong Tool

## Neo4j + Graphiti — **Reconsider Seriously**

This is the one I'd push back on hardest. Here's why Kuzu alone may not be enough:

**What Graphiti does that Kuzu doesn't:**

- Graphiti is specifically designed for **temporal knowledge graphs for AI agents** — it tracks *how facts change over time*, not just what the relationships are
- It handles the exact problem Sarthi has: "last month the founder's churn was 3%, this month it's 4%, and that trend is connected to the cohort degradation pattern from 6 weeks ago"
- Kuzu is an embedded graph DB — good for static semantic relationships, but it has no built-in concept of episodic temporal graph evolution
- Graphiti + Neo4j gives you: entity resolution, temporal edges, contradiction handling, and bi-temporal queries out of the box

**The honest verdict:**

```
textIf Sarthi's memory is just "store and retrieve similar events"
→ Kuzu is fine

If Sarthi's memory needs to understand "this founder's churn
  has been trending up for 3 consecutive months and it
  correlates with the cohort degradation we saw in January"
→ You need Graphiti + Neo4j

For a guardian that surfaces unknown unknowns, the second
case is closer to the truth. Temporal graph memory is the
moat, not just vector similarity.
```

**Recommendation: Keep Neo4j + Graphiti.** Replace Kuzu with it. The embedded convenience of Kuzu is not worth losing temporal graph intelligence.

------

## Pydantic AI + LangGraph — **Both, for Different Reasons**

|                              | LangGraph                    | Pydantic AI                                                  |
| ---------------------------- | ---------------------------- | ------------------------------------------------------------ |
| **What it does**             | State machine for agent flow | Type-safe LLM calls with structured outputs                  |
| **V1 status**                | ✅ Already in use             | ❌ Not in use                                                 |
| **Why you need it**          | Agent graph orchestration    | Guaranteed structured output from every LLM call             |
| **The real risk without it** | None — already working       | LLM returns malformed JSON → guardian message fails silently |

**Pydantic AI is not optional for a guardian.** The guardian message has a strict contract — pattern name, injected numbers, action. If the LLM drifts from that structure, the message breaks. Pydantic AI enforces the schema at the output layer and retries automatically if the LLM returns garbage.

```
python# Without Pydantic AI — fragile
result = llm.invoke(prompt)
message = result.content   # could be anything

# With Pydantic AI — enforced contract
class GuardianMessage(BaseModel):
    pattern_name: str
    insight: str           # max 200 words, validated
    urgency_horizon: str
    one_action: str
    numbers_used: list[str]  # audit trail: what numbers were injected

result = await agent.run(prompt, result_type=GuardianMessage)
# If LLM doesn't return this shape → automatic retry → validated output
```

**Recommendation: Add Pydantic AI. Keep LangGraph. They're not competing — LangGraph handles the agent flow state machine, Pydantic AI handles the LLM output contract.**

------

## Langfuse — **Non-Negotiable, Already Decided**

This one was already in the PRD. But let me state clearly *why* it's non-negotiable for a guardian specifically:

A dashboard tool tells you "latency was 2.3s." Langfuse tells you "the guardian message for `silent_churn_death` had 94% hallucination rate on the urgency_horizon field across 12 tenants last week." That's the difference between infra monitoring and LLM quality monitoring.

For a guardian product where **trust is the entire moat**, you cannot operate without knowing whether your LLM is drifting from the guardian tone or inventing numbers. Langfuse is how you catch that before a founder does.

**Recommendation: Langfuse stays. No change.**

------

## HTMX UI — **Yes, but Scope It Correctly**

The PRD says Slack-first, no dashboard. That's correct for the *founder-facing product*. But you need an internal UI for:

1. **Tenant onboarding status** — which integrations are connected, what's failing
2. **Guardian watchlist management** — view/tune thresholds per tenant
3. **LLMOps dashboard** — Langfuse is the LLM layer, but you need a product-level view of alert quality, founder acknowledgement rates, eval scores
4. **HITL review queue** — Tier 2 and Tier 3 alerts waiting for human review need a UI, not just a Slack channel

HTMX is the right call here. Reasons:

```
text✅ Python backend already (FastAPI) — HTMX is native to this
✅ No React/Next.js build complexity for an internal tool
✅ Server-side rendering means no API layer to maintain separately
✅ Partial page updates perfect for live guardian alert feeds
✅ Ships in days not weeks
```

The scope is **internal ops dashboard only**, not a founder-facing product. The founder never logs in — everything goes to Slack. This UI is for you.

**Recommendation: Add HTMX for internal ops dashboard. Keep Slack as the only founder-facing surface.**

------

## Revised Stack Decision Table

| Component            | Decision           | Reason                                                       |
| -------------------- | ------------------ | ------------------------------------------------------------ |
| **Neo4j + Graphiti** | ✅ **Keep/Restore** | Temporal graph memory is the moat. Kuzu can't do episodic temporal edges. |
| **Kuzu**             | ❌ **Drop**         | Replaced by Neo4j + Graphiti entirely                        |
| **LangGraph**        | ✅ **Keep**         | Agent state machine. Already working.                        |
| **Pydantic AI**      | ✅ **Add**          | Enforces guardian message contract. Retries malformed LLM output. |
| **DSPy**             | ✅ **Keep**         | Prompt optimization layer. Pydantic AI handles output validation, DSPy handles prompt quality. Not competing. |
| **Langfuse**         | ✅ **Keep**         | LLM quality monitoring. Non-negotiable for a trust-based product. |
| **HTMX**             | ✅ **Add**          | Internal ops dashboard only. Founder never sees it.          |
| **Redis**            | ✅ **Keep**         | L1 working memory.                                           |
| **Temporal**         | ✅ **Keep**         | Workflow durability.                                         |
| **Qdrant**           | ✅ **Keep**         | Vector memory L2 + L5.                                       |

------

## What Actually Changes in the LLD

## 1. Graphiti replaces Kuzu as L3

```
python# memory/semantic.py — now uses Graphiti
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

class SemanticMemory:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        self.graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)

    async def write(self, tenant_id: str, payload: dict) -> str:
        # Graphiti handles entity extraction, deduplication,
        # temporal edge creation automatically
        await self.graphiti.add_episode(
            name=payload.get("event_type", "guardian_event"),
            episode_body=json.dumps(payload),
            source=EpisodeType.json,
            source_description=f"tenant:{tenant_id}",
            group_id=tenant_id     # tenant isolation via group_id
        )

    async def search(self, tenant_id: str, query: str) -> list:
        results = await self.graphiti.search(
            query=query,
            group_ids=[tenant_id]  # strict tenant isolation
        )
        return results
```

## 2. Pydantic AI wraps every guardian output

```
python# agents/finance/graph.py — ADD this node
from pydantic_ai import Agent
from pydantic import BaseModel, field_validator

class GuardianOutput(BaseModel):
    pattern_name: str
    insight: str
    urgency_horizon: str
    one_action: str
    injected_numbers: list[str]   # audit: what was injected vs generated

    @field_validator('insight')
    def max_200_words(cls, v):
        if len(v.split()) > 200:
            raise ValueError('Guardian message exceeds 200 words')
        return v

    @field_validator('insight')
    def no_number_generation(cls, v, values):
        # Guardian must use injected numbers only
        # This validator is a soft check — Langfuse catches hard cases
        return v

guardian_agent = Agent(
    model='openai:gpt-4o-mini',
    result_type=GuardianOutput,
    system_prompt=GUARDIAN_TONE_INSTRUCTION
)

# Retries automatically if output doesn't match GuardianOutput schema
result = await guardian_agent.run(prompt)
```

## 3. HTMX internal dashboard routes

```
python# apps/ai/src/dashboard/routes.py (new file)
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/internal")

@router.get("/alerts", response_class=HTMLResponse)
async def alerts_dashboard(request: Request):
    # Returns full page on first load, HTMX partial on subsequent
    alerts = await get_recent_alerts()
    return templates.TemplateResponse("alerts.html", {
        "alerts": alerts,
        "hx_request": request.headers.get("HX-Request")
    })

@router.get("/watchlist", response_class=HTMLResponse)
async def watchlist_status():
    # Live view: which patterns have fired per tenant
    ...

@router.get("/hitl-queue", response_class=HTMLResponse)
async def hitl_queue():
    # Tier 2 + 3 alerts waiting for review
    ...

@router.get("/eval-scores", response_class=HTMLResponse)
async def eval_scores():
    # Weekly guardian quality scores from Langfuse
    ...
```

------

## The One-Line Stack Summary (Updated)

```
textGo (webhooks) → Redpanda (events) → Temporal (workflows)
→ LangGraph (agent flow) → Pydantic AI (output contract)
→ DSPy (prompt quality) → Langfuse (LLM observability)
→ Graphiti + Neo4j (temporal memory graph)
→ Qdrant (vector memory) → Redis (working memory)
→ PostgreSQL (structured data) → Slack (delivery)
→ HTMX (internal ops only)
```

Every component earns its place. Nothing is there for CV-driven development. The additions — Graphiti, Pydantic AI, HTMX — each solve a specific gap in the guardian's ability to be trustworthy, structured, and operable.