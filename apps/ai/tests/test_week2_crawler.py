"""Tests for CrawlerService."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.services.crawler_service import CrawlerService, RawSignal, SOURCES


class TestCrawlerServiceInitialization:
    """Test CrawlerService initialization."""

    def test_default_config(self):
        """Test default configuration uses Crawl4AI."""
        service = CrawlerService()
        
        assert service.use_crawl4ai is True
        assert service.crawl4ai_url == "http://localhost:11235"
        assert service.crawl4ai_token == "saarathi-local"
        assert service.firecrawl_key == ""

    def test_prod_config_with_firecrawl(self):
        """Test production configuration uses Firecrawl."""
        with patch.dict('os.environ', {
            'USE_CRAWL4AI': 'false',
            'FIRECRAWL_API_KEY': 'test-key'
        }):
            service = CrawlerService()
            
            assert service.use_crawl4ai is False
            assert service.firecrawl_key == "test-key"


class TestRawSignal:
    """Test RawSignal dataclass."""

    def test_raw_signal_creation(self):
        """Test creating a RawSignal object."""
        signal = RawSignal(
            source="indie_hackers",
            url="https://indiehackers.com/post/123",
            title="How I built my SaaS",
            content="This is the content..."
        )
        
        assert signal.source == "indie_hackers"
        assert signal.url == "https://indiehackers.com/post/123"
        assert signal.title == "How I built my SaaS"
        assert signal.content == "This is the content..."


class TestCrawlerServiceGetMarketSignals:
    """Test get_market_signals method."""

    @pytest.mark.asyncio
    async def test_fetch_all_sources_concurrently(self):
        """Test fetching from all sources concurrently."""
        service = CrawlerService()
        
        # Mock all fetch methods
        with patch.object(service, '_fetch_source', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = RawSignal(
                source="test",
                url="https://test.com",
                title="Test",
                content="Content"
            )
            
            signals = await service.get_market_signals()
            
            # Should call _fetch_source for each source
            assert mock_fetch.call_count == len(SOURCES)
            assert len(signals) == len(SOURCES)

    @pytest.mark.asyncio
    async def test_handles_exceptions_gracefully(self):
        """Test that exceptions in one source don't break others."""
        service = CrawlerService()
        
        async def side_effect(source):
            if source["name"] == "reddit_startups":
                raise Exception("Network error")
            return RawSignal(
                source=source["name"],
                url=source["url"],
                title="Test",
                content="Content"
            )
        
        with patch.object(service, '_fetch_source', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = side_effect
            
            signals = await service.get_market_signals()
            
            # Should still get signals from successful sources
            assert len(signals) == len(SOURCES) - 1


class TestCrawlerServiceRedditJson:
    """Test Reddit JSON API fetching."""

    @pytest.mark.asyncio
    async def test_fetch_reddit_success(self):
        """Test successful Reddit fetch."""
        service = CrawlerService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Test Post",
                            "selftext": "This is the content",
                            "permalink": "/r/startups/comments/abc/test/"
                        }
                    }
                ]
            }
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client_class.return_value = mock_client

            signals = await service._fetch_reddit_json({
                "name": "reddit_startups",
                "url": "https://reddit.com/r/startups/hot.json?limit=10"
            })

            assert len(signals) == 1
            assert signals[0].title == "Test Post"
            assert "reddit.com" in signals[0].url

    @pytest.mark.asyncio
    async def test_fetch_reddit_failure(self):
        """Test Reddit fetch with non-200 status."""
        service = CrawlerService()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client_class.return_value = mock_client

            signals = await service._fetch_reddit_json({
                "name": "reddit_startups",
                "url": "https://reddit.com/r/startups/hot.json?limit=10"
            })

            assert signals == []


class TestCrawlerServiceCrawl4AI:
    """Test Crawl4AI scraping."""

    @pytest.mark.asyncio
    async def test_crawl4ai_success(self):
        """Test successful Crawl4AI scrape."""
        service = CrawlerService()
        
        # Mock POST response
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"task_id": "task-123"}
        
        # Mock GET response (polling)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "status": "completed",
            "results": [{"markdown": "# Test Content"}]
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_post_response
            mock_client.get.return_value = mock_get_response
            mock_client.__aenter__.return_value = mock_client
            mock_client_class.return_value = mock_client
            
            signal = await service._crawl4ai_scrape({"name": "indie_hackers", "url": "https://test.com"})
            
            assert signal is not None
            assert signal.source == "indie_hackers"
            assert signal.content == "# Test Content"

    @pytest.mark.asyncio
    async def test_crawl4ai_timeout(self):
        """Test Crawl4AI task timeout."""
        service = CrawlerService()
        
        # Mock POST response
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"task_id": "task-123"}
        
        # Mock GET response (still processing)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"status": "processing"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_post_response
            mock_client.get.return_value = mock_get_response
            mock_client.__aenter__.return_value = mock_client
            mock_client_class.return_value = mock_client
            
            signal = await service._crawl4ai_scrape({"name": "indie_hackers", "url": "https://test.com"})
            
            # Should return None after timeout
            assert signal is None


class TestCrawlerServiceFirecrawl:
    """Test Firecrawl scraping."""

    @pytest.mark.asyncio
    async def test_firecrawl_success(self):
        """Test successful Firecrawl scrape."""
        service = CrawlerService()
        service.firecrawl_key = "test-key"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"markdown": "# Firecrawl Content"}
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client_class.return_value = mock_client
            
            signal = await service._firecrawl_scrape({"name": "indie_hackers", "url": "https://test.com"})
            
            assert signal is not None
            assert signal.content == "# Firecrawl Content"

    @pytest.mark.asyncio
    async def test_firecrawl_no_api_key(self):
        """Test Firecrawl without API key."""
        service = CrawlerService()
        service.firecrawl_key = ""
        
        signal = await service._firecrawl_scrape({"name": "indie_hackers", "url": "https://test.com"})
        
        assert signal is None
