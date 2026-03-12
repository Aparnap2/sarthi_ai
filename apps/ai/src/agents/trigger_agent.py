"""
TriggerAgent — Sarthi proactive co-founder AI.

Scoring engine for intervention decisions.
Never nags. Only fires when score > threshold.
Computes a 0–1 score and generates Slack messages with feedback buttons.
"""

from openai import OpenAI
from .memory_agent import MemoryAgent, MemoryQuery
import os
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, TypedDict
import asyncpg

from src.config.llm import get_llm_client, get_model


class TriggerState(TypedDict):
    """State representing trigger evaluation result."""
    founder_id: str
    should_fire: bool
    score: float
    trigger_type: str
    message: Optional[str]
    why_now: str


@dataclass
class TriggerInput:
    """Represents input for trigger evaluation."""
    founder_id: str
    signal_type: str
    signal_data: Dict[str, Any]
    founder_context: Dict[str, Any]


@dataclass
class TriggerDecision:
    """Represents a trigger decision."""
    fire: bool
    score: float
    trigger_type: str
    message: Optional[str]
    why_now: str
    suppression_reason: Optional[str]
    commitments_to_create: List[Dict[str, Any]]


class TriggerAgent:
    """
    Sarthi Trigger Agent for proactive interventions.
    
    Evaluates signals and decides whether to fire a trigger.
    Uses dynamic thresholds based on founder stage and ignore rate.
    """
    
    def __init__(self):
        """Initialize TriggerAgent with MemoryAgent and OpenAI-compatible client."""
        self.memory = MemoryAgent()
        self.client = get_llm_client()
    
    def _get_dynamic_threshold(self, founder_context: Dict[str, Any]) -> float:
        """
        Calculate dynamic threshold based on founder stage and ignore rate.
        
        Args:
            founder_context: Founder context data
            
        Returns:
            Threshold value between 0.5 and 0.9
        """
        stage = founder_context.get("stage", "pre_revenue")
        ignore_rate = founder_context.get("recent_ignore_rate", 0.0)
        
        # Base thresholds by stage
        base_thresholds = {
            "pre_idea": 0.5,
            "idea": 0.55,
            "mvp_building": 0.6,
            "first_users": 0.65,
            "pre_revenue": 0.6,
            "revenue": 0.7,
            "scaling": 0.75
        }
        base = base_thresholds.get(stage, 0.6)
        
        # Adjust based on ignore rate (higher ignore rate = higher threshold)
        adjustment = min(ignore_rate * 0.1, 0.15)
        
        return base + adjustment
    
    def score(self, inp: TriggerInput) -> TriggerDecision:
        """
        Evaluate trigger and return decision.
        
        Args:
            inp: TriggerInput containing signal data
            
        Returns:
            TriggerDecision with fire/no-fire decision and message
        """
        # Retrieve relevant memories
        memories = self.memory.query(MemoryQuery(
            founder_id=inp.founder_id,
            query_text=str(inp.signal_data),
            top_k=15
        ))
        
        # Build memory context
        memory_context = "\n".join([m["content"] for m in memories])
        
        # Get dynamic threshold
        threshold = self._get_dynamic_threshold(inp.founder_context)
        
        # Call LLM for scoring and decision
        response = self.client.chat.completions.create(
            model=get_model(),
            messages=[
                {
                    "role": "system",
                    "content": f"""You are Sarthi, a proactive co-founder AI.
THRESHOLD: {threshold}
Only fire if total score >= {threshold}.
Return JSON with: score, fire, trigger_type, why_now, what_is_true, do_this, suppression_reason, commitments_to_create"""
                },
                {
                    "role": "user",
                    "content": f"Signal type: {inp.signal_type}\nSignal data: {json.dumps(inp.signal_data, indent=2)}"
                }
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Format Slack message if firing
        message = None
        if result["fire"]:
            message = self._format_slack_message(result)
        
        return TriggerDecision(
            fire=result["fire"],
            score=result["score"],
            trigger_type=result.get("trigger_type", inp.signal_type),
            message=message,
            why_now=result["why_now"],
            suppression_reason=result.get("suppression_reason"),
            commitments_to_create=result.get("commitments_to_create", [])
        )
    
    def _format_slack_message(self, result: Dict[str, Any]) -> str:
        """
        Format a Slack block kit message.
        
        Args:
            result: LLM response with trigger data
            
        Returns:
            JSON string of Slack blocks
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚡ {result['why_now'][:150]}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*What's happening:*\n{result['what_is_true']}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Do this now:*\n{result['do_this']}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Did it"},
                        "value": "did_it",
                        "action_id": "feedback_did_it"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Won't do"},
                        "value": "wont_do",
                        "action_id": "feedback_wont_do"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔄 Already done"},
                        "value": "already_done",
                        "action_id": "feedback_already_done"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❓ Doesn't apply"},
                        "value": "doesnt_apply",
                        "action_id": "feedback_doesnt_apply"
                    }
                ]
            }
        ]
        return json.dumps(blocks)


# Global instance
_trigger_agent: Optional[TriggerAgent] = None


async def get_trigger_agent(db_pool: asyncpg.Pool, llm, slack_client=None) -> TriggerAgent:
    """Get or create the global TriggerAgent instance."""
    global _trigger_agent
    if _trigger_agent is None:
        _trigger_agent = TriggerAgent()
    return _trigger_agent
