"""
MemoryAgent — Sarthi founder memory management.

Reads/writes Qdrant with founder-specific namespacing.
Maintains founder long-term memory. Extracts behavioral patterns.
Every reflection is embedded and indexed for retrieval during trigger evaluation.
"""

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue, MatchAny
import os
import uuid
import json
from typing import Optional, List, Dict, Any, TypedDict
from dataclasses import dataclass
import asyncpg

from src.config.llm import get_llm_client, get_model


class FounderMemoryState(TypedDict):
    """State representing founder's memory context."""
    founder_id: str
    embeddings: List[str]
    patterns: Optional[Dict[str, Any]]
    reflection_count: int


@dataclass
class MemoryWrite:
    """Represents a memory to be written."""
    founder_id: str
    content: str
    memory_type: str
    confidence: float = 1.0
    source: str = "system"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MemoryQuery:
    """Represents a memory query."""
    founder_id: str
    query_text: str
    memory_types: Optional[List[str]] = None
    top_k: int = 10
    min_confidence: float = 0.5


class MemoryAgent:
    """
    Sarthi Memory Agent for founder memory management.
    
    Stores and retrieves founder memories using Qdrant vector database.
    Uses Azure OpenAI for embeddings.
    """
    
    COLLECTION_NAME = "sarthi_founder_memory"
    EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(self):
        """Initialize MemoryAgent with OpenAI-compatible and Qdrant clients."""
        self.client = get_llm_client()
        self.qdrant = QdrantClient(
            host=os.environ.get("QDRANT_HOST", "localhost"),
            port=int(os.environ.get("QDRANT_PORT", "6333"))
        )
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Ensure the founder memory collection exists in Qdrant."""
        collections = [c.name for c in self.qdrant.get_collections().collections]
        if self.COLLECTION_NAME not in collections:
            self.qdrant.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
    
    def _embed(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI-compatible API.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        response = self.client.embeddings.create(
            input=text,
            model=os.environ.get("EMBEDDING_MODEL", self.EMBEDDING_MODEL)
        )
        return response.data[0].embedding
    
    def write(self, memory: MemoryWrite) -> str:
        """
        Write a memory to Qdrant.
        
        Args:
            memory: MemoryWrite object containing memory data
            
        Returns:
            Point ID of the written memory
        """
        vector = self._embed(memory.content)
        point_id = str(uuid.uuid4())
        payload = {
            "founder_id": memory.founder_id,
            "content": memory.content,
            "memory_type": memory.memory_type,
            "confidence": memory.confidence,
            "source": memory.source,
            "metadata": memory.metadata or {},
        }
        
        # Check for conflicts
        conflicts = self._find_conflicts(memory)
        if conflicts:
            payload["has_conflicts"] = True
            payload["conflict_ids"] = conflicts
            payload["confidence"] = min(memory.confidence * 0.7, 0.6)
        
        self.qdrant.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)]
        )
        return point_id
    
    def query(self, query: MemoryQuery) -> List[Dict[str, Any]]:
        """
        Query memories from Qdrant.
        
        Args:
            query: MemoryQuery object containing query parameters
            
        Returns:
            List of matching memories with scores
        """
        vector = self._embed(query.query_text)
        
        must_conditions = [
            FieldCondition(key="founder_id", match=MatchValue(value=query.founder_id))
        ]
        if query.memory_types:
            must_conditions.append(
                FieldCondition(key="memory_type", match=MatchAny(any=query.memory_types))
            )
        
        results = self.qdrant.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=vector,
            query_filter=Filter(must=must_conditions),
            limit=query.top_k,
            score_threshold=query.min_confidence
        )
        
        return [
            {
                "content": r.payload["content"],
                "type": r.payload["memory_type"],
                "score": r.score,
                "confidence": r.payload.get("confidence", 1.0),
                "source": r.payload.get("source", "unknown")
            }
            for r in results
        ]
    
    def _find_conflicts(self, memory: MemoryWrite) -> List[str]:
        """
        Find conflicting memories (v1 stub - always returns no conflicts).
        
        Args:
            memory: MemoryWrite object to check for conflicts
            
        Returns:
            List of conflicting memory IDs (empty in v1)
        """
        # v1 stub: always returns no conflicts
        # v2: use LLM to detect semantic conflicts
        return []
    
    def detect_patterns(self, founder_id: str) -> Dict[str, Any]:
        """
        Detect behavioral patterns for a founder.

        Args:
            founder_id: Founder UUID

        Returns:
            Dictionary containing detected patterns and archetype
        """
        client = get_llm_client()

        # Query relevant memories
        reflections = self.query(MemoryQuery(
            founder_id=founder_id,
            query_text="weekly reflection commitment avoidance",
            memory_types=["reflection", "commitment"],
            top_k=20
        ))

        if not reflections:
            return {"patterns": [], "archetype": "unknown"}

        # Build context from memories
        context = "\n".join([r["content"] for r in reflections])

        # Use LLM to detect patterns
        response = client.chat.completions.create(
            model=get_model(),
            messages=[
                {
                    "role": "system",
                    "content": """You are analyzing a founder's behavioral patterns.
Return JSON: {
  "archetype": str,
  "patterns": [str, str, str],
  "commitment_completion_rate": float,
  "customer_frequency": str
}"""
                },
                {
                    "role": "user",
                    "content": f"Founder history:\n{context}"
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)


# Global instance
_memory_agent: Optional[MemoryAgent] = None


async def get_memory_agent(db_pool: asyncpg.Pool, llm) -> MemoryAgent:
    """Get or create the global MemoryAgent instance."""
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent()
    return _memory_agent
