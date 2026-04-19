#!/usr/bin/env python3
"""
Schedule Memory Maintenance Workflow

Triggers the MemoryMaintenanceWorkflow on a weekly schedule.
This ensures memory decay, expiration cleanup, and performance optimization happen regularly.

Usage:
    python scripts/schedule_memory_maintenance.py

Environment Variables:
    TEMPORAL_HOST: Temporal server host (default: localhost:7233)
    TEMPORAL_TASK_QUEUE: Task queue name (default: SARTHI-MAIN-QUEUE)
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta

from temporalio.client import Client
from temporalio.common import RetryPolicy

from src.workflows.memory_maintenance_workflow import MemoryMaintenanceWorkflow

logger = logging.getLogger(__name__)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "SARTHI-MAIN-QUEUE")


async def schedule_memory_maintenance(tenant_ids: list = None):
    """
    Schedule memory maintenance workflow for specified tenants or all tenants.

    Args:
        tenant_ids: List of tenant IDs to maintain. If None, maintains all tenants.
    """
    client = await Client.connect(TEMPORAL_HOST)

    try:
        # Default parameters for weekly maintenance
        workflow_params = {
            "operations": ["decay_weights", "expire_memories", "optimize_performance"],
        }

        if tenant_ids:
            # Schedule separate workflows for each tenant
            for tenant_id in tenant_ids:
                workflow_id = f"memory-maintenance-{tenant_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
                workflow_params["tenant_id"] = tenant_id

                await client.start_workflow(
                    MemoryMaintenanceWorkflow.run,
                    workflow_params,
                    id=workflow_id,
                    task_queue=TASK_QUEUE,
                    retry_policy=RetryPolicy(max_attempts=3),
                )

                logger.info(f"Scheduled memory maintenance for tenant: {tenant_id} (workflow: {workflow_id})")
        else:
            # Schedule single workflow for all tenants
            workflow_id = f"memory-maintenance-all-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

            await client.start_workflow(
                MemoryMaintenanceWorkflow.run,
                workflow_params,
                id=workflow_id,
                task_queue=TASK_QUEUE,
                retry_policy=RetryPolicy(max_attempts=3),
            )

            logger.info(f"Scheduled memory maintenance for all tenants (workflow: {workflow_id})")

    finally:
        await client.close()


async def main():
    """Main entry point for scheduling memory maintenance."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get tenant IDs from environment or command line
    tenant_ids_env = os.getenv("MAINTENANCE_TENANT_IDS", "")
    if tenant_ids_env:
        tenant_ids = [tid.strip() for tid in tenant_ids_env.split(",") if tid.strip()]
    else:
        tenant_ids = None  # All tenants

    logger.info(f"Starting memory maintenance scheduling for tenants: {tenant_ids or 'all'}")

    try:
        await schedule_memory_maintenance(tenant_ids)
        logger.info("Memory maintenance scheduling completed successfully")
    except Exception as e:
        logger.error(f"Failed to schedule memory maintenance: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())