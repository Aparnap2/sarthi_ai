"""
CrawlerService — market signal ingestion.

Dev:  USE_CRAWL4AI=true  → local Crawl4AI Docker (zero cost)
Prod: USE_CRAWL4AI=false → Firecrawl (500 free credits total)
"""

import os
import httpx
import asyncio
from dataclasses import dataclass
from typing import Optional, List
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RawSignal:
    """Raw market signal from a source."""
    source: str
    url: str
    title: str
    content: str


# Market signal sources to monitor
SOURCES = [
    {
        "name": "indie_hackers",
        "url": "https://www.indiehackers.com/posts",
        "type": "crawl",
    },
    {
        "name": "reddit_startups",
        "url": "https://www.reddit.com/r/startups/hot.json?limit=10",
        "type": "json",  # Reddit has public JSON API
    },
    {
        "name": "product_hunt",
        "url": "https://www.producthunt.com/posts",
        "type": "crawl",
    },
]


class CrawlerService:
    """
    Fetches market signals from various sources.
    
    Uses Crawl4AI for local development (zero cost) and
    Firecrawl for production (500 free credits total).
    """

    def __init__(self):
        self.use_crawl4ai = os.getenv("USE_CRAWL4AI", "true").lower() == "true"
        self.crawl4ai_url = os.getenv("CRAWL4AI_URL", "http://localhost:11235")
        self.crawl4ai_token = os.getenv("CRAWL4AI_API_TOKEN", "saarathi-local")
        self.firecrawl_key = os.getenv("FIRECRAWL_API_KEY", "")

    async def get_market_signals(self) -> List[RawSignal]:
        """
        Fetch signals from all sources concurrently.
        
        Returns:
            List of raw market signals
        """
        tasks = [self._fetch_source(s) for s in SOURCES]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        signals = []
        for r in results:
            if isinstance(r, RawSignal):
                signals.append(r)
            elif isinstance(r, list):
                signals.extend(r)
            elif isinstance(r, Exception):
                logger.error("Failed to fetch source", error=str(r))
        
        logger.info("Fetched market signals", count=len(signals))
        return signals

    async def _fetch_source(self, source: dict):
        """Fetch from a single source."""
        if source["type"] == "json":
            return await self._fetch_reddit_json(source)
        
        if self.use_crawl4ai:
            return await self._crawl4ai_scrape(source)
        return await self._firecrawl_scrape(source)

    async def _fetch_reddit_json(self, source: dict) -> List[RawSignal]:
        """
        Reddit's public JSON endpoint — completely free.
        
        Args:
            source: Source configuration dict
            
        Returns:
            List of RawSignal objects
        """
        headers = {"User-Agent": "Saarathi/1.0 founder-agent"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(source["url"], headers=headers)
            if resp.status_code != 200:
                logger.warning("Reddit fetch failed", status=resp.status_code)
                return []
            
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            
            signals = [
                RawSignal(
                    source=source["name"],
                    url=f"https://reddit.com{p['data'].get('permalink', '')}",
                    title=p["data"].get("title", ""),
                    content=p["data"].get("selftext", "")[:1500],
                )
                for p in posts
                if p["data"].get("title")
            ]
            
            logger.info("Fetched Reddit signals", count=len(signals))
            return signals

    async def _crawl4ai_scrape(self, source: dict) -> Optional[RawSignal]:
        """
        Crawl4AI v0.8+ REST API.
        
        Args:
            source: Source configuration dict
            
        Returns:
            RawSignal or None if failed
        """
        async with httpx.AsyncClient(timeout=45) as client:
            try:
                resp = await client.post(
                    f"{self.crawl4ai_url}/crawl",
                    headers={"Authorization": f"Bearer {self.crawl4ai_token}"},
                    json={
                        "urls": [source["url"]],
                        "priority": 5,
                        "crawler_params": {
                            "headless": True,
                            "word_count_threshold": 50,
                        },
                    }
                )
            except Exception as e:
                logger.error("Crawl4AI scrape failed", error=str(e))
                return None
            
            if resp.status_code != 200:
                logger.warning("Crawl4AI POST failed", status=resp.status_code)
                return None
            
            task_id = resp.json().get("task_id")
            if not task_id:
                logger.warning("No task_id in Crawl4AI response")
                return None
            
            return await self._poll_crawl4ai(client, source, task_id)

    async def _poll_crawl4ai(
        self,
        client: httpx.AsyncClient,
        source: dict,
        task_id: str,
        max_attempts: int = 10
    ) -> Optional[RawSignal]:
        """
        Poll Crawl4AI task until complete.
        
        Args:
            client: HTTP client
            source: Source configuration
            task_id: Crawl4AI task ID
            max_attempts: Maximum polling attempts
            
        Returns:
            RawSignal or None if failed
        """
        for _ in range(max_attempts):
            await asyncio.sleep(3)
            
            try:
                status = await client.get(
                    f"{self.crawl4ai_url}/task/{task_id}",
                    headers={"Authorization": f"Bearer {self.crawl4ai_token}"}
                )
            except Exception as e:
                logger.error("Crawl4AI poll failed", error=str(e))
                continue
            
            if status.status_code != 200:
                continue
            
            data = status.json()
            if data.get("status") == "completed":
                results = data.get("results", [{}])
                markdown = results[0].get("markdown", {})
                
                content = markdown if isinstance(markdown, str) \
                          else markdown.get("raw_markdown", "")
                
                logger.info("Crawl4AI task completed", source=source["name"])
                
                return RawSignal(
                    source=source["name"],
                    url=source["url"],
                    title=source["name"].replace("_", " ").title(),
                    content=content[:3000],
                )
        
        logger.warning("Crawl4AI task timeout", task_id=task_id)
        return None

    async def _firecrawl_scrape(self, source: dict) -> Optional[RawSignal]:
        """
        Firecrawl API — use only in prod (500 free credits total).
        
        Args:
            source: Source configuration dict
            
        Returns:
            RawSignal or None if failed
        """
        if not self.firecrawl_key:
            logger.warning("Firecrawl API key not set")
            return None
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    headers={"Authorization": f"Bearer {self.firecrawl_key}"},
                    json={"url": source["url"], "formats": ["markdown"]}
                )
            except Exception as e:
                logger.error("Firecrawl scrape failed", error=str(e))
                return None
            
            if resp.status_code == 200:
                content = resp.json().get("data", {}).get("markdown", "")
                logger.info("Firecrawl scrape successful", source=source["name"])
                
                return RawSignal(
                    source=source["name"],
                    url=source["url"],
                    title=source["name"].replace("_", " ").title(),
                    content=content[:3000],
                )
        
        logger.warning("Firecrawl scrape failed", status=resp.status_code if 'resp' in locals() else "unknown")
        return None
