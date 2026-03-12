# Sarthi.ai — Testing Architecture

**Version:** 4.0  
**Date:** 2026-03-12  
**Status:** PRODUCTION READY

---

## Executive Summary

Sarthi uses a **multi-layer testing strategy** combining:

1. **Pydantic v2** — Type-safe contracts at agent boundaries
2. **DSPy** — Automatic prompt optimization with compiled modules
3. **LangGraph** — State machine testing for agent workflows
4. **pytest-asyncio** — Async test runner for Temporal + LangGraph
5. **Real Azure OpenAI** — No mocks for LLM calls
6. **Real Docker services** — PostgreSQL, Qdrant, Neo4j, Temporal

**Langfuse Note:** Langfuse v3 requires ClickHouse. For dev:
- Use Langfuse Cloud (free tier) OR
- Add ClickHouse to docker-compose OR
- Skip Langfuse tests, use pytest assertions only

---

## The Testing Stack

| Layer | Tool | Purpose | Cost |
|-------|------|---------|------|
| **E2E Orchestration** | pytest-asyncio | Async test runner | $0 OSS |
| **Agent Graphs** | LangGraph | State machine enforcement | $0 OSS |
| **Structured I/O** | Pydantic v2 | Type contracts | $0 OSS |
| **Prompt Optimization** | DSPy | Auto-optimize prompts | $0 OSS |
| **Observability** | Langfuse (optional) | Trace every node | $0 self-host / Cloud free |
| **LLM** | Azure gpt-oss-120b | Real inference | Existing |
| **Workflow** | Temporal Docker | Durable execution | $0 self-host |
| **Memory** | Qdrant Docker | Vector memory | $0 self-host |
| **DB** | PostgreSQL Docker | State | $0 self-host |

---

## Test Flow Architecture

```
TEST RUN FLOW (for every agent test):

pytest invokes test
        │
        ▼
[conftest.py] — fixtures spin up:
  → AzureOpenAI client (real, gpt-oss-120b)
  → Qdrant client (existing Docker)
  → PostgreSQL connection (existing Docker)
        │
        ▼
[DSPy] compiles the agent's LM module ONCE per session
  → optimizes prompts using training examples
  → stores compiled program (reused across tests)
        │
        ▼
[Pydantic] defines the contract for every agent output
  → CFOFinding, BIFinding, RiskAlert, etc.
  → validation happens at graph boundary — not after
        │
        ▼
[LangGraph] runs the agent graph
  → each node is a typed function
  → state machine enforces valid transitions
  → MCP tools called via standardized protocol
        │
        ▼
[pytest assertions] check:
  → Pydantic model valid (structure correct)
  → score >= threshold (quality correct)
  → graph completed (no stuck nodes)
  → Temporal workflow signal received (integration correct)
```

---

## Pydantic Contracts — All Agent Output Types

### Base Class: AgentFinding

```python
class AgentFinding(BaseModel):
    """Base class — every agent finding must inherit this"""
    agent_id: str
    founder_id: str
    severity: Severity
    fire_alert: bool
    plain_message: str = Field(min_length=20, max_length=500)
    one_action: Optional[str] = Field(default=None, max_length=200)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_hitl: bool = False

    @field_validator("plain_message")
    @classmethod
    def no_jargon(cls, v: str) -> str:
        BANNED = ["EBITDA", "DSO", "bps", "YoY", "MoM", "liquidity",
                  "receivables", "CAGR", "working capital", "burn multiple"]
        for word in BANNED:
            if word in v:
                raise ValueError(f"Jargon found in plain_message: '{word}'")
        return v
```

### Agent-Specific Findings

| Agent | Output Type | Key Fields |
|-------|-------------|------------|
| **CFO** | `CFOFinding` | runway_days, monthly_burn, runway_alert, burn_spike |
| **BI** | `BIFinding` | pattern_type, affected_segment, metric_value, metric_delta_pct |
| **Risk** | `RiskAlert` | risk_category, deadline, days_until_deadline, penalty_if_missed |
| **Finance Ops** | `FinanceOpsResult` | task_type, tasks_completed, tasks_pending_hitl, draft_messages |
| **Chief of Staff** | `ChiefOfStaffOutput` | route_to_agent, telegram_message, requires_reply, inline_keyboard |

