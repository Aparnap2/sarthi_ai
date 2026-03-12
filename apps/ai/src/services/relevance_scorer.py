"""
RelevanceScorer — keyword-based scoring (zero LLM cost).

Scores market signals against founder ICP keywords.
Filters out noise (score < 0.15) and ranks by relevance.
"""

import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ScoredSignal:
    """Market signal with relevance score."""
    source: str
    url: str
    title: str
    content: str
    relevance_score: float
    matched_keywords: List[str]


class RelevanceScorer:
    """
    Scores market signals against founder ICP.
    
    Uses keyword matching (zero LLM cost) to determine
    which signals are relevant to the founder's target market.
    """

    # Common English stopwords to filter out
    STOPWORDS = {
        "about", "their", "there", "would", "could", "which",
        "these", "those", "other", "using", "every", "after",
        "before", "where", "while", "being", "having",
        "with", "from", "into", "through", "during", "without",
        "against", "between", "under", "again", "further",
        "then", "once", "here", "when", "ever", "only",
        "each", "both", "few", "more", "most", "some",
        "such", "than", "too", "very", "just", "also",
        "now", "and", "but", "or", "if", "because",
        "as", "until", "while", "although", "though",
        "after", "before", "when", "whenever", "where",
        "wherever", "whether", "while", "although",
    }

    # Minimum score threshold - signals below this are noise
    MIN_SCORE_THRESHOLD = 0.15

    def score_batch(
        self,
        signals: List,
        founder: Dict[str, Any]
    ) -> List[ScoredSignal]:
        """
        Score signals against founder ICP keywords.
        
        Args:
            signals: List of RawSignal objects
            founder: Founder dict with icp, target_audience, competitors
            
        Returns:
            Sorted list of ScoredSignal (highest relevance first),
            filtered to only include signals >= 0.15 threshold
        """
        scored = []
        
        for signal in signals:
            result = self._score_v1_keywords(signal, founder)
            
            if result.relevance_score >= self.MIN_SCORE_THRESHOLD:
                scored.append(result)
            else:
                logger.debug(
                    "Signal filtered as noise",
                    source=signal.source,
                    score=result.relevance_score
                )
        
        # Sort by relevance score (descending)
        sorted_signals = sorted(
            scored,
            key=lambda s: s.relevance_score,
            reverse=True
        )
        
        logger.info(
            "Scored market signals",
            total=len(signals),
            filtered=len(sorted_signals),
            threshold=self.MIN_SCORE_THRESHOLD
        )
        
        return sorted_signals

    def _score_v1_keywords(
        self,
        signal,
        founder: Dict[str, Any]
    ) -> ScoredSignal:
        """
        Keyword match against founder ICP.
        
        Args:
            signal: RawSignal object
            founder: Founder dict with icp, target_audience, competitors
            
        Returns:
            ScoredSignal with relevance score and matched keywords
        """
        # Build keyword text from founder profile
        icp_text = founder.get("icp", "")
        target_audience = founder.get("target_audience", "")
        competitors = founder.get("competitors", "")
        
        keyword_text = f"{icp_text} {target_audience} {competitors}".lower()
        keywords = self._extract_keywords(keyword_text)
        
        # Search for keyword matches in signal
        signal_text = f"{signal.title} {signal.content}".lower()
        hits = [kw for kw in keywords if kw in signal_text]
        
        # Calculate score: percentage of keywords matched, scaled up to 3x
        # This amplifies small differences in keyword coverage
        if not keywords:
            score = 0.0
        else:
            score = min(1.0, len(hits) / len(keywords) * 3)
        
        return ScoredSignal(
            source=signal.source,
            url=signal.url,
            title=signal.title,
            content=signal.content,
            relevance_score=round(score, 3),
            matched_keywords=hits,
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.
        
        Rules:
        - Length > 4 characters
        - Alphabetic only (no numbers/special chars)
        - Excludes common stopwords
        
        Args:
            text: Input text to extract keywords from
            
        Returns:
            List of unique keywords
        """
        # Extract words with 5+ characters, alphabetic only
        words = re.findall(r'\b[a-z]{5,}\b', text.lower())
        
        # Filter out stopwords and return unique set
        keywords = {w for w in words if w not in self.STOPWORDS}
        
        return list(keywords)
