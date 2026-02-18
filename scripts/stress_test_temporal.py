"""Stress test for Temporal workflow orchestration."""

import asyncio
import time
import uuid
from temporalio.client import Client
from temporalio.common import RetryPolicy
from datetime import timedelta


async def stress_test_temporal(
    n_workflows: int = 50,
    concurrency: int = 10,
) -> dict:
    """
    Starts N concurrent FeedbackWorkflows and measures performance.
    """
    try:
        client = await Client.connect("localhost:7233")
    except Exception as e:
        print(f"❌ Cannot connect to Temporal: {e}")
        return {"error": str(e)}

    results = {"started": 0, "completed": 0, "failed": 0, "latencies_ms": []}
    semaphore = asyncio.Semaphore(concurrency)

    async def run_workflow(i: int):
        feedback_id = str(uuid.uuid4())
        workflow_id = f"stress-feedback-{feedback_id}"

        async with semaphore:
            t0 = time.perf_counter()
            try:
                handle = await client.start_workflow(
                    "FeedbackWorkflow",
                    {
                        "text": f"Stress test: app crashes when I do thing {i}",
                        "source": "stress-test",
                        "user_id": f"stress-user-{i}",
                        "channel_id": "test-channel",
                    },
                    id=workflow_id,
                    task_queue="feedback-queue",
                    execution_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )

                start_latency = (time.perf_counter() - t0) * 1000
                results["started"] += 1
                results["latencies_ms"].append(start_latency)

                if i % 10 == 0:
                    print(
                        f"  [{i}] Workflow started: {workflow_id} ({start_latency:.0f}ms)"
                    )

            except Exception as e:
                results["failed"] += 1
                if i % 10 == 0:
                    print(f"  [{i}] FAILED: {e}")

    print(f"🚀 Starting {n_workflows} concurrent FeedbackWorkflows...")
    total_start = time.time()

    await asyncio.gather(*[run_workflow(i) for i in range(n_workflows)])
    total_duration = time.time() - total_start

    latencies = sorted(results["latencies_ms"])
    n = len(latencies) if latencies else 1

    summary = {
        "total_workflows": n_workflows,
        "started_successfully": results["started"],
        "failed_to_start": results["failed"],
        "total_duration_s": round(total_duration, 2),
        "workflow_start_p50_ms": round(latencies[n // 2], 1) if latencies else 0,
        "workflow_start_p95_ms": round(latencies[int(n * 0.95)], 1) if latencies else 0,
        "workflows_per_second": round(n_workflows / total_duration, 1),
    }

    print(f"\n{'=' * 50}")
    print(f"TEMPORAL STRESS TEST RESULTS")
    print(f"{'=' * 50}")
    for k, v in summary.items():
        print(f"{k}: {v}")

    await client.close()
    return summary


if __name__ == "__main__":
    result = asyncio.run(stress_test_temporal(n_workflows=30, concurrency=10))
