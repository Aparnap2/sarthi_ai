"""
MemoryAgent — Reads/writes Qdrant with founder-specific namespacing.

Maintains founder long-term memory. Extracts behavioral patterns.
Every reflection is embedded and indexed for retrieval during trigger evaluation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import asyncio
import json
import structlog
from datetime import datetime
import asyncpg

from langgraph.graph import StateGraph, END

from src.services.qdrant import QdrantService, get_qdrant_service
from src.config import get_config

logger = structlog.get_logger(__name__)


@dataclass
class FounderMemoryState:
    """State for the MemoryAgent workflow."""
    
    founder_id: str
    new_reflection: Optional[str] = None
    retrieved_context: Optional[str] = None
    patterns: Optional[Dict[str, Any]] = field(default_factory=dict)
    embedding_id: Optional[str] = None
    week_start: Optional[str] = None
    shipped: Optional[str] = None
    blocked: Optional[str] = None
    energy_score: Optional[int] = None
    raw_text: Optional[str] = None


class MemoryAgent:
    """
    Maintains founder long-term memory in Qdrant.
    
    Every reflection is embedded and indexed.
    On each trigger evaluation, retrieves relevant past context.
    Computes behavioral patterns: commitment_rate, stall_days, etc.
    """

    def __init__(self, db_pool: asyncpg.Pool, llm, qdrant_service: Optional[QdrantService] = None):
        """
        Initialize MemoryAgent.
        
        Args:
            db_pool: Async PostgreSQL connection pool
            llm: LLM client for processing
            qdrant_service: Qdrant service for embeddings (auto-created if not provided)
        """
        self.pool = db_pool
        self.llm = llm
        self.qdrant = qdrant_service or QdrantService()
        self.collection = "founder_memory"

    async def _ensure_collection(self) -> None:
        """Ensure founder memory collection exists."""
        collections = await self.qdrant.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection not in collection_names:
            logger.info("Creating founder memory collection", collection=self.collection)
            await self.qdrant.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    "content": {
                        "size": 768,  # nomic-embed-text dimension
                        "distance": "Cosine",
                    }
                },
            )
            logger.info("Founder memory collection created", collection=self.collection)

    async def embed_and_store(self, state: FounderMemoryState) -> FounderMemoryState:
        """
        Embed new reflection and store in Qdrant.
        
        Args:
            state: Current founder memory state
            
        Returns:
            Updated state with embedding_id
        """
        if not state.new_reflection:
            logger.info("No new reflection to embed", founder_id=state.founder_id)
            return state
            
        await self._ensure_collection()
        
        # Get embedding
        embedding = await self.qdrant.get_embedding(state.new_reflection)
        
        # Create point ID
        point_id = f"{state.founder_id}_{datetime.utcnow().isoformat()}"
        
        # Store in Qdrant with founder-specific metadata
        from qdrant_client.models import PointStruct
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "founder_id": state.founder_id,
                "text": state.new_reflection,
                "type": "weekly_reflection",
                "week_start": state.week_start,
                "energy_score": state.energy_score,
                "shipped": state.shipped,
                "blocked": state.blocked,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        
        await self.qdrant.client.upsert(
            collection_name=self.collection,
            points=[point],
        )
        
        logger.info("Reflection embedded and stored", founder_id=state.founder_id, point_id=point_id)
        
        return FounderMemoryState(
            **{**state.__dict__, "embedding_id": point_id}
        )

    async def retrieve_relevant_context(self, state: FounderMemoryState) -> FounderMemoryState:
        """
        Pull last 5 most relevant memory chunks for this founder.
        
        Args:
            state: Current founder memory state
            
        Returns:
            Updated state with retrieved_context
        """
        await self._ensure_collection()
        
        # Get embedding for the query
        query = "recent commitments blocks decisions energy"
        query_embedding = await self.qdrant.get_embedding(query)
        
        # Search with founder filter
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        search_results = await self.qdrant.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            limit=5,
            with_payload=True,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="founder_id",
                        match=MatchValue(value=state.founder_id),
                    )
                ]
            ),
        )
        
        # Extract context from results
        context_chunks = []
        for result in search_results:
            payload = result.payload or {}
            text = payload.get("text", "")
            if text:
                context_chunks.append(f"[{payload.get('week_start', 'unknown')}] {text}")
        
        context = "\n---\n".join(context_chunks)
        
        logger.info(
            "Retrieved founder context",
            founder_id=state.founder_id,
            chunks_count=len(context_chunks),
        )
        
        return FounderMemoryState(
            **{**state.__dict__, "retrieved_context": context}
        )

    async def compute_behavioral_patterns(self, state: FounderMemoryState) -> FounderMemoryState:
        """
        Compute real behavioral metrics from Postgres.
        
        These feed directly into TriggerAgent's scoring function.
        
        Args:
            state: Current founder memory state
            
        Returns:
            Updated state with computed patterns
        """
        async with self.pool.acquire() as conn:
            # Commitment completion rate (last 4 weeks)
            commitment_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE completed = true)::float /
                    NULLIF(COUNT(*), 0) AS completion_rate,
                    COUNT(*) FILTER (WHERE completed = false
                        AND due_date < NOW()) AS overdue_count
                FROM commitments
                WHERE founder_id = $1
                  AND created_at > NOW() - INTERVAL '4 weeks'
            """, state.founder_id)

            # Days since last commit (decision_stall proxy)
            last_activity = await conn.fetchrow("""
                SELECT
                    EXTRACT(EPOCH FROM (NOW() - MAX(created_at)))/86400
                    AS days_since_last_reflection
                FROM weekly_reflections
                WHERE founder_id = $1
            """, state.founder_id)

            # Energy trend (declining = momentum drop)
            energy_trend = await conn.fetch("""
                SELECT energy_score
                FROM weekly_reflections
                WHERE founder_id = $1
                ORDER BY created_at DESC
                LIMIT 4
            """, state.founder_id)

        # Calculate momentum drop
        scores = [r["energy_score"] for r in energy_trend if r["energy_score"]]
        momentum_drop = (scores[0] - scores[-1]) / 10 if len(scores) >= 2 else 0

        patterns = {
            "commitment_completion_rate": float(commitment_stats["completion_rate"] or 0),
            "overdue_commitments": int(commitment_stats["overdue_count"] or 0),
            "days_since_reflection": float(last_activity["days_since_last_reflection"] or 0),
            "momentum_drop": max(0, momentum_drop),
            "retrieved_context": state.retrieved_context,
        }
        
        logger.info(
            "Computed behavioral patterns",
            founder_id=state.founder_id,
            completion_rate=patterns["commitment_completion_rate"],
            overdue=patterns["overdue_commitments"],
            days_since=patterns["days_since_reflection"],
            momentum_drop=patterns["momentum_drop"],
        )
        
        return FounderMemoryState(**{**state.__dict__, "patterns": patterns})

    async def store_reflection_in_db(self, state: FounderMemoryState) -> FounderMemoryState:
        """
        Store the reflection in PostgreSQL.
        
        Args:
            state: Current founder memory state
            
        Returns:
            Updated state with reflection stored
        """
        if not state.new_reflection:
            return state
            
        async with self.pool.acquire() as conn:
            # Parse week_start if provided
            week_start = None
            if state.week_start:
                try:
                    week_start = datetime.fromisoformat(state.week_start).date()
                except ValueError:
                    week_start = datetime.utcnow().date()
            else:
                week_start = datetime.utcnow().date()
            
            # Insert reflection
            result = await conn.fetchrow("""
                INSERT INTO weekly_reflections 
                    (founder_id, week_start, shipped, blocked, energy_score, raw_text, embedding_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """,
                state.founder_id,
                week_start,
                state.shipped,
                state.blocked,
                state.energy_score,
                state.raw_text or state.new_reflection,
                state.embedding_id,
            )
            
            logger.info("Reflection stored in database", founder_id=state.founder_id, reflection_id=result["id"])
        
        return state

    def create_graph(self) -> StateGraph:
        """Create LangGraph workflow for memory operations."""
        graph = StateGraph(FounderMemoryState)
        
        # Add nodes
        graph.add_node("retrieve_context", self.retrieve_relevant_context)
        graph.add_node("compute_patterns", self.compute_behavioral_patterns)
        graph.add_node("embed_reflection", self.embed_and_store)
        graph.add_node("store_in_db", self.store_reflection_in_db)
        
        # Set entry point
        graph.set_entry_point("retrieve_context")
        
        # Define conditional edges
        def should_embed(state):
            return "embed_reflection" if state.new_reflection else "store_in_db"
        
        graph.add_conditional_edges(
            "retrieve_context",
            should_embed,
            {
                "embed_reflection": "embed_reflection",
                "store_in_db": "store_in_db",
            }
        )
        
        # After embedding, store in DB
        graph.add_edge("embed_reflection", "store_in_db")
        
        # After storing in DB, compute patterns
        graph.add_edge("store_in_db", "compute_patterns")
        
        # End after computing patterns
        graph.add_edge("compute_patterns", END)
        
        return graph.compile()

    async def process_reflection(
        self,
        founder_id: str,
        reflection_text: str,
        week_start: Optional[str] = None,
        shipped: Optional[str] = None,
        blocked: Optional[str] = None,
        energy_score: Optional[int] = None,
    ) -> FounderMemoryState:
        """
        Process a new founder reflection through the complete workflow.
        
        Args:
            founder_id: Founder UUID
            reflection_text: The reflection text to process
            week_start: ISO date string for week start
            shipped: What the founder shipped
            blocked: What's blocking the founder
            energy_score: Energy level 1-10
            
        Returns:
            Final state with patterns computed
        """
        initial_state = FounderMemoryState(
            founder_id=founder_id,
            new_reflection=reflection_text,
            week_start=week_start,
            shipped=shipped,
            blocked=blocked,
            energy_score=energy_score,
            raw_text=reflection_text,
        )
        
        graph = self.create_graph()
        result = await graph.ainvoke(initial_state)
        
        logger.info("Reflection processing complete", founder_id=founder_id)
        
        return result

    async def get_founder_context(
        self,
        founder_id: str,
    ) -> FounderMemoryState:
        """
        Retrieve context and compute patterns for an existing founder.
        
        Args:
            founder_id: Founder UUID
            
        Returns:
            State with context and patterns (no new reflection stored)
        """
        initial_state = FounderMemoryState(
            founder_id=founder_id,
            new_reflection=None,  # No new reflection
        )
        
        graph = self.create_graph()
        result = await graph.ainvoke(initial_state)
        
        return result


# Global instance
_memory_agent: Optional[MemoryAgent] = None


async def get_memory_agent(db_pool: asyncpg.Pool, llm) -> MemoryAgent:
    """Get or create the global MemoryAgent instance."""
    global _memory_agent
    if _memory_agent is None:
        qdrant_service = await get_qdrant_service()
        _memory_agent = MemoryAgent(db_pool=db_pool, llm=llm, qdrant_service=qdrant_service)
    return _memory_agent
