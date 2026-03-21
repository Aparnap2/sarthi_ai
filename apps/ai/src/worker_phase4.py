"""
Temporal Worker for Sarthi v1.0 - Phase 4.

Listens to 'sarthi-queue' and executes:
- Activities: run_finance_agent, run_bi_agent, send_telegram_message, send_telegram_photo
- Workflows: FinanceWorkflow, BIWorkflow
"""
import asyncio
import os
import structlog
from temporalio.client import Client
from temporalio.worker import Worker

from src.activities.run_finance_agent import run_finance_agent
from src.activities.run_bi_agent import run_bi_agent
from src.activities.send_telegram import send_telegram_message, send_telegram_photo
from src.workflows.finance_workflow import FinanceWorkflow
from src.workflows.bi_workflow import BIWorkflow

logger = structlog.get_logger(__name__)

# Configuration from environment
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TASK_QUEUE = os.getenv("TASK_QUEUE", "sarthi-queue")


async def run_worker():
    """Run the Temporal worker for Sarthi activities and workflows."""
    logger.info(
        "Starting Sarthi Worker",
        address=TEMPORAL_HOST,
        task_queue=TASK_QUEUE,
        namespace=TEMPORAL_NAMESPACE,
    )

    # Connect to Temporal server
    client = await Client.connect(
        TEMPORAL_HOST,
        namespace=TEMPORAL_NAMESPACE,
    )

    # Create worker with all activities and workflows
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        activities=[
            run_finance_agent,
            run_bi_agent,
            send_telegram_message,
            send_telegram_photo,
        ],
        workflows=[
            FinanceWorkflow,
            BIWorkflow,
        ],
    )

    logger.info("Sarthi Worker started, waiting for tasks...")

    # Run the worker
    await worker.run()


def main():
    """Entry point for the Sarthi worker."""
    log = structlog.get_logger()

    try:
        log.info("Initializing Sarthi Worker...")
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        log.info("Sarthi Worker shutting down...")
    except Exception as e:
        log.error("Worker error", error=str(e))
        raise


if __name__ == "__main__":
    main()
