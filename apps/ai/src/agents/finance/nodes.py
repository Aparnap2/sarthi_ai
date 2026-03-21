"""
Finance Agent Nodes for Sarthi v1.0.

Implements 9 node functions for the LangGraph state machine:
  N1: node_ingest_event       — Validate and normalize incoming event
  N2: node_update_snapshot    — Query PostgreSQL for revenue, expenses, burn, runway
  N3: node_load_vendor_baseline — Load 90-day spend baseline for vendor
  N4: node_detect_anomaly     — Score-based anomaly detection (no LLM)
  N5: node_query_memory       — Query Qdrant finance_memory for similar past anomalies
  N6: node_reason_and_explain — LLM explains anomaly via DSPy ChainOfThought
  N7: node_decide_action      — ALERT | DIGEST | SKIP
  N8: node_write_memory       — Write event + explanation to Qdrant
  N9: node_emit_output        — Format output_message for Telegram

All nodes are pure functions: FinanceState → FinanceState
"""
import os
import uuid
import json
import dspy
import psycopg2
import requests
from contextlib import contextmanager
from typing import List, Dict, Any

from .state import FinanceState
from .prompts import AnomalyExplainer, FinanceDigestWriter

# ── Environment ───────────────────────────────────────────────────
DATABASE_URL      = os.getenv("DATABASE_URL",
    "postgresql://sarthi:sarthi @localhost:5433/sarthi")
QDRANT_URL        = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:0.6b")
EMBED_MODEL       = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

# ── DSPy — wired to local Ollama, no external API ────────────────
_dspy_lm = dspy.LM(
    model=f"ollama_chat/{OLLAMA_CHAT_MODEL}",
    api_base="http://localhost:11434",
    api_key="ollama",
    max_tokens=200,
    temperature=0.1,
)
dspy.configure(lm=_dspy_lm)
explainer = dspy.ChainOfThought(AnomalyExplainer)
digester  = dspy.ChainOfThought(FinanceDigestWriter)

# ── Postgres helper ───────────────────────────────────────────────
@contextmanager
def _pg():
    """Context manager for PostgreSQL connection."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def _normalize_vendor(event: Dict) -> str:
    """
    Extract normalized vendor name from event.

    Uses vendor field if present, falls back to description.
    Strips whitespace and converts to lowercase for consistent matching.

    Args:
        event: Event dict with vendor and/or description fields

    Returns:
        Normalized vendor string
    """
    vendor = (event.get("vendor") or
              event.get("description") or
              "unknown").strip().lower()
    return vendor if vendor else "unknown"


# ── Qdrant embed + search helpers ────────────────────────────────
def _embed(text: str) -> List[float]:
    """Embed using nomic-embed-text via Ollama REST."""
    # Build URL from configured OLLAMA_BASE_URL
    embed_url = OLLAMA_BASE_URL.rstrip('/') + '/api/embeddings'
    r = requests.post(
        embed_url,
        json={"model": EMBED_MODEL, "input": text},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    embeddings = data.get("embeddings") or data.get("embedding")
    if isinstance(embeddings, list) and len(embeddings) > 0 and isinstance(embeddings[0], list):
        return embeddings[0]
    return embeddings if isinstance(embeddings, list) else []


def _qdrant_search(collection: str, vector: List[float],
                   tenant_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Search Qdrant collection with tenant filter."""
    r = requests.post(
        f"{QDRANT_URL}/collections/{collection}/points/search",
        json={
            "vector": vector,
            "limit": top_k,
            "score_threshold": 0.55,
            "filter": {
                "must": [{"key": "tenant_id", "match": {"value": tenant_id}}]
            },
            "with_payload": True,
        },
        timeout=15,
    )
    if r.status_code != 200:
        return []
    return r.json().get("result", [])


def _qdrant_upsert(collection: str, point_id: str,
                   vector: List[float], payload: Dict[str, Any]) -> None:
    """Upsert a single point into Qdrant."""
    r = requests.put(
        f"{QDRANT_URL}/collections/{collection}/points",
        json={"points": [{
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id)),
            "vector": vector,
            "payload": payload,
        }]},
        timeout=15,
    )
    r.raise_for_status()