**All outputs validated at graph boundary.** If validation fails, test fails — not an assertion.

---

## DSPy Signatures — Agent Prompt Optimization

### CFO Analysis Signature

```python
class CFOAnalysis(dspy.Signature):
    """
    Analyze financial data for a startup founder.
    Calculate runway, detect burn spikes, identify cash risks.
    Output must be in plain founder language — no financial jargon.
    """
    financial_data: str = dspy.InputField(desc="Bank transactions, balances, expenses")
    founder_context: str = dspy.InputField(desc="Business stage, goals, known context")

    runway_days: int = dspy.OutputField(desc="Days of runway remaining, integer")
    monthly_burn: float = dspy.OutputField(desc="Average monthly burn in INR")
    fire_alert: bool = dspy.OutputField(desc="True if runway < 90 days or burn spike > 20%")
    plain_message: str = dspy.OutputField(
        desc="Plain language explanation for a non-finance founder. No jargon. Max 3 sentences."
    )
    one_action: str = dspy.OutputField(desc="Single most important action to take this week")
```

### Training Examples (DSPy Bootstrap)

```python
CFO_TRAINSET = [
    dspy.Example(
        financial_data="Balance: ₹2,80,000. Burn Jan: ₹85k, Feb: ₹1,10,000, Mar: ₹1,28,000",
        founder_context="B2B SaaS, pre-revenue, 2 founders + 1 engineer",
        runway_days=66,
        monthly_burn=107666.0,
        fire_alert=True,
        plain_message="You have about 2 months of money left, and your costs are growing fast — up 50% from January to March.",
        one_action="Pause any non-essential spending this week and map out which customer you can close fastest."
    ).with_inputs("financial_data", "founder_context"),
]
```

**DSPy compiles once per test session.** Compiled module cached and reused.

---

## LangGraph Agent Graphs — CFO Agent Example

### State Definition

```python
class CFOState(TypedDict):
    founder_id: str
    founder_name: str
    financial_data: str
    founder_context: str
    raw_analysis: dict
    finding: CFOFinding | None
    error: str | None
```

### Node Functions

| Node | Purpose | Validation |
|------|---------|------------|
| `validate_input` | Check required fields | Returns error if missing |
| `run_analysis` | DSPy-optimized LLM call | Loads compiled module |
| `validate_output` | Pydantic validation | Fails test if invalid |
| `error_node` | Graceful error handling | Ends graph cleanly |

### Graph Flow

```
Entry → validate_input → (error? → END) → run_analysis → (error? → END) → validate_output → END
```

---

## Test Categories

### 1. Infrastructure Health Tests

```bash
uv run pytest tests/test_sarthi_tdd.py::TestInfrastructureHealth -v
```

**Tests:**
- Azure LLM responds (real call)
- Azure LLM returns JSON (structured output)
- Qdrant reachable (Docker container)
- Qdrant sarthi_founder_memory collection exists
- PostgreSQL reachable (Docker container)
- PostgreSQL sarthi schema exists (all tables)

### 2. Memory Agent Tests

```bash
uv run pytest tests/test_sarthi_tdd.py::TestMemoryAgent -v
```

**Tests:**
- Embed returns 1536 floats (ada-002 dimension)
- Write memory to Qdrant (upsert works)
- Semantic search finds relevant memory
- Founder isolation (no cross-founder leakage)

### 3. Chief of Staff Agent Tests

```bash
uv run pytest tests/test_sarthi_tdd.py::TestChiefOfStaffAgent -v
```

**Tests:**
- Produces plain language (no jargon)
- Routes to correct agent (classification)

### 4. Bank Statement Parser Tests

```bash
uv run pytest tests/test_sarthi_tdd.py::TestBankStatementParser -v
```

**Tests:**
- HDFC CSV parsed correctly (pandas)
- Digital PDF routes to pdfplumber (not Docling)
- Scanned PDF routes to Docling (OCR + vision)
- Docling accurate mode configured (do_cell_matching=True)
- Transaction auto-categorization (LLM)

### 5. CFO Agent Tests

```bash
uv run pytest tests/test_sarthi_tdd.py::TestCFOAgent -v
```

