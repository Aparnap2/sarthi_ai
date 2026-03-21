#!/usr/bin/env bash
# Simulate a BI query by triggering the BI Workflow via Temporal Python client
# Usage: scripts/simulate_query.sh <tenant_id> <query>

set -euo pipefail

TENANT_ID="${1:-demo-tenant}"
QUERY="${2:-Total expenses by vendor last 30 days?}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-sarthi-alerts}"

echo "🔍 Triggering BI Workflow..."
echo "   Tenant: ${TENANT_ID}"
echo "   Query: ${QUERY}"
echo "   Telegram Chat: ${TELEGRAM_CHAT_ID}"

# Use Python to start the workflow via Temporal client
cd /home/aparna/Desktop/iterate_swarm/apps/ai

uv run python -c "
import asyncio
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

async def main():
    # Connect to Temporal
    client = await Client.connect('${TEMPORAL_HOST:-localhost:7233}')
    
    # Start BI Workflow
    try:
        handle = await client.start_workflow(
            'BIWorkflow',
            args=['${TENANT_ID}', '${QUERY}', '${TELEGRAM_CHAT_ID}'],
            id='bi-workflow-${TENANT_ID}-$(date +%s)',
            task_queue='${TASK_QUEUE:-sarthi-queue}',
        )
        print(f'✓ Workflow started: {handle.id}')
        print(f'  Status: Running')
    except WorkflowAlreadyStartedError:
        print(f'⚠ Workflow already started with this ID')

asyncio.run(main())
"

echo ""
echo "✓ BI Workflow triggered"
echo "  Check Temporal UI at http://localhost:8088 for workflow execution"