# ─────────────────────────────────────────────────────────────────
# NODE FUNCTIONS
# Each takes FinanceState, returns updated FinanceState dict.
# ─────────────────────────────────────────────────────────────────

def node_ingest_event(state: FinanceState) -> Dict:
    """
    N1: Validate and normalize incoming event.

    Validates:
    - event_type and tenant_id present
    - event tenant_id matches state tenant_id

    Args:
        state: Current FinanceState

    Returns:
        Updated FinanceState with normalized event

    Raises:
        ValueError: If event missing required fields or tenant mismatch
    """
    event = state["event"]
    required = {"event_type", "tenant_id"}
    missing = required - set(event.keys())
    if missing:
        raise ValueError(f"Event missing required fields: {missing}")

    # Validate tenant_id consistency
    if event.get("tenant_id") != state["tenant_id"]:
        raise ValueError(
            f"Event tenant_id '{event.get('tenant_id')}' does not match "
            f"state tenant_id '{state['tenant_id']}'"
        )

    # Normalize amount to float
    if "amount" in event:
        event = {**event, "amount": float(event["amount"])}

    return {**state, "event": event}


def node_update_snapshot(state: FinanceState) -> Dict:
    """
    N2: Query PostgreSQL for revenue, expenses, burn, runway.
    
    Note: transactions table uses debit/credit columns (not amount/type).
    Revenue = SUM(credit), Expenses = SUM(debit)
    
    Args:
        state: Current FinanceState
        
    Returns:
        Updated FinanceState with monthly_revenue, monthly_expense,
        burn_rate, runway_months
    """
    tid = state["tenant_id"]

    with _pg() as conn:
        with conn.cursor() as cur:
            # 30d revenue (credits)
            cur.execute("""
                SELECT COALESCE(SUM(credit), 0) FROM transactions
                WHERE tenant_id = %s
                  AND txn_date >= NOW() - INTERVAL '30 days'
            """, (tid,))
            monthly_revenue = float(cur.fetchone()[0])

            # 30d expenses (debits)
            cur.execute("""
                SELECT COALESCE(SUM(debit), 0) FROM transactions
                WHERE tenant_id = %s
                  AND txn_date >= NOW() - INTERVAL '30 days'
            """, (tid,))
            monthly_expense = float(cur.fetchone()[0])

            # Cash balance from latest snapshot
            cur.execute("""
                SELECT runway_months FROM finance_snapshots
                WHERE tenant_id = %s
                ORDER BY snapshot_date DESC LIMIT 1
            """, (tid,))
            row = cur.fetchone()
            runway_months = float(row[0]) if row else 99.0

    burn_rate = monthly_expense if monthly_expense > 0 else 1.0

    return {
        **state,
        "monthly_revenue": monthly_revenue,
        "monthly_expense": monthly_expense,
        "burn_rate": burn_rate,
        "runway_months": min(runway_months, 99.0),
    }


