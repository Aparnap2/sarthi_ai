"""
Saarathi AI Agents - Core Accountability Loop.

Week 1 Implementation:
- MemoryAgent: Founder long-term memory with Qdrant embeddings
- TriggerAgent: Scoring engine for intervention decisions

V2 (dormant in actions/):
- SWE Agent: Automated code fixes
- Reviewer Agent: Code review
- Triage Agent: Feedback classification
"""

from src.config.llm_guard import scan_directory_for_violations

# Run enforcement on import - let ImportError propagate
scan_directory_for_violations("apps/ai/src/agents")

from src.agents.memory_agent import MemoryAgent, FounderMemoryState, get_memory_agent
from src.agents.trigger_agent import TriggerAgent, TriggerState, get_trigger_agent

__all__ = [
    "MemoryAgent",
    "FounderMemoryState",
    "get_memory_agent",
    "TriggerAgent",
    "TriggerState",
    "get_trigger_agent",
]