**Tests:**
- Runway calculation correct (math verified)
- CFO proactive alert fires on low runway (<90 days)

### 6. E2E Agent Tests (Full Stack)

```bash
uv run pytest tests/test_e2e_saarathi.py -v --timeout=120
```

**Flows:**
- Flow 1: First-time founder onboarding (6 tests)
- Flow 2: Weekly reflection → trigger → Slack (5 tests)
- Flow 3: Market signal → intervention (3 tests)
- Flow 4: Sandbox execution (3 tests)
- Flow 5: Calibration loop (3 tests)
- Flow 6: Bank parser + CFO Agent (3 tests)

### 7. LLM Eval Tests (LLM-as-Judge)

```bash
uv run pytest tests/test_llm_eval.py -v --timeout=60
```

**Evals:**
- EVAL 1: TriggerAgent output quality (5 evals)
  - Message under 4 sentences
  - Contains ₹ amounts
  - No jargon words
  - Ends with one action
  - Suppression reason specific
- EVAL 2: ToneFilter fidelity (4 evals)
  - EBITDA replaced
  - Good news celebratory
  - Bad news calm
  - Hindi contains Devanagari
- EVAL 3: ContextInterviewAgent (3 evals)
  - Extracted context matches intent
  - Confidence <0.8 for vague answers
  - ICP context_type correct
- EVAL 4: MemoryAgent pattern detection (3 evals)
  - Builder archetype from coding reflections
  - Avoidance pattern detected
  - Commitment completion rate estimated

---

## Running Tests

### Full Test Suite

```bash
cd apps/ai

# All tests (141 total)
uv run pytest tests/ -v --timeout=120

# Specific groups
uv run pytest tests/test_sarthi_tdd.py -v           # TDD tests (~106)
uv run pytest tests/test_e2e_saarathi.py -v         # E2E flows (20)
uv run pytest tests/test_llm_eval.py -v             # LLM evals (15)

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### First Run Notes

- **Docling** downloads ML models (~800MB) on first run — cached locally
- **DSPy** compiles modules once per session — cached in `compiled/`
- **Azure OpenAI** calls cost tokens — use gpt-oss-120b (cheapest)

---

## Test Count Summary

| Category | Count | Status |
|----------|-------|--------|
| **Phase 0-2 (existing)** | ~106 tests | ✅ Passing |
| **E2E flows (Phase 3 P2)** | 20 flows | ✅ Created |
| **LLM evals (Phase 3 P2)** | 15 evals | ✅ Created |
| **TOTAL** | **~141 tests** | ✅ |

---

## Langfuse Integration (Optional)

**Langfuse v3 requires:**
- PostgreSQL (existing)
- ClickHouse (new — heavy)

### Option 1: Langfuse Cloud (Recommended for Dev)

```bash
# Sign up free tier: langfuse.com
# Add to .env:
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Option 2: Self-Host with ClickHouse

```yaml
# Add to docker-compose.yml:
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "9000:9000"
    environment:
      - CLICKHOUSE_USER=clickhouse
      - CLICKHOUSE_PASSWORD=clickhouse
    volumes:
      - clickhouse_data:/var/lib/clickhouse

  langfuse:
    image: langfuse/langfuse:3
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/langfuse
      - CLICKHOUSE_HOST=clickhouse
      - CLICKHOUSE_PORT=9000
    depends_on:
      - postgres
      - clickhouse
```

### Option 3: Skip Langfuse Tests

Tests work without Langfuse — use pytest assertions only.

---

## Definition of Done

**A test passes when:**
1. ✅ Pydantic model validates (type-safe)
2. ✅ Graph completes (no stuck nodes)
3. ✅ Score >= threshold (quality)
4. ✅ No jargon in output (tone)
5. ✅ One action at end (actionable)

**A feature ships when:**
1. ✅ All tests pass (100%)
2. ✅ DSPy module compiled (optimized prompts)
3. ✅ E2E flow verified (real LLM, real Docker)
4. ✅ LLM eval score >= 0.8 (quality gate)

---

**Document Version:** 4.0  
**Last Updated:** 2026-03-12  
**Status:** ✅ PRODUCTION READY
