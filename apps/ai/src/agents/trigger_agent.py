"""
TriggerAgent — Scoring engine for intervention decisions.

Never nags. Only fires when score > threshold.
Computes a 0–1 score across four dimensions:
- commitment_gap: Missing committed deliverables
- decision_stall: Days without reflection/progress
- market_signal: Relevant external opportunities
- momentum_drop: Declining energy scores
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import json
import os
import structlog
from datetime import datetime
import asyncpg

from langgraph.graph import StateGraph, END

logger = structlog.get_logger(__name__)


@dataclass
class TriggerState:
    """State for the TriggerAgent workflow."""
    
    founder_id: str
    patterns: Dict[str, Any] = field(default_factory=dict)
    market_signal: Optional[Dict[str, Any]] = None
    score: float = 0.0
    should_fire: bool = False
    trigger_type: Optional[str] = None
    message: Optional[str] = None
    suppression_reason: Optional[str] = None
    cta: Optional[str] = None
    slack_ts: Optional[str] = None
    founder_rating: Optional[int] = None


# Scoring weights — tunable, calibrated by founder ratings
WEIGHTS = {
    "commitment_gap": 0.30,
    "decision_stall": 0.30,
    "market_signal": 0.20,
    "momentum_drop": 0.20,
}

FIRE_THRESHOLD = 0.60

# Trigger type emojis
TRIGGER_EMOJIS = {
    "commitment_gap": "🎯",
    "decision_stall": "⏸️",
    "market_signal": "📡",
    "momentum_drop": "📉",
}


class TriggerAgent:
    """
    Computes a 0–1 score across four dimensions.
    
    If score > 0.6, fires a Slack message with a specific reason.
    If score < 0.6, logs suppression reason — no message sent.
    """

    def __init__(self, db_pool: asyncpg.Pool, llm, slack_client=None):
        """
        Initialize TriggerAgent.
        
        Args:
            db_pool: Async PostgreSQL connection pool
            llm: LLM client for message generation
            slack_client: Slack client for sending messages (optional)
        """
        self.pool = db_pool
        self.llm = llm
        self.slack_client = slack_client

    async def compute_score(self, state: TriggerState) -> TriggerState:
        """
        Compute intervention score from behavioral patterns.
        
        Args:
            state: Current trigger state
            
        Returns:
            Updated state with score and should_fire flag
        """
        p = state.patterns

        # Normalize each dimension to 0–1
        commitment_gap = min(
            1.0, 
            (1 - p.get("commitment_completion_rate", 1)) + 
            p.get("overdue_commitments", 0) * 0.1
        )
        decision_stall = min(1.0, p.get("days_since_reflection", 0) / 14)
        market_signal = (
            state.market_signal.get("relevance_score", 0) 
            if state.market_signal else 0.0
        )
        momentum_drop = p.get("momentum_drop", 0)

        score = (
            WEIGHTS["commitment_gap"] * commitment_gap +
            WEIGHTS["decision_stall"] * decision_stall +
            WEIGHTS["market_signal"] * market_signal +
            WEIGHTS["momentum_drop"] * momentum_drop
        )

        # Dominant trigger type = highest contributing dimension
        components = {
            "commitment_gap": WEIGHTS["commitment_gap"] * commitment_gap,
            "decision_stall": WEIGHTS["decision_stall"] * decision_stall,
            "market_signal": WEIGHTS["market_signal"] * market_signal,
            "momentum_drop": WEIGHTS["momentum_drop"] * momentum_drop,
        }
        trigger_type = max(components, key=components.get)

        should_fire = score >= FIRE_THRESHOLD

        logger.info(
            "Trigger score computed",
            founder_id=state.founder_id,
            score=round(score, 3),
            should_fire=should_fire,
            trigger_type=trigger_type,
            components={k: round(v, 3) for k, v in components.items()},
        )

        return TriggerState(
            **{
                **state.__dict__,
                "score": round(score, 3),
                "should_fire": should_fire,
                "trigger_type": trigger_type,
            }
        )

    async def generate_message(self, state: TriggerState) -> TriggerState:
        """
        Generate a precise, context-backed Slack message.
        
        Args:
            state: Current trigger state with score computed
            
        Returns:
            Updated state with generated message and CTA
        """
        context = state.patterns.get("retrieved_context", "")
        market = state.market_signal or {}

        emoji = TRIGGER_EMOJIS.get(state.trigger_type, "💡")

        prompt = f"""You are an AI co-founder agent. Generate a SHORT, direct Slack message.

