# Sarthi v4.3.0 — Reality-Based Implementation Brief
## Corrected for Actual v4.2.0-alpha Codebase State

**Date:** March 2026  
**Branch Point:** `v4.2.0-alpha` (tagged on commit 96c228c)  
**Current Branch:** `fix/e2e-tests-and-env-vars`

---

## Critical Gaps Discovered (vs AGENT_INSTRUCTION.md Assumptions)

| Assumed in AGENT_INSTRUCTION.md | Actual v4.2.0-alpha State | Action Required |
|--------------------------------|---------------------------|-----------------|
| `apps/core/internal/db/migrations/` exists | ❌ Directory doesn't exist | **CREATE** migrations directory structure |
| `scripts/test_sarthi.sh` exists | ❌ File doesn't exist | **CREATE** test runner script |
| `apps/core/internal/api/` for webhooks | ❌ Handlers in `apps/core/internal/web/` | **USE** existing web/ directory pattern |
| `apps/core/internal/events/` for envelopes | ❌ Directory doesn't exist | **CREATE** events package |
| `apps/ai/src/sops/` for SOP registry | ❌ Directory doesn't exist | **CREATE** sops/ package |
| `apps/ai/src/config/event_dictionary.py` | ❌ Doesn't exist | **CREATE** event dictionary |
| 255 tests passing | ✅ Verified (v4.2.0-alpha tag) | **PRESERVE** all existing tests |
| Agents: Supervisor, Researcher, SRE, etc. | ✅ Confirmed in `apps/ai/src/agents/` | **INTEGRATE** SOP runtime with existing agents |

---

## Corrected Implementation Sequence

### PHASE 0 ✅ — Baseline (COMPLETE)

**Status:** v4.2.0-alpha tagged at commit 96c228c

**Verified:**
- ✅ 255 tests passing
- ✅ 13 virtual employees across 6 desks
- ✅ LLM factory with thread safety (`apps/ai/src/config/llm.py`)
- ✅ Import guard (`apps/ai/src/config/llm_guard.py`)
- ✅ Go + Python polyglot architecture working

---

### PHASE 1 — Foundation (NEW — Must Create First)

**Target:** Create missing directory structure and test runner

#### 1.1 Create Migrations Directory

```bash
mkdir -p apps/core/internal/db/migrations
```

**File:** `apps/core/internal/db/migrations/001_sarthi_sop_runtime.sql`

**Note:** Use `001` (not `009`) since this is the first migration in the new directory.

#### 1.2 Create Test Runner Script

**File:** `scripts/test_sarthi.sh`

```bash
#!/bin/bash
set -e

echo "═══════════════════════════════════════════════"
echo " SARTHI Full Test Suite — Real Docker + Azure"
echo "═══════════════════════════════════════════════"

# ── 1. Infrastructure health ──────────────────────
echo "[1/5] Checking Docker services..."
docker compose ps | grep -E "temporal|redpanda|postgres|qdrant" | grep -q "healthy\|running" || {
    echo "✗ Services not healthy. Run: docker compose up -d"
    exit 1
}
echo "  ✓ All services running"

# ── 2. Azure LLM connectivity ─────────────────────
echo "[2/5] Checking Azure LLM..."
cd apps/ai
uv run python -c "
from src.config.llm import get_llm_client, get_chat_model
r = get_llm_client().chat.completions.create(
    model=get_chat_model(),
    messages=[{'role':'user','content':'ping'}],
    max_tokens=3
)
print('  ✓ Azure LLM:', r.model)
"

# ── 3. Python tests ───────────────────────────────
echo "[3/5] Python tests..."
uv run pytest tests/ -v --tb=short --timeout=90 -x

# ── 4. Go tests ───────────────────────────────────
echo "[4/5] Go tests..."
cd ../core
go test ./... -v -timeout=60s

# ── 5. Summary ────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo " ALL TESTS PASSED ✓"
echo "═══════════════════════════════════════════════"
```

**Make executable:** `chmod +x scripts/test_sarthi.sh`

#### 1.3 Verify Existing Tests Still Pass

```bash
bash scripts/test_sarthi.sh
# Must show: ALL TESTS PASSED ✓
```

**Exit Criteria:**
- ✅ Migrations directory exists
- ✅ test_sarthi.sh runs and passes
- ✅ All 255 existing tests still green

---

