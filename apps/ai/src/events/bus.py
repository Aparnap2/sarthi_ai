"""
Redis Streams Event Bus for Sarthi.

Provides lightweight ordered event streaming as a replacement for Redpanda.
Uses Redis Streams with consumer groups for ordered, replayable event processing.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Awaitable, Callable

import redis.asyncio as redis

log = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
MAX_STREAM_LENGTH = 1000


class EventBus:
    """Redis Streams event bus for Sarthi events."""

    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

    async def emit(
        self,
        topic: str,
        tenant_id: str,
        payload: dict[str, Any],
    ) -> str | None:
        """
        Emit an event to a Redis Stream.

        Args:
            topic: Event topic (e.g., "stripe.events", "sentry.events")
            tenant_id: Tenant identifier for stream isolation
            payload: Event payload

        Returns:
            Message ID from Redis, or None on failure
        """
        try:
            client = await self._get_client()
            stream = f"sarthi:{tenant_id}:{topic}"

            values = {
                "tenant_id": tenant_id,
                "topic": topic,
                "payload": json.dumps(payload),
                "emitted_at": datetime.utcnow().isoformat(),
            }

            result = await client.xadd(
                stream,
                values,
                maxlen=MAX_STREAM_LENGTH,
                approximate=True,
            )

            log.debug(f"Emitted to {stream}: {result}")
            return result

        except Exception as e:
            log.error(f"Failed to emit to {topic}: {e}")
            return None

    async def ensure_group(self, stream: str, group: str) -> bool:
        """
        Ensure a consumer group exists on a stream.

        Args:
            stream: Stream name
            consumer group name

        Returns:
            True if group exists or was created
        """
        try:
            client = await self._get_client()
            await client.xgroup_create(stream, group, id="0", mkstream=True)
            return True
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                return True
            log.warning(f"Failed to create group {group}: {e}")
            return False
        except Exception as e:
            log.warning(f"Failed to ensure group {group}: {e}")
            return False

    async def consume(
        self,
        topic: str,
        tenant_id: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> dict[str, list[tuple[str, dict[str, str]]]:
        """
        Consume messages from a stream using a consumer group.

        Args:
            topic: Event topic
            tenant_id: Tenant identifier
            group: Consumer group name
            consumer: Consumer name
            count: Max messages to fetch
            block_ms: Block timeout in milliseconds

        Returns:
            Dict with stream name -> list of (message_id, fields) tuples
        """
        try:
            client = await self._get_client()
            stream = f"sarthi:{tenant_id}:{topic}"
            await self.ensure_group(stream, group)

            results = await client.xreadgroup(
                group,
                consumer,
                {stream: ">"},
                count=count,
                block=block_ms,
            )

            return results or {}

        except Exception as e:
            log.warning(f"Failed to consume from {topic}: {e}")
            return {}

    async def acknowledge(
        self,
        topic: str,
        tenant_id: str,
        group: str,
        message_id: str,
    ) -> bool:
        """
        Acknowledge a processed message.

        Args:
            topic: Event topic
            tenant_id: Tenant identifier
            group: Consumer group name
            message_id: Message ID to ack

        Returns:
            True on success
        """
        try:
            client = await self._get_client()
            stream = f"sarthi:{tenant_id}:{topic}"
            await client.xack(stream, group, message_id)
            return True
        except Exception as e:
            log.warning(f"Failed to ack {message_id}: {e}")
            return False

    async def read_stream(
        self,
        topic: str,
        tenant_id: str,
        count: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Read last N messages from a stream (no consumer group).

        Args:
            topic: Event topic
            tenant_id: Tenant identifier
            count: Max messages

        Returns:
            List of message dicts
        """
        try:
            client = await self._get_client()
            stream = f"sarthi:{tenant_id}:{topic}"

            results = await client.xrange(stream, count=count)
            messages = []

            for msg_id, fields in results:
                msg = {"id": msg_id, **fields}
                if "payload" in fields:
                    msg["payload"] = json.loads(fields["payload"])
                messages.append(msg)

            return messages

        except Exception as e:
            log.warning(f"Failed to read stream {topic}: {e}")
            return []

    async def health_check(self) -> dict[str, Any]:
        """
        Check Redis connectivity.

        Returns:
            Health status dict
        """
        try:
            client = await self._get_client()
            await client.ping()
            return {"status": "healthy", "redis": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "redis": str(e)}


_global_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global EventBus instance."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


async def emit(topic: str, tenant_id: str, payload: dict[str, Any]) -> str | None:
    """Emit an event (convenience function)."""
    bus = get_event_bus()
    return await bus.emit(topic, tenant_id, payload)


async def consume(
    topic: str,
    tenant_id: str,
    group: str,
    consumer: str,
    count: int = 10,
    block_ms: int = 5000,
) -> dict[str, list[tuple[str, dict[str, str]]]:
    """Consume events (convenience function)."""
    bus = get_event_bus()
    return await bus.consume(topic, tenant_id, group, consumer, count, block_ms)


async def acknowledge(
    topic: str,
    tenant_id: str,
    group: str,
    message_id: str,
) -> bool:
    """Acknowledge an event (convenience function)."""
    bus = get_event_bus()
    return await bus.acknowledge(topic, tenant_id, group, message_id)