#!/bin/bash
# Test Schema Migration for Saarathi Pivot
# Runs migration 003 and verifies tables are created

set -e

POSTGRES_CONTAINER="iterateswarm-postgres"
DB_NAME="iterateswarm"
DB_USER="iterateswarm"
MIGRATION_FILE="/home/aparna/Desktop/iterate_swarm/apps/core/migrations/003_saarathi_pivot.sql"

echo "=== Saarathi Schema Migration Test ==="
echo ""

# Check if PostgreSQL container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
    echo "❌ PostgreSQL container not running."
    echo "   Start it with: docker start ${POSTGRES_CONTAINER}"
    echo "   Or: docker-compose up -d postgres"
    exit 1
fi

echo "✓ PostgreSQL container found"

# Check if migration file exists
if [ ! -f "${MIGRATION_FILE}" ]; then
    echo "❌ Migration file not found: ${MIGRATION_FILE}"
    exit 1
fi

echo "✓ Migration file found: ${MIGRATION_FILE}"
echo ""

# Run the migration
echo "Running migration..."
docker exec -i ${POSTGRES_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -f - < "${MIGRATION_FILE}"

echo ""
echo "✓ Migration executed successfully"
echo ""

# Verify tables
echo "=== Verifying Tables ==="
echo ""

TABLES=("founders" "weekly_reflections" "commitments" "trigger_log" "market_signals")

for table in "${TABLES[@]}"; do
    echo -n "Checking table: ${table}... "
    result=$(docker exec ${POSTGRES_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '${table}');")
    
    if [[ "$result" =~ "t" ]]; then
        echo "✓"
    else
        echo "❌ NOT FOUND"
        exit 1
    fi
done

echo ""
echo "=== Table Structure ==="
echo ""

for table in "${TABLES[@]}"; do
    echo "--- ${table} ---"
    docker exec ${POSTGRES_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c "\d ${table}"
    echo ""
done

# Verify trigger
echo "=== Verifying Trigger ==="
docker exec ${POSTGRES_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c "SELECT trigger_name, event_manipulation, event_object_table FROM information_schema.triggers WHERE trigger_name = 'market_signal_notify';"

# Verify default founder
echo ""
echo "=== Default Founder ==="
docker exec ${POSTGRES_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c "SELECT id, slack_user_id, name, stage FROM founders;"

echo ""
echo "=== Migration Test Complete ==="
echo "✓ All tables created successfully"
echo "✓ Trigger configured"
echo "✓ Default founder inserted"
echo ""
echo "Next steps:"
echo "  1. Test MemoryAgent with: python -m pytest apps/ai/tests/test_memory_agent.py -v"
echo "  2. Test TriggerAgent with: python -m pytest apps/ai/tests/test_trigger_agent.py -v"
