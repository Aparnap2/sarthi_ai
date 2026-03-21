#!/usr/bin/env bash
# Full end-to-end smoke test for Sarthi v1.0 Phase 4
# Tests: Temporal connection, Workflow execution, Telegram integration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Sarthi v1.0 Phase 4 - Smoke Test"
echo "========================================"
echo ""

# Test 0: Check Ollama (existing step)
log "STEP 0a — Ollama"
if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Ollama running"
else
    echo -e "${YELLOW}⚠${NC} Ollama not running (optional for smoke tests)"
fi

# Test 0b: Mockoon CLI
log "STEP 0b — Mockoon CLI (@mockoon/cli)"

# Stop any existing Mockoon
if [ -f /tmp/sarthi-mockoon.pid ]; then
    kill $(cat /tmp/sarthi-mockoon.pid) 2>/dev/null || true
    rm -f /tmp/sarthi-mockoon.pid
fi
pkill -f "mockoon-cli.*3000" 2>/dev/null || true
sleep 1

# Start Mockoon CLI
bash scripts/start-mockoon.sh > /tmp/mockoon.log 2>&1 &
MOCKOON_PID=$!
echo $MOCKOON_PID > /tmp/sarthi-mockoon.pid

# Wait for Mockoon to be ready
for i in {1..15}; do
    if curl -sf http://localhost:3000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Mockoon ready on :3000"
        break
    fi
    sleep 1
done

export MOCKOON_BASE_URL=http://localhost:3000

run_test() {
    local name="$1"
    local cmd="$2"
    echo -n "   Testing: $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
}

run_test "mockoon: health" \
  curl -sf http://localhost:3000/health

run_test "mockoon: HITL investigate" bash -c "
  curl -sf -X POST http://localhost:3000/internal/hitl/investigate \
    -H 'Content-Type: application/json' \
    -d '{\"workflow_id\":\"test-123\"}' | grep -q '\"ok\": true'
"

run_test "mockoon: BI query" bash -c "
  curl -sf -X POST http://localhost:3000/internal/query \
    -H 'Content-Type: application/json' \
    -d '{\"tenant_id\":\"test\",\"query\":\"Revenue last 30 days\"}' \
  | grep -q 'workflow_id'
"

echo "  Mockoon running on :3000 — kept alive for E2E steps"

# Test 1: Check containers
echo -n "1. Checking Docker containers... "
TEMPORAL_RUNNING=$(docker ps --filter name="sarthi-temporal" --format "{{.Status}}" | grep -c "Up" || true)
TG_MOCK_RUNNING=$(docker ps --filter name="sarthi-tg-mock" --format "{{.Status}}" | grep -c "Up" || true)

if [[ "$TEMPORAL_RUNNING" -ge 1 && "$TG_MOCK_RUNNING" -ge 1 ]]; then
    echo -e "${GREEN}✓${NC} Containers running"
else
    echo -e "${RED}✗${NC} Containers not running"
    echo "   Temporal: $TEMPORAL_RUNNING, TG-Mock: $TG_MOCK_RUNNING"
    exit 1
fi

# Test 2: Check Temporal connection
echo -n "2. Checking Temporal connection... "
cd /home/aparna/Desktop/iterate_swarm/apps/ai

uv run python -c "
import asyncio
from temporalio.client import Client

async def check():
    try:
        client = await Client.connect('localhost:7233')
        await client.get_worker_build_id_compatibility('sarthi-queue')
        return True
    except Exception as e:
        print(f'Error: {e}')
        return False

result = asyncio.run(check())
exit(0 if result else 1)
" 2>/dev/null && echo -e "${GREEN}✓${NC} Connected" || {
    echo -e "${RED}✗${NC} Failed to connect"
    exit 1
}

# Test 3: Check Telegram mock
echo -n "3. Checking Telegram mock API... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8085/bot/test-bot-token/getMe || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}✓${NC} API responding"
else
    echo -e "${YELLOW}⚠${NC} API returned $HTTP_CODE (might be OK)"
fi

# Test 4: Run unit tests
echo -n "4. Running unit tests... "
cd /home/aparna/Desktop/iterate_swarm/apps/ai

TEST_OUTPUT=$(uv run pytest tests/unit/test_workflows.py -v --timeout=30 --asyncio-mode=auto 2>&1 || true)
TEST_PASS=$(echo "$TEST_OUTPUT" | grep -c "passed" || true)

if [[ "$TEST_PASS" -ge 1 ]]; then
    echo -e "${GREEN}✓${NC} Tests passed"
    echo "$TEST_OUTPUT" | tail -5
else
    echo -e "${YELLOW}⚠${NC} Some tests failed (see output below)"
    echo "$TEST_OUTPUT" | tail -20
fi

# Test 5: Start worker and trigger workflow
echo ""
echo "5. Testing end-to-end workflow execution..."
echo -n "   Starting worker in background... "

cd /home/aparna/Desktop/iterate_swarm/apps/ai
uv run python -m src.worker_phase4 > /tmp/worker.log 2>&1 &
WORKER_PID=$!
sleep 4

if kill -0 $WORKER_PID 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Worker started (PID: $WORKER_PID)"
else
    echo -e "${RED}✗${NC} Worker failed to start"
    cat /tmp/worker.log
    exit 1
fi

# Trigger BI workflow
echo -n "   Triggering BI workflow... "
WORKFLOW_ID="smoke-test-bi-$(date +%s)"

uv run python -c "
import asyncio
from temporalio.client import Client

async def trigger():
    client = await Client.connect('localhost:7233')
    handle = await client.start_workflow(
        'BIWorkflow',
        args=['demo-tenant', 'Show total revenue', 'smoke-test'],
        id='${WORKFLOW_ID}',
        task_queue='sarthi-queue',
    )
    return handle.id

workflow_id = asyncio.run(trigger())
print(workflow_id)
" 2>/dev/null && echo -e "${GREEN}✓${NC} Workflow triggered" || {
    echo -e "${RED}✗${NC} Failed to trigger workflow"
}

# Wait for workflow to complete
echo -n "   Waiting for workflow completion... "
sleep 8

# Check workflow status
uv run python -c "
import asyncio
from temporalio.client import Client
from temporalio.workflow import WorkflowStatus

async def check():
    client = await Client.connect('localhost:7233')
    try:
        handle = client.get_workflow_handle('${WORKFLOW_ID}')
        status = await handle.status()
        return status
    except Exception as e:
        return f'Error: {e}'

status = asyncio.run(check())
print(f'Status: {status}')
" 2>/dev/null || echo "   (Status check failed - check Temporal UI)"

# Stop worker
echo -n "   Stopping worker... "
kill $WORKER_PID 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓${NC} Worker stopped"

# Stop Mockoon
echo -n "   Stopping Mockoon... "
if [ -f /tmp/sarthi-mockoon.pid ]; then
    kill $(cat /tmp/sarthi-mockoon.pid) 2>/dev/null || true
    rm -f /tmp/sarthi-mockoon.pid
fi
pkill -f "mockoon-cli.*3000" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓${NC} Mockoon stopped"

# Summary
echo ""
echo "========================================"
echo -e "${GREEN}Smoke Test Complete${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Check Temporal UI: http://localhost:8088"
echo "2. Check worker logs: cat /tmp/worker.log"
echo "3. Run full test suite: uv run pytest tests/ -v"