Trigger type: {state.trigger_type}
Score: {state.score}
Founder context (last few weeks): {context[:1000] if context else "No context"}
Market signal: {market.get('title', 'none')} — {market.get('content', '')[:300] if market.get('content') else 'No content'}

Rules:
- Max 3 sentences
- Start with WHY NOW (one sentence citing the trigger)
- Give WHAT'S TRUE (one sentence from memory context)
- End with ONE specific action (not "think about it")
- Do NOT be motivational. Be precise and factual.
- Start message with emoji: {emoji}

Return JSON: {{"message": "...", "cta": "..."}}"""

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Try to parse JSON from response
            try:
                # Handle potential markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                data = json.loads(content.strip())
                message = data.get("message", content.strip())
                cta = data.get("cta", "Take action now")
            except json.JSONDecodeError:
                # Fallback: use entire response as message
                message = content.strip()
                cta = "Take action now"
        except Exception as e:
            logger.error("Failed to generate message", error=str(e))
            # Fallback message
            emoji = TRIGGER_EMOJIS.get(state.trigger_type, "💡")
            message = f"{emoji} Your intervention score is {state.score:.2f}. Review your commitments and take action."
            cta = "Take action now"

        logger.info(
            "Trigger message generated",
            founder_id=state.founder_id,
            trigger_type=state.trigger_type,
            message_length=len(message),
        )

        return TriggerState(
            **{**state.__dict__, "message": message, "cta": cta}
        )

    async def suppress(self, state: TriggerState) -> TriggerState:
        """
        Log suppression reason.
        
        Args:
            state: Current trigger state with score computed
            
        Returns:
            Updated state with suppression reason
        """
        reason = (
            f"Score {state.score:.3f} below threshold {FIRE_THRESHOLD}. "
            f"Dominant dimension: {state.trigger_type}"
        )
        
        logger.info(
            "Trigger suppressed",
            founder_id=state.founder_id,
            score=state.score,
            reason=reason,
        )

        return TriggerState(
            **{**state.__dict__, "suppression_reason": reason}
        )

    async def send_slack_message(self, state: TriggerState) -> TriggerState:
        """
        Send the generated message to Slack.
        
        Args:
            state: Current trigger state with message generated
            
        Returns:
            Updated state with Slack timestamp
        """
        if not self.slack_client or not state.message:
            logger.warning("Slack client not configured or no message to send")
            return state

        # Get founder's Slack user ID from database
        async with self.pool.acquire() as conn:
            founder = await conn.fetchrow(
                "SELECT slack_user_id FROM founders WHERE id = $1",
                state.founder_id,
            )
        
        if not founder:
            logger.error("Founder not found", founder_id=state.founder_id)
            return state

        slack_user_id = founder["slack_user_id"]

        try:
            # Send DM to founder
            response = await self.slack_client.conversations_open(users=slack_user_id)
            channel_id = response["channel"]["id"]
            
            # Send message
            message_response = await self.slack_client.chat_postMessage(
                channel=channel_id,
                text=state.message,
            )
            
            slack_ts = message_response["ts"]
            
            logger.info(
                "Slack message sent",
                founder_id=state.founder_id,
                slack_ts=slack_ts,
            )
            
            return TriggerState(
                **{**state.__dict__, "slack_ts": slack_ts}
            )
            
        except Exception as e:
            logger.error("Failed to send Slack message", error=str(e))
            return state

    async def log_trigger_decision(self, state: TriggerState) -> TriggerState:
        """
        Log the trigger decision to the database.
        
        Args:
            state: Current trigger state
            
        Returns:
            Updated state
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO trigger_log 
                    (founder_id, trigger_type, score, fired, suppression_reason, message_sent, slack_ts)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                state.founder_id,
                state.trigger_type,
                state.score,
                state.should_fire,
                state.suppression_reason,
                state.message,
                state.slack_ts,
            )
        
        logger.info(
            "Trigger decision logged",
            founder_id=state.founder_id,
            fired=state.should_fire,
        )
        
        return state

    def create_graph(self) -> StateGraph:
        """Create LangGraph workflow for trigger decisions."""
        graph = StateGraph(TriggerState)
        
        # Add nodes
        graph.add_node("compute_score", self.compute_score)
        graph.add_node("generate_message", self.generate_message)
        graph.add_node("suppress", self.suppress)
        graph.add_node("send_slack", self.send_slack_message)
        graph.add_node("log_decision", self.log_trigger_decision)
        
        # Set entry point
        graph.set_entry_point("compute_score")
        
        # Route after score computation
        def route_after_score(state):
            return "generate_message" if state.should_fire else "suppress"
        
        graph.add_conditional_edges(
            "compute_score",
            route_after_score,
            {
                "generate_message": "generate_message",
                "suppress": "suppress",
            }
        )
        
        # After generating message, send to Slack
        graph.add_edge("generate_message", "send_slack")
        
        # After sending to Slack, log decision
        graph.add_edge("send_slack", "log_decision")
        
        # After suppression, log decision
        graph.add_edge("suppress", "log_decision")
        
        # End after logging
        graph.add_edge("log_decision", END)
        
        return graph.compile()

    async def evaluate_trigger(
        self,
        founder_id: str,
        patterns: Dict[str, Any],
        market_signal: Optional[Dict[str, Any]] = None,
    ) -> TriggerState:
        """
        Evaluate whether to fire a trigger for a founder.
        
        Args:
            founder_id: Founder UUID
            patterns: Behavioral patterns from MemoryAgent
            market_signal: Optional market signal data
            
        Returns:
            Final trigger state with decision
        """
        initial_state = TriggerState(
            founder_id=founder_id,
            patterns=patterns,
            market_signal=market_signal,
        )
        
        graph = self.create_graph()
        result = await graph.ainvoke(initial_state)
        
        logger.info(
            "Trigger evaluation complete",
            founder_id=founder_id,
            score=result.score,
            fired=result.should_fire,
        )
        
        return result

    async def evaluate_all_founders(self) -> List[TriggerState]:
        """
        Evaluate triggers for all founders.
        
        Returns:
            List of trigger states for each founder
        """
        async with self.pool.acquire() as conn:
            founders = await conn.fetch("SELECT id FROM founders")
        
        results = []
        for founder_row in founders:
            founder_id = founder_row["id"]
            
            # Get patterns from MemoryAgent
            from src.agents.memory_agent import get_memory_agent
            memory_agent = await get_memory_agent(self.pool, self.llm)
            memory_state = await memory_agent.get_founder_context(founder_id)
            
            # Evaluate trigger
            result = await self.evaluate_trigger(
                founder_id=founder_id,
                patterns=memory_state.patterns or {},
                market_signal=None,
            )
            
            results.append(result)
        
        return results


# Global instance
_trigger_agent: Optional[TriggerAgent] = None


async def get_trigger_agent(db_pool: asyncpg.Pool, llm, slack_client=None) -> TriggerAgent:
    """Get or create the global TriggerAgent instance."""
    global _trigger_agent
    if _trigger_agent is None:
        _trigger_agent = TriggerAgent(db_pool=db_pool, llm=llm, slack_client=slack_client)
    return _trigger_agent
