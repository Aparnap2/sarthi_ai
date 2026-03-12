"""
SupervisorAgent — Orchestrates Saarathi's core accountability loop.

Routes incoming signals to appropriate agents:
- weekly_reflection → MemoryAgent (embed + compute patterns)
- market_signal → ResearcherAgent (process and score)
- trigger evaluation → TriggerAgent (score and potentially fire)

Action agents (SWE, Reviewer, Triage) are dormant in actions/
and only activated when ENABLE_ACTION_AGENTS=true.
"""

import os
from typing import Any, Optional, TypedDict, Literal
from dataclasses import dataclass
import structlog
import asyncpg

from langgraph.graph import StateGraph, END

from src.agents.memory_agent import MemoryAgent, FounderMemoryState, get_memory_agent
from src.agents.trigger_agent import TriggerAgent, TriggerState, get_trigger_agent

logger = structlog.get_logger(__name__)


# Flag to enable/disable action agents (V2 features)
ENABLE_ACTION_AGENTS = os.getenv("ENABLE_ACTION_AGENTS", "false") == "true"


@dataclass
class SupervisorState:
    """State for the Supervisor Agent workflow."""
    
    # Input
    signal_type: str  # 'weekly_reflection', 'market_signal', 'trigger_eval'
    founder_id: str
    payload: dict[str, Any]
    
    # Processing
    memory_state: Optional[FounderMemoryState] = None
    trigger_state: Optional[TriggerState] = None
    researcher_result: Optional[dict[str, Any]] = None
    
    # Output
    action_taken: Optional[str] = None
    message_sent: Optional[str] = None
    error: Optional[str] = None


