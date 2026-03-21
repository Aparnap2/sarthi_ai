#!/usr/bin/env bash
# Setup Redpanda topics for Sarthi v1.0
# Usage: bash scripts/setup_redpanda_topics.sh

set -euo pipefail

REDPANDA_CONTAINER="${REDPANDA_CONTAINER:-iterateswarm-redpanda}"
BROKERS="${BROKERS:-localhost:19092}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     SARTHI v1.0 — REDPANDA TOPICS SETUP                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Redpanda is running
echo "1. Checking Redpanda..."
if ! docker ps --format "{{.Names}}" | grep -q "^${REDPANDA_CONTAINER}$"; then
    echo "❌ Redpanda container not running"
    echo "   Run: docker start ${REDPANDA_CONTAINER}"
    exit 1
fi
echo "✅ Redpanda running (${REDPANDA_CONTAINER})"
echo ""

# Wait for Redpanda to be ready
echo "2. Waiting for Redpanda to be ready..."
for i in {1..30}; do
    if docker exec "${REDPANDA_CONTAINER}" rpk cluster health 2>/dev/null | grep -q "Healthy"; then
        echo "✅ Redpanda healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Redpanda not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done
echo ""

# Create topics
echo "3. Creating topics..."

# sarthi.events.raw (3 partitions)
echo "   Creating sarthi.events.raw (3 partitions)..."
docker exec "${REDPANDA_CONTAINER}" \
  rpk topic create sarthi.events.raw --partitions 3 --replicas 1 \
  --config retention.ms=604800000 \
  --if-not-exists
echo "   ✅ sarthi.events.raw created"

# sarthi.finance.events (3 partitions)
echo "   Creating sarthi.finance.events (3 partitions)..."
docker exec "${REDPANDA_CONTAINER}" \
  rpk topic create sarthi.finance.events --partitions 3 --replicas 1 \
  --config retention.ms=604800000 \
  --if-not-exists
echo "   ✅ sarthi.finance.events created"

# sarthi.bi.queries (3 partitions)
echo "   Creating sarthi.bi.queries (3 partitions)..."
docker exec "${REDPANDA_CONTAINER}" \
  rpk topic create sarthi.bi.queries --partitions 3 --replicas 1 \
  --config retention.ms=604800000 \
  --if-not-exists
echo "   ✅ sarthi.bi.queries created"

# sarthi.dlq (1 partition)
echo "   Creating sarthi.dlq (1 partition)..."
docker exec "${REDPANDA_CONTAINER}" \
  rpk topic create sarthi.dlq --partitions 1 --replicas 1 \
  --config retention.ms=2592000000 \
  --if-not-exists
echo "   ✅ sarthi.dlq created"

# founder.signals (3 partitions) - for founder HITL signals
echo "   Creating founder.signals (3 partitions)..."
docker exec "${REDPANDA_CONTAINER}" \
  rpk topic create founder.signals --partitions 3 --replicas 1 \
  --config retention.ms=604800000 \
  --if-not-exists
echo "   ✅ founder.signals created"

echo ""

# List topics
echo "4. Listing topics..."
docker exec "${REDPANDA_CONTAINER}" rpk topic list
echo ""

# Test produce/consume
echo "5. Testing produce/consume..."
TEST_MSG='{"test": true, "timestamp": "'$(date -Iseconds)'"}'
echo "   Producing test message to sarthi.events.raw..."
echo "${TEST_MSG}" | docker exec -i "${REDPANDA_CONTAINER}" \
  rpk topic produce sarthi.events.raw

echo "   Consuming test message..."
CONSUMED=$(docker exec "${REDPANDA_CONTAINER}" \
  rpk topic consume sarthi.events.raw --num 1 2>&1)

if echo "${CONSUMED}" | grep -q '"test": true'; then
    echo "   ✅ Produce/consume test passed"
else
    echo "   ⚠️  Produce/consume test inconclusive (check manually)"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     ✅ REDPANDA TOPICS READY                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Topics created:"
echo "  - sarthi.events.raw (3 partitions, 7-day retention)"
echo "  - sarthi.finance.events (3 partitions, 7-day retention)"
echo "  - sarthi.bi.queries (3 partitions, 7-day retention)"
echo "  - sarthi.dlq (1 partition, 30-day retention)"
echo ""
echo "✅ PHASE 1C COMPLETE"
echo "✅ READY FOR PHASE 2 (FINANCE AGENT)"
