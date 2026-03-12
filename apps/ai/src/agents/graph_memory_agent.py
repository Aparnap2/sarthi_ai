"""
GraphMemoryAgent — temporal knowledge graph memory.
Uses Graphiti (Zep) on Neo4j for structured relationship memory.
Keeps Qdrant for raw semantic similarity (unchanged).
Both are queried on every TriggerAgent evaluation.

MemoryAgent (Qdrant)   → "what's similar to this signal?"
GraphMemoryAgent (Neo4j) → "what's the pattern over time?"
SupervisorAgent merges both before scoring.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://saarathi-neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "saarathi")


class GraphMemoryAgent:
    """
    Wraps Graphiti for Saarathi.
    Every reflection, commitment, signal, and decision
    is an episode in the graph.
    """

    def __init__(self) -> None:
        self._g = Graphiti(
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASS,
        )

    async def initialize(self) -> None:
        """Call once on startup — creates Neo4j indices."""
        await self._g.build_indices_and_constraints()

    async def add_reflection(
        self,
        founder_id: str,
        content: str,
        week_number: int,
        energy: int,
        commitments: list[str],
    ) -> None:
        """Ingest a weekly reflection as a Graphiti episode."""
        enriched = (
            f"Weekly reflection for founder {founder_id}, "
            f"week {week_number}. Energy level: {energy}/5.\n\n"
            f"{content}\n\n"
            f"Commitments this week: {'; '.join(commitments)}"
        )
        await self._g.add_episode(
            name=f"reflection_w{week_number}_{founder_id[:8]}",
            episode_body=enriched,
            source=EpisodeType.text,
            source_description="weekly_reflection",
            reference_time=datetime.now(timezone.utc),
            group_id=founder_id,
        )

    async def add_commitment_outcome(
        self,
        founder_id: str,
        commitment_text: str,
        completed: bool,
        week_number: int,
    ) -> None:
        """Record whether a commitment was kept."""
        outcome = "completed" if completed else "did not complete"
        await self._g.add_episode(
            name=f"commitment_{week_number}_{founder_id[:8]}",
            episode_body=(
                f"Founder {founder_id} {outcome} their commitment: "
                f"'{commitment_text}' in week {week_number}."
            ),
            source=EpisodeType.text,
            source_description="commitment_outcome",
            reference_time=datetime.now(timezone.utc),
            group_id=founder_id,
        )

    async def add_market_signal(
        self,
        founder_id: str,
        signal_text: str,
        relevance: float,
        source: str,
    ) -> None:
        """Log market signals as graph episodes."""
        await self._g.add_episode(
            name=f"signal_{datetime.now().date()}_{founder_id[:8]}",
            episode_body=(
                f"Market signal (relevance {relevance:.2f}) from {source} "
                f"relevant to founder {founder_id}: {signal_text}"
            ),
            source=EpisodeType.text,
            source_description="market_signal",
            reference_time=datetime.now(timezone.utc),
            group_id=founder_id,
        )

    async def add_intervention(
        self,
        founder_id: str,
        message: str,
        trigger_type: str,
        score: float,
        rating: int | None = None,
    ) -> None:
        """Record every Saarathi intervention."""
        rating_text = f" Founder rated it: {rating}." if rating else ""
        await self._g.add_episode(
            name=f"intervention_{datetime.now().isoformat()}_{founder_id[:8]}",
            episode_body=(
                f"Saarathi sent a {trigger_type} intervention "
                f"(score: {score:.2f}) to founder {founder_id}. "
                f"Message: {message[:200]}.{rating_text}"
            ),
            source=EpisodeType.text,
            source_description="saarathi_intervention",
            reference_time=datetime.now(timezone.utc),
            group_id=founder_id,
        )

    async def search(
        self,
        founder_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Hybrid search: semantic similarity + graph traversal."""
        results = await self._g.search(
            query=query,
            group_ids=[founder_id],
            config=NODE_HYBRID_SEARCH_RRF,
            num_results=top_k,
        )
        return [
            {
                "content": r.fact,
                "score": r.score,
                "valid_at": str(r.valid_at) if r.valid_at else None,
                "episode": r.name,
                "uuid": str(r.uuid),
            }
            for r in results
        ]

    async def get_pattern_context(
        self,
        founder_id: str,
    ) -> dict:
        """Rich pattern context for TriggerAgent."""
        avoidance = await self.search(
            founder_id,
            "commitments not completed repeated week",
            top_k=3,
        )
        correlation = await self.search(
            founder_id,
            "low energy revenue decline same period",
            top_k=3,
        )
        wins = await self.search(
            founder_id,
            "completed goals revenue increased momentum",
            top_k=3,
        )
        effective = await self.search(
            founder_id,
            "Saarathi intervention founder responded positively",
            top_k=2,
        )
        return {
            "avoidance_patterns": avoidance,
            "revenue_correlations": correlation,
            "what_worked": wins,
            "effective_interventions": effective,
        }

    async def close(self) -> None:
        await self._g.close()
