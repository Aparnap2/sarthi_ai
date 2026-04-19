#!/usr/bin/env python3
"""
Migrate existing Qdrant vectors to include temporal fields for memory decay.

This script adds:
- occurred_at: When the memory was created (set to now for existing)
- expires_at: When the memory expires (6 months from now)
- relevance_weight: Starting weight (1.0 for existing)

ALWAYS run with --dry-run first to see what would change.
"""

import argparse
import datetime
import logging
import sys
import time
from typing import List

# Add the src directory to path so we can import
sys.path.insert(0, 'apps/ai/src')

from qdrant_client import QdrantClient
from qdrant_client.models import ScrollRequest, SetPayload

# Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "sarthi_memory"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_client():
    """Get Qdrant client."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def get_existing_vectors(dry_run: bool = True) -> List[dict]:
    """Get all vectors that need migration."""
    client = get_client()

    try:
        # Use the correct Qdrant client API
        scroll_result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )
        all_vectors = scroll_result[0]

        # Filter vectors that need migration (missing occurred_at)
        needs_migration = [
            v for v in all_vectors
            if not v.payload or "occurred_at" not in v.payload
        ]

        if dry_run:
            logger.info(f"DRY RUN: Found {len(needs_migration)} vectors needing migration")
            if needs_migration:
                logger.info("Sample vector payload:")
                logger.info(needs_migration[0].payload)
        else:
            logger.info(f"Found {len(needs_migration)} vectors needing migration")

        return needs_migration

    except Exception as e:
        logger.error(f"Failed to scroll vectors: {e}")
        return []


def migrate_batch(client: QdrantClient, vectors: List, batch_size: int = 100) -> int:
    """Migrate vectors in batches."""
    total_migrated = 0

    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        batch_ids = [v.id for v in batch]

        # Prepare new payload fields
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(days=180)  # 6 months

        new_payload = {
            "occurred_at": now.isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
            "relevance_weight": 1.0,
        }

        try:
            # Update payload for this batch
            client.set_payload(
                collection_name=COLLECTION_NAME,
                payload=new_payload,
                points=batch_ids,
            )

            total_migrated += len(batch)
            logger.info(f"Migrated batch {i//batch_size + 1}: {len(batch)} vectors")

            # Small delay to avoid overwhelming Qdrant
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Failed to migrate batch starting at index {i}: {e}")
            break

    return total_migrated


def main():
    parser = argparse.ArgumentParser(description="Migrate Qdrant memory schema")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of vectors to migrate per batch (default: 100)"
    )

    args = parser.parse_args()

    # Always warn about safety
    if not args.dry_run:
        print("⚠️  WARNING: This will modify your Qdrant database!")
        print("   Make sure you have a backup before proceeding.")
        response = input("Continue? (type 'yes' to proceed): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return

    logger.info(f"Starting migration (dry_run={args.dry_run})")

    # Get vectors needing migration
    vectors_to_migrate = get_existing_vectors(args.dry_run)

    if not vectors_to_migrate:
        logger.info("No vectors need migration")
        return

    if args.dry_run:
        logger.info(f"Would migrate {len(vectors_to_migrate)} vectors")
        return

    # Perform actual migration
    client = get_client()
    migrated_count = migrate_batch(client, vectors_to_migrate, args.batch_size)

    logger.info(f"Migration complete: {migrated_count} vectors updated")

    # Verification
    remaining = get_existing_vectors(dry_run=True)
    if remaining:
        logger.warning(f"Still {len(remaining)} vectors need migration")
    else:
        logger.info("✅ Migration successful - all vectors updated")


if __name__ == "__main__":
    main()