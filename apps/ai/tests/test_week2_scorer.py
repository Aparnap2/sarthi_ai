"""Tests for RelevanceScorer."""

import pytest
from dataclasses import dataclass
from typing import List

from src.services.relevance_scorer import RelevanceScorer, ScoredSignal
from src.services.crawler_service import RawSignal


@dataclass
class MockRawSignal:
    """Mock RawSignal for testing."""
    source: str
    url: str
    title: str
    content: str


class TestRelevanceScorerInitialization:
    """Test RelevanceScorer initialization."""

    def test_default_threshold(self):
        """Test default score threshold."""
        scorer = RelevanceScorer()
        
        assert scorer.MIN_SCORE_THRESHOLD == 0.15

    def test_stopwords_present(self):
        """Test that stopwords are defined."""
        scorer = RelevanceScorer()
        
        assert len(scorer.STOPWORDS) > 0
        assert "the" in scorer.STOPWORDS or "with" in scorer.STOPWORDS


class TestKeywordExtraction:
    """Test keyword extraction logic."""

    def test_extract_keywords_basic(self):
        """Test basic keyword extraction."""
        scorer = RelevanceScorer()
        
        text = "building saas products for startups"
        keywords = scorer._extract_keywords(text)
        
        # Keywords may include: building, saas, products, startups
        # All are >= 5 chars and not stopwords
        assert len(keywords) > 0
        assert "building" in keywords or "products" in keywords or "startups" in keywords

    def test_extract_keywords_filters_short_words(self):
        """Test that words < 5 chars are filtered."""
        scorer = RelevanceScorer()
        
        text = "the cat sat on the mat"
        keywords = scorer._extract_keywords(text)
        
        # All words are < 5 chars
        assert len(keywords) == 0

    def test_extract_keywords_removes_stopwords(self):
        """Test that stopwords are filtered out."""
        scorer = RelevanceScorer()
        
        text = "using their platform for building"
        keywords = scorer._extract_keywords(text)
        
        assert "their" not in keywords
        assert "using" not in keywords
        assert "building" in keywords or "platform" in keywords

    def test_extract_keywords_unique(self):
        """Test that keywords are unique (set behavior)."""
        scorer = RelevanceScorer()
        
        text = "saas saas saas building building"
        keywords = scorer._extract_keywords(text)
        
        # Should have at most 2 unique keywords
        assert len(keywords) <= 2
        # Each keyword should appear only once in the list
        for kw in keywords:
            assert keywords.count(kw) == 1


class TestScoreBatch:
    """Test batch scoring functionality."""

    def test_score_batch_filters_low_scores(self):
        """Test that signals below threshold are filtered."""
        scorer = RelevanceScorer()
        
        signals = [
            MockRawSignal(
                source="test1",
                url="https://test1.com",
                title="Relevant SaaS Content",
                content="This is about saas and startups and building products"
            ),
            MockRawSignal(
                source="test2",
                url="https://test2.com",
                title="Irrelevant Content",
                content="This is about cats and dogs and weather"
            )
        ]
        
        founder = {
            "icp": "saas startups",
            "target_audience": "founders building products",
            "competitors": ""
        }
        
        scored = scorer.score_batch(signals, founder)
        
        # Should filter out low-scoring signals
        assert len(scored) >= 1
        assert all(s.relevance_score >= 0.15 for s in scored)

    def test_score_batch_sorts_by_relevance(self):
        """Test that results are sorted by relevance score."""
        scorer = RelevanceScorer()
        
        signals = [
            MockRawSignal(
                source="low",
                url="https://low.com",
                title="Low Relevance",
                content="Some content"
            ),
            MockRawSignal(
                source="high",
                url="https://high.com",
                title="High Relevance SaaS Startup",
                content="Building saas products for startups and founders"
            )
        ]
        
        founder = {
            "icp": "saas startups",
            "target_audience": "founders building products",
            "competitors": ""
        }
        
        scored = scorer.score_batch(signals, founder)
        
        # Should be sorted descending
        for i in range(len(scored) - 1):
            assert scored[i].relevance_score >= scored[i + 1].relevance_score

    def test_score_batch_empty_input(self):
        """Test scoring empty signal list."""
        scorer = RelevanceScorer()
        
        signals = []
        founder = {"icp": "saas", "target_audience": "", "competitors": ""}
        
        scored = scorer.score_batch(signals, founder)
        
        assert scored == []


class TestScoreV1Keywords:
    """Test individual signal scoring."""

    def test_score_with_matching_keywords(self):
        """Test scoring when keywords match."""
        scorer = RelevanceScorer()
        
        signal = MockRawSignal(
            source="test",
            url="https://test.com",
            title="SaaS Startup Guide",
            content="Building a saas product for startups"
        )
        
        founder = {
            "icp": "saas startups",
            "target_audience": "founders",
            "competitors": ""
        }
        
        result = scorer._score_v1_keywords(signal, founder)
        
        assert isinstance(result, ScoredSignal)
        assert result.relevance_score > 0
        assert len(result.matched_keywords) > 0

    def test_score_with_no_matches(self):
        """Test scoring when no keywords match."""
        scorer = RelevanceScorer()
        
        signal = MockRawSignal(
            source="test",
            url="https://test.com",
            title="Cat Care Guide",
            content="How to take care of your pet cat"
        )
        
        founder = {
            "icp": "saas startups",
            "target_audience": "founders",
            "competitors": ""
        }
        
        result = scorer._score_v1_keywords(signal, founder)
        
        assert result.relevance_score == 0.0
        assert result.matched_keywords == []

    def test_score_preserves_signal_data(self):
        """Test that original signal data is preserved."""
        scorer = RelevanceScorer()
        
        signal = MockRawSignal(
            source="indie_hackers",
            url="https://indiehackers.com/post/123",
            title="Test Post",
            content="Test content"
        )
        
        founder = {"icp": "test", "target_audience": "", "competitors": ""}
        
        result = scorer._score_v1_keywords(signal, founder)
        
        assert result.source == "indie_hackers"
        assert result.url == "https://indiehackers.com/post/123"
        assert result.title == "Test Post"
        assert result.content == "Test content"


class TestScoredSignal:
    """Test ScoredSignal dataclass."""

    def test_scored_signal_creation(self):
        """Test creating a ScoredSignal object."""
        signal = ScoredSignal(
            source="test",
            url="https://test.com",
            title="Test",
            content="Content",
            relevance_score=0.75,
            matched_keywords=["saas", "startup"]
        )
        
        assert signal.source == "test"
        assert signal.relevance_score == 0.75
        assert "saas" in signal.matched_keywords
        assert "startup" in signal.matched_keywords

    def test_scored_signal_rounded_score(self):
        """Test that scores can be rounded to 3 decimals."""
        # Note: dataclass doesn't auto-round, caller is responsible
        signal = ScoredSignal(
            source="test",
            url="https://test.com",
            title="Test",
            content="Content",
            relevance_score=round(0.123456789, 3),
            matched_keywords=[]
        )
        
        assert signal.relevance_score == 0.123
