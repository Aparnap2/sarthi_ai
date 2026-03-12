#!/bin/bash
# Redpanda Topic Management for Saarathi Pivot
# Creates new topics for the core accountability loop

set -e

REDPANDA_CONTAINER="iterateswarm-redpanda"

echo "=== Saarathi Redpanda Topic Setup ==="

# Check if Redpanda container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${REDPANDA_CONTAINER}$"; then
    echo "❌ Redpanda container not running. Start it first."
    exit 1
fi

echo "✓ Redpanda container found"

# Create new topics for Saarathi
echo ""
echo "Creating founder.signals topic..."
docker exec ${REDPANDA_CONTAINER} rpk topic create founder.signals \
  --partitions 3 --replicas 1 || echo "Topic may already exist"

echo "Creating founder.triggers topic..."
docker exec ${REDPANDA_CONTAINER} rpk topic create founder.triggers \
  --partitions 1 --replicas 1 || echo "Topic may already exist"

echo "Creating market.crawled topic..."
docker exec ${REDPANDA_CONTAINER} rpk topic create market.crawled \
  --partitions 3 --replicas 1 || echo "Topic may already exist"

# Delete old feedback topics (optional, comment out to keep)
echo ""
echo "Cleaning up old feedback topics..."
docker exec ${REDPANDA_CONTAINER} rpk topic delete feedback-events 2>/dev/null && echo "✓ Deleted feedback-events" || echo "  feedback-events not found (OK)"
docker exec ${REDPANDA_CONTAINER} rpk topic delete feedback-triage 2>/dev/null && echo "✓ Deleted feedback-triage" || echo "  feedback-triage not found (OK)"
docker exec ${REDPANDA_CONTAINER} rpk topic delete feedback-research 2>/dev/null && echo "✓ Deleted feedback-research" || echo "  feedback-research not found (OK)"

# List all topics
echo ""
echo "=== Current Redpanda Topics ==="
docker exec ${REDPANDA_CONTAINER} rpk topic list

echo ""
echo "=== Saarathi Topics Ready ==="
echo "  - founder.signals: Founder weekly reflections and signals"
echo "  - founder.triggers: Intervention trigger decisions"
echo "  - market.crawled: Market signals from crawler"