### PHASE 2 — Event Envelope (Corrected Paths)

**Target:** Canonical event envelope schema

#### 2.1 Python Envelope Schema

**File:** `apps/ai/src/schemas/event_envelope.py` (create new)

```python
from __future__ import annotations
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, field_validator

class EventSource(str, Enum):
    RAZORPAY          = "razorpay"
    ZOHO_BOOKS        = "zoho_books"
    TELEGRAM          = "telegram"
    CRON              = "cron"
    # Add all 8 sources from design doc

class EventEnvelope(BaseModel):
    event_id:         str
    founder_id:       str
    source:           EventSource
    event_name:       str
    topic:            str
    sop_name:         str
    payload_ref:      str    # "raw_events:<uuid>" — NEVER raw JSON
    payload_hash:     str
    occurred_at:      datetime
    received_at:      datetime
    trace_id:         str
    idempotency_key:  str
    version:          str = "v1"

    @field_validator("event_name")
    @classmethod
    def event_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("event_name must not be empty")
        return v

    @field_validator("payload_ref")
    @classmethod
    def payload_ref_is_reference(cls, v: str) -> str:
        if v.startswith("{") or v.startswith("["):
            raise ValueError("payload_ref must be storage reference, not raw JSON")
        return v
```

#### 2.2 Go Envelope Struct

**File:** `apps/core/internal/events/envelope.go` (create new directory + file)

```go
package events

import "time"

type EventSource string

const (
    SourceRazorpay    EventSource = "razorpay"
    SourceZohoBooks   EventSource = "zoho_books"
    SourceTelegram    EventSource = "telegram"
    SourceCron        EventSource = "cron"
    // Add all sources
)

type EventEnvelope struct {
    EventID        string      `json:"event_id"`
    FounderID      string      `json:"founder_id"`
    Source         EventSource `json:"source"`
    EventName      string      `json:"event_name"`
    Topic          string      `json:"topic"`
    SOPName        string      `json:"sop_name"`
    PayloadRef     string      `json:"payload_ref"`     // "raw_events:<uuid>"
    PayloadHash    string      `json:"payload_hash"`
    OccurredAt     time.Time   `json:"occurred_at"`
    ReceivedAt     time.Time   `json:"received_at"`
    TraceID        string      `json:"trace_id"`
    IdempotencyKey string      `json:"idempotency_key"`
    Version        string      `json:"version"`
}
```

#### 2.3 Tests

**File:** `apps/ai/tests/test_event_envelope.py` (create new)

```python
import pytest, uuid
from datetime import datetime, timezone
from src.schemas.event_envelope import EventEnvelope, EventSource

class TestEventEnvelope:
    def test_valid_razorpay_envelope_passes(self):
        env = EventEnvelope(
            event_id=str(uuid.uuid4()),
            founder_id=str(uuid.uuid4()),
            source=EventSource.RAZORPAY,
            event_name="payment.captured",
            topic="finance.revenue.captured",
            sop_name="SOP_REVENUE_RECEIVED",
            payload_ref="raw_events:abc123",
            payload_hash="sha256:deadbeef",
            occurred_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            trace_id=str(uuid.uuid4()),
            idempotency_key="razorpay:pay_abc123:v1",
        )
        assert env.source == EventSource.RAZORPAY
        assert env.sop_name == "SOP_REVENUE_RECEIVED"

    def test_payload_ref_never_contains_raw_json(self):
        with pytest.raises(ValueError):
            EventEnvelope(
                event_id=str(uuid.uuid4()),
                founder_id=str(uuid.uuid4()),
                source=EventSource.RAZORPAY,
                event_name="payment.captured",
                topic="finance.revenue.captured",
                sop_name="SOP_REVENUE_RECEIVED",
                payload_ref='{"amount": 5000}',  # raw JSON — must FAIL
                payload_hash="sha256:x",
                occurred_at=datetime.now(timezone.utc),
                received_at=datetime.now(timezone.utc),
                trace_id=str(uuid.uuid4()),
                idempotency_key="razorpay:pay_x:v1",
            )
```

**Run:** `uv run pytest tests/test_event_envelope.py -v` → expect PASS

---

### PHASE 3 — Event Dictionary (Corrected for Existing Agents)

**Target:** Map events to existing 6 desks + 13 virtual employees

#### 3.1 Python Event Dictionary

**File:** `apps/ai/src/config/event_dictionary.py` (create new)