class SupervisorAgent:
    """
    Orchestrates the Saarathi accountability loop.
    
    Routes signals to appropriate agents and manages the overall workflow.
    """

    def __init__(self, db_pool: asyncpg.Pool, llm, slack_client=None):
        """
        Initialize SupervisorAgent.
        
        Args:
            db_pool: Async PostgreSQL connection pool
            llm: LLM client for message generation
            slack_client: Slack client for sending messages (optional)
        """
        self.pool = db_pool
        self.llm = llm
        self.slack_client = slack_client
        self._memory_agent: Optional[MemoryAgent] = None
        self._trigger_agent: Optional[TriggerAgent] = None

    async def _get_memory_agent(self) -> MemoryAgent:
        """Get or create MemoryAgent instance."""
        if self._memory_agent is None:
            self._memory_agent = await get_memory_agent(self.pool, self.llm)
        return self._memory_agent

    async def _get_trigger_agent(self) -> TriggerAgent:
        """Get or create TriggerAgent instance."""
        if self._trigger_agent is None:
            self._trigger_agent = await get_trigger_agent(self.pool, self.llm, self.slack_client)
        return self._trigger_agent

    async def process_weekly_reflection(self, state: SupervisorState) -> SupervisorState:
        """
        Process a weekly reflection from founder.
        
        Args:
            state: Current supervisor state
            
        Returns:
            Updated state with memory processing complete
        """
        logger.info("Processing weekly reflection", founder_id=state.founder_id)
        
        payload = state.payload
        
        try:
            memory_agent = await self._get_memory_agent()
            
            memory_state = await memory_agent.process_reflection(
                founder_id=state.founder_id,
                reflection_text=payload.get("raw_text", ""),
                week_start=payload.get("week_start"),
                shipped=payload.get("shipped"),
                blocked=payload.get("blocked"),
                energy_score=payload.get("energy_score"),
            )
            
            logger.info(
                "Weekly reflection processed",
                founder_id=state.founder_id,
                embedding_id=memory_state.embedding_id,
                patterns_computed=bool(memory_state.patterns),
            )
            
            return SupervisorState(
                **{
                    **state.__dict__,
                    "memory_state": memory_state,
                    "action_taken": "reflection_processed",
                }
            )
            
        except Exception as e:
            logger.error("Failed to process reflection", error=str(e))
            return SupervisorState(
                **{**state.__dict__, "error": str(e)}
            )

    async def process_market_signal(self, state: SupervisorState) -> SupervisorState:
        """
        Process a market signal from crawler.
        
        Args:
            state: Current supervisor state
            
        Returns:
            Updated state with market signal processed
        """
        logger.info("Processing market signal", founder_id=state.founder_id)
        
        payload = state.payload
        
        # Store market signal in database
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO market_signals (source, url, title, content, relevance_score, founder_id)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
                payload.get("source", "unknown"),
                payload.get("url"),
                payload.get("title"),
                payload.get("content"),
                payload.get("relevance_score", 0.5),
                state.founder_id,
            )
        
        logger.info("Market signal stored", founder_id=state.founder_id)
        
        return SupervisorState(
            **{
                **state.__dict__,
                "researcher_result": payload,
                "action_taken": "market_signal_stored",
            }
        )

    async def evaluate_trigger(self, state: SupervisorState) -> SupervisorState:
        """
        Evaluate whether to fire an intervention trigger.
        
        Args:
            state: Current supervisor state
            
        Returns:
            Updated state with trigger evaluation complete
        """
        logger.info("Evaluating trigger", founder_id=state.founder_id)
        
        try:
            # Get patterns from memory agent
            memory_agent = await self._get_memory_agent()
            memory_state = await memory_agent.get_founder_context(state.founder_id)
            
            # Get market signal if available
            market_signal = state.payload.get("market_signal") if state.payload else None
            
            # Evaluate trigger
            trigger_agent = await self._get_trigger_agent()
            trigger_state = await trigger_agent.evaluate_trigger(
                founder_id=state.founder_id,
                patterns=memory_state.patterns or {},
                market_signal=market_signal,
            )
            
            logger.info(
                "Trigger evaluation complete",
                founder_id=state.founder_id,
                score=trigger_state.score,
                fired=trigger_state.should_fire,
            )
            
            return SupervisorState(
                **{
                    **state.__dict__,
                    "memory_state": memory_state,
                    "trigger_state": trigger_state,
                    "action_taken": "trigger_evaluated",
                    "message_sent": trigger_state.message if trigger_state.should_fire else None,
                }
            )
            
        except Exception as e:
            logger.error("Failed to evaluate trigger", error=str(e))
            return SupervisorState(
                **{**state.__dict__, "error": str(e)}
            )

    async def route_action_agents(self, state: SupervisorState) -> SupervisorState:
        """
        Route to action agents if enabled (V2 feature).
        
        Args:
            state: Current supervisor state
            
        Returns:
            Updated state
        """
        if not ENABLE_ACTION_AGENTS:
            logger.debug("Action agents disabled, skipping")
            return state
        
        # V2: Route to SWE, Reviewer, or Triage based on signal
        # This is dormant for Week 1
        logger.info("Action agents enabled but no routing logic for Week 1")
        
        return state

    def create_graph(self) -> StateGraph:
        """Create LangGraph workflow for supervisor orchestration."""
        graph = StateGraph(SupervisorState)
        
        # Add nodes
        graph.add_node("process_reflection", self.process_weekly_reflection)
        graph.add_node("process_market", self.process_market_signal)
        graph.add_node("evaluate_trigger", self.evaluate_trigger)
        graph.add_node("route_actions", self.route_action_agents)
        
        # Set entry point based on signal type
        def route_by_signal_type(state):
            if state.signal_type == "weekly_reflection":
                return "process_reflection"
            elif state.signal_type == "market_signal":
                return "process_market"
            elif state.signal_type in ("trigger_eval", "commitment_gap", "decision_stall", "momentum_drop"):
                return "evaluate_trigger"
            else:
                return "evaluate_trigger"  # Default to trigger evaluation
        
        graph.set_entry_point("route_by_signal_type")
        
        # Conditional routing based on signal type
        graph.add_conditional_edges(
            "route_by_signal_type",
            route_by_signal_type,
            {
                "process_reflection": "process_reflection",
                "process_market": "process_market",
                "evaluate_trigger": "evaluate_trigger",
            }
        )
        
        # After processing, optionally route to action agents
        graph.add_edge("process_reflection", "route_actions")
        graph.add_edge("process_market", "route_actions")
        graph.add_edge("evaluate_trigger", "route_actions")
        
        # End after action routing
        graph.add_edge("route_actions", END)
        
        return graph.compile()

    async def handle_signal(
        self,
        signal_type: str,
        founder_id: str,
        payload: dict[str, Any],
    ) -> SupervisorState:
        """
        Handle an incoming signal.
        
        Args:
            signal_type: Type of signal ('weekly_reflection', 'market_signal', 'trigger_eval')
            founder_id: Founder UUID
            payload: Signal payload
            
        Returns:
            Final supervisor state
        """
        initial_state = SupervisorState(
            signal_type=signal_type,
            founder_id=founder_id,
            payload=payload,
        )
        
        graph = self.create_graph()
        result = await graph.ainvoke(initial_state)
        
        logger.info(
            "Signal handling complete",
            founder_id=founder_id,
            signal_type=signal_type,
            action_taken=result.action_taken,
            error=result.error,
        )
        
        return result


# Global instance
_supervisor_agent: Optional[SupervisorAgent] = None


async def get_supervisor_agent(db_pool: asyncpg.Pool, llm, slack_client=None) -> SupervisorAgent:
    """Get or create the global SupervisorAgent instance."""
    global _supervisor_agent
    if _supervisor_agent is None:
        _supervisor_agent = SupervisorAgent(db_pool=db_pool, llm=llm, slack_client=slack_client)
    return _supervisor_agent
