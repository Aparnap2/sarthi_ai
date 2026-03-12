"""
ContextInterviewAgent — Slack-native onboarding.

Asks 6 questions over a thread. Extracts structured context.
Writes to Qdrant via existing MemoryAgent + Postgres.
"""

from openai import AzureOpenAI
from .memory_agent import MemoryAgent, MemoryWrite
import os
import json
from dataclasses import dataclass
from typing import Optional


ONBOARDING_QUESTIONS = [
    {"id": "mission", "text": "What problem are you solving, and why does it matter to you personally?", "context_type": "mission"},
    {"id": "philosophy_money", "text": "When revenue and product quality conflict, which wins for you — and why?", "context_type": "philosophy"},
    {"id": "non_negotiable", "text": "What would you never do to grow this company, even if it worked?", "context_type": "non_negotiable"},
    {"id": "icp", "text": "Describe the one customer who, if you had 100 of them, would make this company successful.", "context_type": "icp"},
    {"id": "success", "text": "What does winning look like in 12 months? And failing?", "context_type": "goal"},
    {"id": "constraints", "text": "What are your hard constraints right now — time, money, skills, anything?", "context_type": "constraint"},
]


@dataclass
class InterviewState:
    """State for tracking onboarding interview progress."""
    founder_id: str
    slack_user_id: str
    answered_ids: list[str]
    last_ts: str | None = None


class ContextInterviewAgent:
    """
    ContextInterviewAgent manages the Slack-based founder onboarding flow.
    
    Asks 6 structured questions over Slack, extracts behavioral context from answers,
    and stores memories in Qdrant via MemoryAgent.
    """

    def __init__(self):
        """Initialize ContextInterviewAgent with MemoryAgent and Azure OpenAI client."""
        self.memory = MemoryAgent()
        self.client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_KEY"],
            api_version="2024-02-01"
        )

    def get_next_question(self, answered_ids: list[str]) -> Optional[dict]:
        """
        Get the next unanswered question.
        
        Args:
            answered_ids: List of question IDs already answered
            
        Returns:
            Next question dict or None if all answered
        """
        for q in ONBOARDING_QUESTIONS:
            if q["id"] not in answered_ids:
                return q
        return None

    def is_complete(self, answered_ids: list[str]) -> bool:
        """
        Check if onboarding is complete (all 6 questions answered).
        
        Args:
            answered_ids: List of question IDs already answered
            
        Returns:
            True if all 6 questions answered, False otherwise
        """
        return len(answered_ids) >= 6

    def process_answer(self, founder_id: str, question_id: str, question_text: str, raw_answer: str) -> dict:
        """
        Process a founder's answer to extract structured context.
        
        Args:
            founder_id: Founder UUID
            question_id: Question ID being answered
            question_text: Full question text
            raw_answer: Founder's raw answer text
            
        Returns:
            Dict with extracted context, confidence, and Qdrant point ID
        """
        response = self.client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            messages=[{
                "role": "system",
                "content": """Extract structured founder context.
Return JSON: {"context_type": str, "content": str, "confidence": float, "implicit_constraints": [str], "keywords": [str]}"""
            }, {
                "role": "user",
                "content": f"Question: {question_text}\nAnswer: {raw_answer}"
            }],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        parsed = json.loads(response.choices[0].message.content)
        
        # Write to Qdrant via MemoryAgent
        point_id = self.memory.write(MemoryWrite(
            founder_id=founder_id,
            content=parsed["content"],
            memory_type="context",
            confidence=parsed["confidence"],
            source="onboarding",
            metadata={"context_type": parsed["context_type"], "question_id": question_id, "keywords": parsed.get("keywords", [])}
        ))
        
        parsed["qdrant_point_id"] = point_id
        return parsed

    def detect_archetype(self, founder_id: str) -> str:
        """
        Detect founder archetype based on accumulated memories.
        
        Args:
            founder_id: Founder UUID
            
        Returns:
            Detected archetype string (builder/hustler/analyst/operator/unknown)
        """
        patterns = self.memory.detect_patterns(founder_id)
        return patterns.get("archetype", "unknown")