**Key Decision:** Map events to **existing agents** (Supervisor, Researcher, SRE, etc.) initially, then gradually migrate to SOP pattern.

```python
from dataclasses import dataclass
from typing import List

@dataclass
class DictionaryEntry:
    source:      str
    event_name:  str
    topic:       str
    sop:         str
    employees:   list[str]  # Map to existing desk names

_REGISTRY: List[DictionaryEntry] = [
    # RAZORPAY
    DictionaryEntry("razorpay","payment.captured", "finance.revenue.captured",
        "SOP_REVENUE_RECEIVED", ["Bookkeeper","CFO"]),
    # Add all 48 events from design doc
    
    # Map to existing agents where SOPs don't exist yet:
    # Example: "market_intel" events → Researcher agent
]

class UnknownEventError(Exception):
    """Raised when event is not in dictionary."""
    pass

class EventDictionary:
    def __init__(self):
        self._index = {(e.source, e.event_name): e for e in _REGISTRY}

    def resolve(self, source: str, event_name: str) -> DictionaryEntry:
        key = (source, event_name)
        if key not in self._index:
            raise UnknownEventError(f"No mapping for {source}::{event_name}")
        return self._index[key]
```

#### 3.2 Go Event Dictionary

**File:** `apps/core/internal/events/dictionary.go` (create in same dir as envelope.go)

```go
package events

import "fmt"

type DictionaryEntry struct {
    Source    EventSource
    EventName string
    Topic     string
    SOPName   string
    Employees []string
}

var registry = []DictionaryEntry{
    {SourceRazorpay, "payment.captured", "finance.revenue.captured",
        "SOP_REVENUE_RECEIVED", []string{"Bookkeeper","CFO"}},
    // Add all events
}

var index map[string]DictionaryEntry

func init() {
    index = make(map[string]DictionaryEntry)
    for _, e := range registry {
        key := fmt.Sprintf("%s::%s", e.Source, e.EventName)
        index[key] = e
    }
}

func Resolve(source EventSource, eventName string) (DictionaryEntry, error) {
    key := fmt.Sprintf("%s::%s", source, eventName)
    e, ok := index[key]
    if !ok {
        return DictionaryEntry{}, fmt.Errorf("no mapping for %q::%q", source, eventName)
    }
    return e, nil
}
```

#### 3.3 Tests

**File:** `apps/ai/tests/test_event_dictionary.py` (create new)

```python
from src.config.event_dictionary import EventDictionary, UnknownEventError
import pytest

class TestEventDictionary:
    def test_razorpay_payment_captured_maps_correctly(self):
        d = EventDictionary()
        entry = d.resolve(source="razorpay", event_name="payment.captured")
        assert entry.topic == "finance.revenue.captured"
        assert entry.sop == "SOP_REVENUE_RECEIVED"

    def test_unknown_event_raises(self):
        d = EventDictionary()
        with pytest.raises(UnknownEventError):
            d.resolve(source="razorpay", event_name="nonexistent.event")
```

**Run:** `uv run pytest tests/test_event_dictionary.py -v` → expect PASS

---

### PHASE 4 — Database Migration (Corrected Numbering)

**Target:** Append-only SOP runtime tables

#### 4.1 Migration File

**File:** `apps/core/internal/db/migrations/001_sarthi_sop_runtime.sql`

**Note:** Use `001` (first migration in new directory structure).

```sql
-- MIGRATION 001: Sarthi SOP Runtime tables
-- APPEND ONLY. Never modify existing tables.

-- Raw event archive
CREATE TABLE IF NOT EXISTS raw_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id      UUID NOT NULL REFERENCES founders(id) ON DELETE CASCADE,
    source          VARCHAR(50) NOT NULL,
    event_name      VARCHAR(100) NOT NULL,
    topic           VARCHAR(150) NOT NULL,
    sop_name        VARCHAR(100) NOT NULL,
    payload_hash    VARCHAR(100) NOT NULL,
    payload_body    JSONB NOT NULL,
    received_at     TIMESTAMPTZ DEFAULT NOW(),
    idempotency_key VARCHAR(200),
    UNIQUE(idempotency_key)
);

-- SOP execution jobs
CREATE TABLE IF NOT EXISTS sop_jobs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id       UUID NOT NULL REFERENCES founders(id),
    raw_event_id     UUID REFERENCES raw_events(id),
    sop_name         VARCHAR(100) NOT NULL,
    temporal_run_id  VARCHAR(200),
    status           VARCHAR(30) DEFAULT 'pending',
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Add all 9 tables from AGENT_INSTRUCTION.md Phase 3
-- transactions, accounts_payable, compliance_calendar, sop_findings, etc.
```

