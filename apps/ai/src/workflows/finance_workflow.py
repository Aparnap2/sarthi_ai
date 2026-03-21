"""
Finance Workflow for Temporal.

Orchestrates the Finance Agent with HITL (Human-in-the-Loop) support:
1. Executes run_finance_agent activity
2. Sends Telegram alert if action=ALERT
3. Waits for HITL signal (10 min timeout)
4. Triggers BI cross-query if "investigate" signal received
"""
import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.activities.run_finance_agent import run_finance_agent
    from src.activities.run_bi_agent import run_bi_agent
    from src.activities.send_telegram import send_telegram_message


@workflow.defn(name="FinanceWorkflow")
class FinanceWorkflow:
    """
    Finance Workflow with HITL support.

    This workflow:
    1. Runs the Finance Agent to detect payment anomalies
    2. If ALERT action: sends Telegram message and waits for HITL decision
    3. If "investigate" signal received: triggers BI cross-query
    4. Completes with final action status

    Signals:
        hitl_action: Human-in-the-Loop action (approve, reject, investigate)
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        self._hitl_action: str | None = None
        self._hitl_received: asyncio.Event = asyncio.Event()

    @workflow.signal(name="hitl_action")
    async def hitl_action_signal(self, action: str) -> None:
        """
        Handle HITL action signal from user.

        Args:
            action: One of "approve", "reject", "investigate"
        """
        self._hitl_action = action
        self._hitl_received.set()

    @workflow.run
    async def run(self, tenant_id: str, event: dict, telegram_chat_id: str) -> dict[str, Any]:
        """
        Execute the Finance Workflow.

        Args:
            tenant_id: Tenant identifier
            event: Payment event dict
            telegram_chat_id: Telegram chat ID for alerts

        Returns:
            dict with workflow execution results
        """
        # Configure retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
        )

        # Step 1: Execute Finance Agent
        finance_result = await workflow.execute_activity(
            run_finance_agent,
            tenant_id,
            event,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )

        action = finance_result.get("action", "DIGEST")
        anomaly_score = finance_result.get("anomaly_score", 0.0)

        # Step 2: If ALERT, send Telegram and wait for HITL
        if action == "ALERT":
            # Send alert message
            alert_message = finance_result.get(
                "output_message",
                f"⚠️ Anomaly detected (score: {anomaly_score:.2f})",
            )

            await workflow.execute_activity(
                send_telegram_message,
                telegram_chat_id,
                alert_message,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

            # Wait for HITL signal (10 minute timeout)
            try:
                await asyncio.wait_for(
                    self._hitl_received.wait(),
                    timeout=timedelta(minutes=10),
                )

                # Step 3: If "investigate", trigger BI cross-query
                if self._hitl_action == "investigate":
                    vendor = event.get("vendor", "unknown")
                    bi_query = f"Show all transactions with {vendor} in the last 30 days"

                    bi_result = await workflow.execute_activity(
                        run_bi_agent,
                        tenant_id,
                        bi_query,
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=retry_policy,
                    )

                    # Send BI results
                    if bi_result.get("narrative"):
                        await workflow.execute_activity(
                            send_telegram_message,
                            telegram_chat_id,
                            f"🔍 Investigation results:\n{bi_result['narrative']}",
                            start_to_close_timeout=timedelta(seconds=30),
                            retry_policy=retry_policy,
                        )

            except asyncio.TimeoutError:
                # Timeout - log and continue
                workflow.logger.info("HITL signal timeout - proceeding without user input")

        # Step 4: Return final status
        return {
            "tenant_id": tenant_id,
            "action": action,
            "anomaly_score": anomaly_score,
            "hitl_action_received": self._hitl_action,
            "workflow_status": "completed",
        }
