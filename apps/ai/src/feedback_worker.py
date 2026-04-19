#!/usr/bin/env python3
"""
Feedback Worker for IterateSwarm

Consumes agent feedback events from Redpanda and adjusts thresholds dynamically.
This worker implements the learning loop that makes IterateSwarm truly iterative.
"""

import asyncio
import json
import logging
import signal
import sys
from typing import Dict, Any

from aiokafka import AIOKafkaConsumer

from src.config import get_config
from src.learning.feedback_consumer import process_feedback_event

logger = logging.getLogger(__name__)


class FeedbackWorker:
    """Worker that processes feedback events from Redpanda."""

    def __init__(self):
        self.config = get_config()
        self.consumer: AIOKafkaConsumer = None
        self.running = False

    async def start(self):
        """Start the feedback worker."""
        logger.info("Starting Feedback Worker...")

        self.running = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # Create Kafka consumer
            self.consumer = AIOKafkaConsumer(
                self.config.feedback_events_topic,
                bootstrap_servers=self.config.redpanda_brokers,
                group_id="feedback-worker",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            )

            await self.consumer.start()
            logger.info(f"Connected to Redpanda, consuming from topic: {self.config.feedback_events_topic}")

            # Main processing loop
            await self._process_messages()

        except Exception as e:
            logger.error(f"Error in feedback worker: {e}")
            raise
        finally:
            await self._cleanup()

    async def _process_messages(self):
        """Process messages from Redpanda."""
        while self.running:
            try:
                # Wait for messages with timeout
                message_batch = await self.consumer.getmany(timeout_ms=1000)

                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            await self._handle_message(message)
                        except Exception as e:
                            logger.error(f"Error processing message {message.offset}: {e}")

            except asyncio.TimeoutError:
                # No messages, continue loop
                continue
            except Exception as e:
                logger.error(f"Error getting messages: {e}")
                if self.running:
                    await asyncio.sleep(1)  # Brief pause before retry

    async def _handle_message(self, message):
        """Handle a single feedback message."""
        try:
            event_data = message.value

            # Validate event structure
            if not isinstance(event_data, dict):
                logger.warning(f"Invalid event data type: {type(event_data)}")
                return

            event_type = event_data.get("type")
            if event_type != "agent_feedback":
                # Skip non-feedback events
                return

            feedback_id = event_data.get("feedback_id")
            logger.info(f"Processing feedback event: {feedback_id}")

            # Process the feedback event
            await process_feedback_event(event_data)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            # Continue processing other messages

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def _cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up feedback worker...")

        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

        logger.info("Feedback worker shutdown complete")


async def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    worker = FeedbackWorker()

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())