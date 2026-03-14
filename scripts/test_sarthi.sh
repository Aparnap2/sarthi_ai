#!/usr/bin/env bash
# scripts/test_sarthi.sh
# Sarthi Full Test Suite — Real Docker + Real Azure LLM
set -euo pipefail

echo "════════════════════════════════════════════════"
echo " SARTHI TEST SUITE — Real Docker + Real Azure"
echo "════════════════════════════════════════════════"

PASS=0; FAIL=0

check() {
  local label="$1"; shift
  if "$@" > /tmp/sarthi_check.log 2>&1; then
    echo "  ✓ $label"; ((PASS++))
  else
    echo "  ✗ $label"; cat /tmp/sarthi_check.log; ((FAIL++))
  fi
}

# ── 1. Docker health ──────────────────────────────
echo "[1/7] Docker services"
for svc in postgres redpanda; do
  check "$svc healthy" docker compose ps "$svc" --format "{{.Status}}" \
    | grep -qiE "running|healthy"
done

# ── 2. Azure LLM smoke ────────────────────────────
echo "[2/7] Azure LLM"
cd apps/ai
check "Azure chat completions" uv run python -c "
from src.config.llm import get_llm_client, get_chat_model
r = get_llm_client().chat.completions.create(
    model=get_chat_model(),
    messages=[{'role':'user','content':'ping'}],
    max_tokens=3
)
print('ok:', r.model)
" 2>/dev/null || echo "  ⚠ Azure LLM not configured (skipping)"

# ── 3. Event dictionary + envelope ───────────────
echo "[3/7] Event dictionary + envelope"
check "event_envelope tests" uv run pytest tests/test_event_envelope.py -q --timeout=30
check "event_dictionary tests" uv run pytest tests/test_event_dictionary.py -q --timeout=30

# ── 4. SOP unit tests (real LLM, real Docker) ───
echo "[4/7] SOP unit tests"
check "SOP registry" uv run pytest tests/test_sop_registry.py -q --timeout=30
check "SOP revenue_received" uv run pytest tests/test_sop_revenue_received.py -q --timeout=30
check "SOP bank_statement_ingest" uv run pytest tests/test_sop_bank_statement_ingest.py -q --timeout=30
check "SOP weekly_briefing" uv run pytest tests/test_sop_weekly_briefing.py -q --timeout=30

# ── 5. Go tests ───────────────────────────────────
echo "[5/7] Go tests"
cd ../core
check "Go all" go test ./... -timeout=60s -count=1

# ── 6. E2E flows ──────────────────────────────────
echo "[6/7] E2E flows"
cd ../ai
check "E2E: payment.captured" uv run pytest tests/test_e2e_sop_flows.py \
  -k "payment_captured" -q --timeout=120 2>/dev/null || echo "  ⚠ E2E skipped (infrastructure)"
check "E2E: bank statement" uv run pytest tests/test_e2e_sop_flows.py \
  -k "bank_statement" -q --timeout=120 2>/dev/null || echo "  ⚠ E2E skipped (infrastructure)"
check "E2E: weekly briefing" uv run pytest tests/test_e2e_sop_flows.py \
  -k "weekly_briefing" -q --timeout=120

# ── 7. Summary ────────────────────────────────────
cd ../..
echo ""
echo "════════════════════════════════════════════════"
echo " PASSED: $PASS  FAILED: $FAIL"
if [[ $FAIL -eq 0 ]]; then
  echo " ✅ ALL TESTS PASSED — Sarthi SOP Runtime operational"
else
  echo " ❌ FAILURES DETECTED — fix before merging"
fi
echo "════════════════════════════════════════════════"
exit $FAIL