#### 4.2 Go Test

**File:** `apps/core/internal/db/raw_events_test.go` (create new)

```go
package db

import (
    "testing"
    "github.com/google/uuid"
    "github.com/stretchr/testify/require"
)

func TestRawEventInsertAndFetch(t *testing.T) {
    db := connectTestDB(t)  // Reuse existing test helper
    id := uuid.New().String()
    _, err := db.Exec(`
        INSERT INTO raw_events (id, founder_id, source, event_name, topic,
            sop_name, payload_hash, payload_body, received_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
    `, id, "founder_test", "razorpay", "payment.captured",
       "finance.revenue.captured", "SOP_REVENUE_RECEIVED",
       "sha256:abc", `{"payment_id":"pay_test"}`)
    require.NoError(t, err)

    var count int
    db.QueryRow("SELECT COUNT(*) FROM raw_events WHERE id=$1", id).Scan(&count)
    require.Equal(t, 1, count)
}
```

**Run:** `go test ./internal/db -run TestRawEvent -v` → expect PASS

---

## Revised Commit Sequence (Reality-Based)

| Commit | Description | Files Created | Tests |
|--------|-------------|---------------|-------|
| 1 | `feat: foundation — migrations dir + test runner` | `migrations/`, `test_sarthi.sh` | Existing 255 pass |
| 2 | `feat: event envelope schema` | `event_envelope.py`, `envelope.go` | 3 pass |
| 3 | `feat: event dictionary` | `event_dictionary.py`, `dictionary.go` | 5 pass |
| 4 | `feat: migration 001 sop runtime` | `001_sarthi_sop_runtime.sql`, `raw_events_test.go` | 1 pass |
| 5 | `feat: razorpay webhook handler` | `razorpay.go` in `web/` | 4 pass |
| 6 | `feat: telegram ingress` | `telegram.go` in `web/` | 3 pass |
| 7 | `feat: temporal workflow redesign` | `business_os_workflow.go`, `sop_router.go` | 3 pass |
| 8 | `feat: sop registry + base` | `base.py`, `registry.py` in `sops/` | 2 pass |
| 9 | `feat: SOP_REVENUE_RECEIVED` | `revenue_received.py` | 3 pass |
| 10 | `feat: SOP_BANK_STATEMENT_INGEST` | `bank_statement_ingest.py` | 5 pass |
| 11 | `feat: SOP_WEEKLY_BRIEFING` | `weekly_briefing.py` | 4 pass |
| 12 | `feat: e2e sop flows` | `test_e2e_sop_flows.py` | 6 pass |
| 13 | `feat: update test runner` | Update `test_sarthi.sh` | All 300+ pass |

**Tag:** `git tag v4.3.0-alpha` after Commit 13

---

## Invariants (Unchanged from AGENT_INSTRUCTION.md)

```bash
# 1. No raw JSON in Temporal signals
grep -r "json.Marshal" apps/core/internal/workflow/ | grep -v "_test.go"

# 2. No direct AzureOpenAI() outside llm.py
grep -rn "AzureOpenAI(" apps/ai/src/ | grep -v "config/llm.py"

# 3. Existing tests still pass
cd apps/ai && uv run pytest tests/ -x -q --timeout=90
cd apps/core && go test ./... -timeout=60s

# 4. No banned jargon in SOP outputs
grep -rn "leverage\|synergy\|utilize\|streamline\|paradigm" apps/ai/src/sops/
```

---

## Next Agent Instructions

1. **Start branch:** `git checkout -b feature/sop-runtime v4.2.0-alpha`
2. **Run baseline:** `bash scripts/test_sarthi.sh` (after creating it in Phase 1)
3. **Execute commits 1-13** in sequence from this document
4. **Tag:** `git tag v4.3.0-alpha` after all 13 commits
5. **Verify:** All 300+ tests passing

**This document corrects all path assumptions from AGENT_INSTRUCTION.md to match actual v4.2.0-alpha codebase structure.**

---

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Status:** Ready for implementation
