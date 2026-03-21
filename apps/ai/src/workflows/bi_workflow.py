"""
BI Workflow for Temporal.

Orchestrates the BI Agent for natural language to SQL queries:
1. Executes run_bi_agent activity
2. Sends narrative via Telegram
3. Sends chart PNG if generated
"""
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.activities.run_bi_agent import run_bi_agent
    from src.activities.send_telegram import send_telegram_message, send_telegram_photo


@workflow.defn(name="BIWorkflow")
class BIWorkflow:
    """
    BI Workflow for natural language queries.

    This workflow:
    1. Runs the BI Agent to convert NL query to SQL
    2. Sends narrative explanation via Telegram
    3. Sends chart PNG if one was generated

    No HITL signals needed — fully automated.
    """

    @workflow.run
    async def run(self, tenant_id: str, query: str, telegram_chat_id: str) -> dict[str, Any]:
        """
        Execute the BI Workflow.

        Args:
            tenant_id: Tenant identifier
            query: Natural language question
            telegram_chat_id: Telegram chat ID for results

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

        # Step 1: Execute BI Agent
        bi_result = await workflow.execute_activity(
            run_bi_agent,
            tenant_id,
            query,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )

        narrative = bi_result.get("narrative", "No analysis available.")
        chart_path = bi_result.get("chart_path", "")
        chart_type = bi_result.get("chart_type", "none")

        # Step 2: Send narrative via Telegram
        narrative_message = f"📊 Query: {query}\n\n{narrative}"

        await workflow.execute_activity(
            send_telegram_message,
            telegram_chat_id,
            narrative_message,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        # Step 3: Send chart PNG if generated
        if chart_path and chart_type != "none":
            try:
                await workflow.execute_activity(
                    send_telegram_photo,
                    telegram_chat_id,
                    chart_path,
                    f"Chart: {chart_type}",
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
            except Exception as e:
                workflow.logger.warning(f"Failed to send chart: {e}")

        # Return final status
        return {
            "tenant_id": tenant_id,
            "query": query,
            "narrative": narrative,
            "chart_type": chart_type,
            "chart_generated": bool(chart_path and chart_type != "none"),
            "workflow_status": "completed",
        }
