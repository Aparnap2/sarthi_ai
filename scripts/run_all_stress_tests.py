#!/usr/bin/env python3
"""Combined stress test runner for all infrastructure components."""

import asyncio
import json
import time
import sys
from datetime import datetime

sys.path.insert(0, "/home/aparna/Desktop/iterate_swarm/apps/ai")
sys.path.insert(0, "/home/aparna/Desktop/iterate_swarm")


async def main():
    print("🧪 IterateSwarm Infrastructure Stress Tests")
    print(f"   Started: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    report = {"timestamp": datetime.utcnow().isoformat(), "results": {}}

    # 1. Redpanda stress test
    print("\n[1/3] Redpanda throughput test...")
    try:
        from scripts.stress_test_redpanda import stress_test_redpanda

        redpanda_result = stress_test_redpanda(n_messages=500)
        report["results"]["redpanda"] = {
            "throughput_msgs_per_s": redpanda_result.throughput_msgs_per_s,
            "p99_produce_ms": redpanda_result.p99_produce_ms,
            "messages_lost": redpanda_result.messages_lost,
            "verdict": "✅ PASS" if redpanda_result.messages_lost == 0 else "❌ FAIL",
        }
    except Exception as e:
        report["results"]["redpanda"] = {"error": str(e), "verdict": "❌ FAIL"}
        print(f"   Redpanda test failed: {e}")

    # 2. Temporal workflow start throughput
    print("\n[2/3] Temporal workflow start throughput...")
    try:
        from scripts.stress_test_temporal import stress_test_temporal

        temporal_result = await stress_test_temporal(n_workflows=30, concurrency=10)
        report["results"]["temporal"] = {
            "workflows_per_second": temporal_result.get("workflows_per_second", 0),
            "start_p95_ms": temporal_result.get("workflow_start_p95_ms", 0),
            "success_rate": f"{temporal_result.get('started_successfully', 0)}/{temporal_result.get('total_workflows', 0)}",
            "verdict": "✅ PASS"
            if temporal_result.get("failed_to_start", 0) == 0
            else "⚠️ PARTIAL",
        }
    except Exception as e:
        report["results"]["temporal"] = {"error": str(e), "verdict": "❌ FAIL"}
        print(f"   Temporal test failed: {e}")

    # 3. End-to-end concurrent benchmark
    print("\n[3/3] End-to-end concurrent pipeline test (10 real AI requests)...")
    try:
        import httpx

        feedbacks = [
            "App crashes on login with Google OAuth",
            "Please add dark mode to the UI",
            "How do I export data to CSV?",
            "500 error when uploading files > 10MB",
            "Add bulk delete to inbox",
            "Notifications not showing after enabling",
            "Search results don't update with filters",
            "Mobile app very slow on Android 12",
            "What are the API rate limits?",
            "Login button unresponsive on Firefox",
        ]

        async with httpx.AsyncClient() as client:
            t0 = time.time()
            tasks = [
                client.post(
                    "http://localhost:3000/api/feedback",
                    json={
                        "content": fb,
                        "source": "stress-test",
                        "user_id": f"user-{i}",
                    },
                    timeout=30.0,
                )
                for i, fb in enumerate(feedbacks)
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            e2e_duration = time.time() - t0

        successes = sum(
            1 for r in responses if hasattr(r, "status_code") and r.status_code == 200
        )
        report["results"]["e2e"] = {
            "requests": len(feedbacks),
            "successes": successes,
            "total_wall_time_s": round(e2e_duration, 2),
            "success_rate": f"{successes}/{len(feedbacks)}",
            "verdict": "✅ PASS" if successes == len(feedbacks) else "⚠️ PARTIAL",
        }
    except Exception as e:
        report["results"]["e2e"] = {"error": str(e), "verdict": "❌ FAIL"}
        print(f"   E2E test failed: {e}")

    # Save report
    filename = f"stress_test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'=' * 60}")
    print("FINAL STRESS TEST REPORT")
    print(f"{'=' * 60}")
    for component, result in report["results"].items():
        print(f"\n{component.upper()}:")
        for k, v in result.items():
            print(f"  {k}: {v}")

    print(f"\n✅ Full report saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())
