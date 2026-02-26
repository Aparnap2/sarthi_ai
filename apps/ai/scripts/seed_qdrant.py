"""Seed Qdrant with 5 realistic past issues for duplicate detection in demo.

Run: cd apps/ai && uv run python scripts/seed_qdrant.py

Requires:
- Qdrant running on localhost:6333
- sentence-transformers package installed
"""

import asyncio
import os
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

COLLECTION = "feedback_vectors"

SEED_ISSUES = [
    "Database connection pool exhausted under high load",
    "Login button unresponsive after session timeout",
    "Payment service returns 500 for international cards",
    "Search results missing for queries with special characters",
    "File upload fails silently for files over 10MB",
]


async def seed():
    """Seed Qdrant with example issues."""
    client = AsyncQdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
    
    try:
        # Try to import sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            print("⚠️  sentence-transformers not installed. Using random vectors for demo.")
            print("   Install with: uv add sentence-transformers")
            model = None
        
        # Create collection if not exists
        collections = await client.get_collections()
        names = [c.name for c in collections.collections]
        
        if COLLECTION not in names:
            await client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            print(f"✅ Created collection '{COLLECTION}'")
        
        if model:
            # Embed and upsert
            embeddings = model.encode(SEED_ISSUES)
            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb.tolist(),
                    payload={"text": text, "source": "seed"},
                )
                for text, emb in zip(SEED_ISSUES, embeddings)
            ]
            await client.upsert(collection_name=COLLECTION, points=points)
            print(f"✅ Seeded {len(points)} issues into Qdrant collection '{COLLECTION}'")
        else:
            # Create points with random vectors (fallback)
            import random
            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=[random.random() for _ in range(384)],
                    payload={"text": text, "source": "seed"},
                )
                for text in SEED_ISSUES
            ]
            await client.upsert(collection_name=COLLECTION, points=points)
            print(f"✅ Seeded {len(points)} issues with random vectors (install sentence-transformers for real embeddings)")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(seed())
