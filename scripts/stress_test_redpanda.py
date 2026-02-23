"""Stress test for Redpanda message queue throughput."""

import time
import json
import uuid
from dataclasses import dataclass, asdict
from typing import List
from kafka import KafkaProducer, KafkaConsumer


@dataclass
class StressResult:
    total_messages: int
    duration_s: float
    throughput_msgs_per_s: float
    p50_produce_ms: float
    p95_produce_ms: float
    p99_produce_ms: float
    consumer_lag: int
    messages_lost: int


def stress_test_redpanda(
    n_messages: int = 1000, concurrency: int = 10, message_size_bytes: int = 512
) -> StressResult:
    """Stress test Redpanda with N messages and measure throughput."""

    producer = KafkaProducer(
        bootstrap_servers=["localhost:19092"],
        value_serializer=lambda v: json.dumps(v).encode(),
        key_serializer=lambda k: k.encode(),
        batch_size=16384,
        linger_ms=5,
        compression_type="snappy",
        acks="all",
    )

    sent_ids = set()
    produce_latencies = []

    print(f"🚀 Producing {n_messages} messages to feedback-events...")
    start = time.time()

    for i in range(n_messages):
        feedback_id = str(uuid.uuid4())
        sent_ids.add(feedback_id)

        msg = {
            "feedback_id": feedback_id,
            "text": f"Stress test feedback #{i}: app crashes when I do thing {i % 50}",
            "source": "stress-test",
            "user_id": f"stress-user-{i % concurrency}",
            "timestamp": time.time(),
        }

        t0 = time.perf_counter()
        future = producer.send("feedback-events", key=feedback_id, value=msg)
        future.get(timeout=10)
        produce_latencies.append((time.perf_counter() - t0) * 1000)

        if i % 100 == 0:
            print(f"  Sent {i}/{n_messages} ({i / n_messages * 100:.0f}%)")

    producer.flush()
    produce_duration = time.time() - start

    produce_latencies.sort()
    n = len(produce_latencies)

    # Verify consumption
    print(f"\n📥 Verifying consumption...")
    consumer = KafkaConsumer(
        "feedback-events",
        bootstrap_servers=["localhost:19092"],
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
        group_id=f"stress-verify-{uuid.uuid4()}",
    )

    received_ids = set()
    for msg in consumer:
        received_ids.add(msg.value["feedback_id"])
        if len(received_ids) >= n_messages:
            break

    consumer.close()
    messages_lost = len(sent_ids - received_ids)

    result = StressResult(
        total_messages=n_messages,
        duration_s=round(produce_duration, 2),
        throughput_msgs_per_s=round(n_messages / produce_duration, 1),
        p50_produce_ms=round(produce_latencies[n // 2], 2),
        p95_produce_ms=round(produce_latencies[int(n * 0.95)], 2),
        p99_produce_ms=round(produce_latencies[int(n * 0.99)], 2),
        consumer_lag=n_messages - len(received_ids),
        messages_lost=messages_lost,
    )

    print(f"\n{'=' * 50}")
    print(f"REDPANDA STRESS TEST RESULTS")
    print(f"{'=' * 50}")
    print(f"Messages:       {result.total_messages}")
    print(f"Duration:       {result.duration_s}s")
    print(f"Throughput:     {result.throughput_msgs_per_s} msg/s")
    print(f"p50 produce:    {result.p50_produce_ms}ms")
    print(f"p95 produce:    {result.p95_produce_ms}ms")
    print(f"p99 produce:    {result.p99_produce_ms}ms")
    print(
        f"Messages lost:  {result.messages_lost} ({'✅' if result.messages_lost == 0 else '❌'})"
    )
    print(f"Consumer lag:   {result.consumer_lag}")

    return result


if __name__ == "__main__":
    # Run progressively harder tests
    for n in [100, 500, 1000]:
        print(f"\n{'=' * 50}")
        print(f"Running {n} message test...")
        result = stress_test_redpanda(n_messages=n)
        assert result.messages_lost == 0, "DATA LOSS DETECTED"
        print(f"✅ {n} messages: zero loss confirmed")
