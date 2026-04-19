"""
Feedback Consumer for IterateSwarm Learning Loop

Processes founder feedback from Slack buttons and adjusts agent thresholds dynamically.
This implements the minimal feedback loop to make IterateSwarm truly iterative.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from ..config import get_config
from ..memory.qdrant_ops import QdrantMemoryManager

logger = logging.getLogger(__name__)


class FeedbackConsumer:
    """Consumes feedback events and adjusts agent thresholds based on founder input."""

    def __init__(self):
        self.config = get_config()
        self.memory_manager = QdrantMemoryManager()
        self.db_conn = None

    async def connect_db(self):
        """Connect to PostgreSQL database."""
        try:
            self.db_conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_db,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
            )
            self.db_conn.autocommit = True
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def process_feedback_event(self, event_data: Dict[str, Any]) -> None:
        """
        Process a single feedback event from Redpanda.

        Expected event format:
        {
            "feedback_id": "uuid",
            "type": "agent_feedback",
            "agent_type": "anomaly|investor|pulse|qa",
            "pattern": "specific_pattern_detected",
            "tenant_id": "tenant-uuid",
            "feedback_type": "acted_on|not_relevant|already_knew",
            "user_id": "slack-user-id",
            "channel_id": "slack-channel-id",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        try:
            feedback_id = event_data.get("feedback_id")
            agent_type = event_data.get("agent_type")
            pattern = event_data.get("pattern")
            tenant_id = event_data.get("tenant_id")
            feedback_type = event_data.get("feedback_type")

            logger.info(f"Processing feedback {feedback_id}: {agent_type}.{pattern} -> {feedback_type}")

            # Adjust threshold based on feedback
            await self.adjust_threshold(agent_type, pattern, tenant_id, feedback_type)

            # Store feedback for analytics
            await self.store_feedback(event_data)

        except Exception as e:
            logger.error(f"Failed to process feedback event {event_data.get('feedback_id')}: {e}")

    async def adjust_threshold(self, agent_type: str, pattern: str, tenant_id: str, feedback_type: str) -> None:
        """
        Adjust agent threshold based on founder feedback.

        Learning Rules:
        - "acted_on": Decrease threshold (be more sensitive) - reduce false negatives
        - "not_relevant": Increase threshold (be less sensitive) - reduce false positives
        - "already_knew": Slight increase (reduce noise) but less than "not_relevant"
        """
        # Get current threshold
        current_threshold = await self.get_current_threshold(agent_type, pattern, tenant_id)

        # Calculate adjustment
        adjustment = self.calculate_threshold_adjustment(feedback_type, current_threshold)

        # Apply new threshold
        new_threshold = max(0.0, min(1.0, current_threshold + adjustment))  # Clamp to [0,1]

        # Store updated threshold
        await self.store_threshold(agent_type, pattern, tenant_id, new_threshold, feedback_type)

        logger.info(
            f"Adjusted {agent_type}.{pattern} threshold: {current_threshold:.3f} -> {new_threshold:.3f} "
            f"(feedback: {feedback_type}, adjustment: {adjustment:+.3f})"
        )

    def calculate_threshold_adjustment(self, feedback_type: str, current_threshold: float) -> float:
        """
        Calculate threshold adjustment based on feedback type.

        Uses adaptive adjustment that considers current threshold level.
        """
        base_adjustments = {
            "acted_on": -0.05,      # Decrease threshold (more sensitive)
            "not_relevant": +0.10,  # Increase threshold (less sensitive)
            "already_knew": +0.03,  # Slight increase (reduce noise)
        }

        base_adjustment = base_adjustments.get(feedback_type, 0.0)

        # Adaptive adjustment: smaller changes when threshold is at extremes
        if current_threshold < 0.2:
            base_adjustment *= 0.5  # Smaller adjustments near 0
        elif current_threshold > 0.8:
            base_adjustment *= 0.5  # Smaller adjustments near 1

        return base_adjustment

    async def get_current_threshold(self, agent_type: str, pattern: str, tenant_id: str) -> float:
        """Get current threshold for agent pattern, with fallback to defaults."""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT threshold_value
                    FROM pattern_thresholds
                    WHERE tenant_id = %s AND agent_type = %s AND pattern = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (tenant_id, agent_type, pattern))

                result = cursor.fetchone()
                if result:
                    return float(result['threshold_value'])

        except Exception as e:
            logger.warning(f"Failed to fetch current threshold: {e}")

        # Return default threshold
        return self.get_default_threshold(agent_type, pattern)

    def get_default_threshold(self, agent_type: str, pattern: str) -> float:
        """Get default threshold for agent pattern."""
        defaults = {
            "anomaly": {
                "high_volume": 0.7,
                "unusual_timing": 0.6,
                "default": 0.5,
            },
            "investor": {
                "revenue_drop": 0.8,
                "cash_burn": 0.7,
                "default": 0.6,
            },
            "pulse": {
                "engagement_drop": 0.6,
                "churn_signal": 0.7,
                "default": 0.5,
            },
            "qa": {
                "error_pattern": 0.8,
                "performance_issue": 0.7,
                "default": 0.6,
            },
        }

        agent_defaults = defaults.get(agent_type, {"default": 0.5})
        return agent_defaults.get(pattern, agent_defaults["default"])

    async def store_threshold(self, agent_type: str, pattern: str, tenant_id: str,
                            threshold: float, feedback_type: str) -> None:
        """Store updated threshold in database."""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO pattern_thresholds
                    (tenant_id, agent_type, pattern, threshold_value, last_feedback_type, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, agent_type, pattern)
                    DO UPDATE SET
                        threshold_value = EXCLUDED.threshold_value,
                        last_feedback_type = EXCLUDED.last_feedback_type,
                        updated_at = EXCLUDED.updated_at
                """, (tenant_id, agent_type, pattern, threshold, feedback_type, datetime.utcnow()))

        except Exception as e:
            logger.error(f"Failed to store threshold: {e}")

    async def store_feedback(self, event_data: Dict[str, Any]) -> None:
        """Store feedback event for analytics."""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO agent_feedback
                    (feedback_id, tenant_id, agent_type, pattern, feedback_type, user_id, channel_id, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event_data.get("feedback_id"),
                    event_data.get("tenant_id"),
                    event_data.get("agent_type"),
                    event_data.get("pattern"),
                    event_data.get("feedback_type"),
                    event_data.get("user_id"),
                    event_data.get("channel_id"),
                    datetime.fromisoformat(event_data.get("timestamp", "").replace('Z', '+00:00'))
                ))

        except Exception as e:
            logger.error(f"Failed to store feedback: {e}")

    async def get_threshold(self, agent_type: str, pattern: str, tenant_id: str) -> float:
        """Public method to get current threshold for agents."""
        return await self.get_current_threshold(agent_type, pattern, tenant_id)

    async def close(self):
        """Cleanup connections."""
        if self.db_conn:
            self.db_conn.close()
        await self.memory_manager.close()


# Global instance for agent access
_feedback_consumer: Optional[FeedbackConsumer] = None


async def get_feedback_consumer() -> FeedbackConsumer:
    """Get or create global feedback consumer instance."""
    global _feedback_consumer
    if _feedback_consumer is None:
        _feedback_consumer = FeedbackConsumer()
        await _feedback_consumer.connect_db()
    return _feedback_consumer


async def process_feedback_event(event_data: Dict[str, Any]) -> None:
    """Process a feedback event (convenience function)."""
    consumer = await get_feedback_consumer()
    await consumer.process_feedback_event(event_data)


async def get_agent_threshold(agent_type: str, pattern: str, tenant_id: str) -> float:
    """Get current threshold for an agent pattern."""
    consumer = await get_feedback_consumer()
    return await consumer.get_threshold(agent_type, pattern, tenant_id)