def node_load_vendor_baseline(state: FinanceState) -> Dict:
    """
    N3: Load 90-day spend baseline for the event vendor.

    Args:
        state: Current FinanceState

    Returns:
        Updated FinanceState with vendor_baselines dict
    """
    event     = state["event"]
    vendor    = _normalize_vendor(event)
    tid       = state["tenant_id"]
    baselines = dict(state.get("vendor_baselines") or {})

    with _pg() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT avg_30d, avg_90d, transaction_count
                FROM vendor_baselines
                WHERE tenant_id = %s AND vendor_name = %s
            """, (tid, vendor))
            row = cur.fetchone()

    if row:
        baselines[vendor] = {
            "avg_30d": float(row[0] or 0),
            "avg_90d": float(row[1] or 0),
            "count": int(row[2] or 0),
        }
    else:
        baselines[vendor] = {"avg_30d": 0.0, "avg_90d": 0.0, "count": 0}

    return {**state, "vendor_baselines": baselines}


def node_detect_anomaly(state: FinanceState) -> Dict:
    """
    N4: Score-based anomaly detection. Pure logic — no LLM.

    Scoring rules:
    - Spend >= 2.0x baseline: +0.5
    - Spend >= 1.5x baseline: +0.3
    - First-time vendor (count=0): +0.3
    - Runway < 3 months: +0.5
    - Runway < 6 months: +0.2
    - Revenue drop on TIME_TICK: +0.3

    Args:
        state: Current FinanceState

    Returns:
        Updated FinanceState with anomaly_detected, anomaly_score
    """
    event      = state["event"]
    etype      = event.get("event_type", "")
    vendor     = _normalize_vendor(event)
    amount     = float(event.get("amount", 0))
    baselines  = state.get("vendor_baselines") or {}
    baseline   = baselines.get(vendor, {})
    avg_90d    = float(baseline.get("avg_90d", 0))
    count      = int(baseline.get("count", 0))
    runway     = float(state.get("runway_months", 99))
    score      = 0.0

    # Spend anomaly rules
    if avg_90d > 0:
        multiple = amount / avg_90d
        if multiple >= 2.0:
            score += 0.5
        elif multiple >= 1.5:
            score += 0.3
    
    # First-time vendor
    if count == 0 and amount > 0:
        score += 0.3

    # Runway urgency
    if runway < 3:
        score += 0.5
    elif runway < 6:
        score += 0.2

    # Revenue drop on weekly tick
    if "TIME_TICK" in etype:
        rev = state.get("monthly_revenue", 0)
        exp = state.get("monthly_expense", 0)
        if rev == 0 and exp > 0:
            score += 0.3

    score = round(min(score, 1.0), 2)
    return {
        **state,
        "anomaly_detected": score >= 0.5,
        "anomaly_score": score,
    }


def node_query_memory(state: FinanceState) -> Dict:
    """
    N5: Query Qdrant finance_memory for similar past anomalies.
    
    Args:
        state: Current FinanceState
        
    Returns:
        Updated FinanceState with past_context list
    """
    event  = state["event"]
    vendor = (event.get("vendor") or "unknown").strip()
    amount = float(event.get("amount", 0))

    query_text = f"anomaly {vendor} spend spike {amount:,.0f}"
    try:
        vector  = _embed(query_text)
        results = _qdrant_search("finance_memory", vector,
                                  state["tenant_id"], top_k=3)
        past = [
            r["payload"].get("content", "")
            for r in results
            if r.get("payload", {}).get("content")
        ]
    except Exception:
        past = []

    return {**state, "past_context": past}


def node_reason_and_explain(state: FinanceState) -> Dict:
    """
    N6: LLM explains anomaly via DSPy ChainOfThought.
    
    Falls back to deterministic explanation if LLM fails.
    
    Args:
        state: Current FinanceState
        
    Returns:
        Updated FinanceState with anomaly_explanation
    """
    if not state.get("anomaly_detected"):
        return {**state, "anomaly_explanation": ""}

    event    = state["event"]
    vendor   = (event.get("vendor") or "unknown").strip()
    amount   = float(event.get("amount", 0))
    baseline = (state.get("vendor_baselines") or {}).get(vendor, {})
    avg_90d  = float(baseline.get("avg_90d", 0))
    past     = state.get("past_context") or []
    past_str = "\n".join(past) if past else "No history for this vendor."

    try:
        result = explainer(
            event_type=event.get("event_type", "BANK_WEBHOOK"),
            vendor=vendor,
            amount=amount,
            avg_90d=avg_90d,
            anomaly_score=state.get("anomaly_score", 0),
            past_context=past_str,
            runway_months=state.get("runway_months", 99),
        )
        explanation = result.explanation.strip()
    except Exception as e:
        # Fallback: deterministic explanation — no LLM crash stops the graph
        multiple = (amount / avg_90d) if avg_90d > 0 else 0
        explanation = (
            f"{vendor}: {amount:,.0f} is "
            f"{'%.1fx usual' % multiple if multiple > 0 else 'a new vendor'}. "
            f"Runway is {state.get('runway_months', 99):.1f} months. "
            f"Check recent {vendor} usage."
        )

    return {**state, "anomaly_explanation": explanation}


def node_decide_action(state: FinanceState) -> Dict:
    """
    N7: Decide action: ALERT | DIGEST | SKIP.
    
    Rules:
    - anomaly_score >= 0.7 → ALERT
    - TIME_TICK_WEEKLY or TIME_TICK_DAILY → DIGEST
    - Otherwise → SKIP
    
    Args:
        state: Current FinanceState
        
    Returns:
        Updated FinanceState with action
    """
    etype = state["event"].get("event_type", "")
    score = state.get("anomaly_score", 0.0)

    if score >= 0.7:
        action = "ALERT"
    elif "TIME_TICK_WEEKLY" in etype or "TIME_TICK_DAILY" in etype:
        action = "DIGEST"
    else:
        action = "SKIP"

    return {**state, "action": action}


def node_write_memory(state: FinanceState) -> Dict:
    """
    N8: Write event + explanation to Qdrant finance_memory.
    
    SKIP action → no-op (returns state unchanged)
    
    Args:
        state: Current FinanceState
        
    Returns:
        Updated FinanceState (unchanged if SKIP)
    """
    if state.get("action") == "SKIP":
        return state

    event       = state["event"]
    vendor      = (event.get("vendor") or "unknown").strip()
    amount      = float(event.get("amount", 0))
    score       = state.get("anomaly_score", 0)
    explanation = state.get("anomaly_explanation", "")
    tid         = state["tenant_id"]
    action      = state.get("action", "SKIP")

    content = (
        f"{vendor}: {amount:,.0f} | score={score} | {action} | "
        f"{explanation or 'routine event'}"
    )

    try:
        vector   = _embed(content)
        point_id = f"{tid}-{vendor}-{event.get('event_type', '')}-{amount}"
        _qdrant_upsert(
            collection="finance_memory",
            point_id=point_id,
            vector=vector,
            payload={
                "tenant_id": tid,
                "content": content,
                "vendor": vendor,
                "amount": amount,
                "anomaly_score": score,
                "action": action,
                "memory_type": "finance_anomaly",
            },
        )
    except Exception:
        pass   # Memory write failure must not stop workflow

    return state


def node_emit_output(state: FinanceState) -> Dict:
    """
    N9: Format output_message for Telegram.
    
    ALERT: 🔴 or 🟡 Finance Alert with explanation
    DIGEST: 📊 Weekly Finance Brief with numbers
    SKIP: Empty message
    
    Args:
        state: Current FinanceState
        
    Returns:
        Updated FinanceState with output_message
    """
    action  = state.get("action", "SKIP")
    event   = state["event"]
    vendor  = (event.get("vendor") or "unknown").strip()
    amount  = float(event.get("amount", 0))
    score   = state.get("anomaly_score", 0)
    explain = state.get("anomaly_explanation", "")
    runway  = state.get("runway_months", 99)
    burn    = state.get("burn_rate", 0)
    revenue = state.get("monthly_revenue", 0)

    if action == "ALERT":
        icon = "🔴" if score >= 0.8 else "🟡"
        msg = (
            f"{icon} *Finance Alert*\n\n"
            f"{explain}\n\n"
            f"Vendor: {vendor} | Amount: {amount:,.0f}\n"
            f"Runway: {runway:.1f} months"
        )
    elif action == "DIGEST":
        msg = (
            f"📊 *Weekly Finance Brief*\n\n"
            f"🟢 Revenue (30d): {revenue:,.0f}\n"
            f"🔴 Burn (30d): {burn:,.0f}\n"
            f"⏱ Runway: {runway:.1f} months"
        )
    else:
        msg = ""

    return {**state, "output_message": msg}
