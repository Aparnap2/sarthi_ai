"""
Rate Limiter Implementation — Sarthi v4.2 Phase 7.

Implements rate limiting for external API calls:
- Telegram API (5 req/s)
- Azure OpenAI (per deployment limits)
- gRPC calls

Uses token bucket algorithm for smooth rate limiting.

Usage:
    from src.resilience.rate_limiter import RateLimiter
    
    limiter = RateLimiter(
        name="telegram",
        rate=5,  # 5 requests per second
        burst=10,  # Allow burst of 10
    )
    
    @limiter
    async def send_telegram_message():
        # ... implementation
"""

import time
import asyncio
from functools import wraps
from typing import Callable, Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class TokenBucket:
    """
    Token bucket rate limiter.
    
    Attributes:
        rate: Tokens per second
        burst: Maximum bucket capacity
    """
    
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False otherwise
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Add tokens based on elapsed time
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_for_token(self, tokens: int = 1) -> None:
        """
        Wait until tokens are available.
        
        Args:
            tokens: Number of tokens to acquire
        """
        while not await self.acquire(tokens):
            # Calculate wait time
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)


class RateLimiter:
    """
    Rate limiter for API calls.
    
    Attributes:
        name: Unique identifier for this rate limiter
        rate: Requests per second
        burst: Maximum burst size
    """
    
    def __init__(self, name: str, rate: float, burst: int):
        self.name = name
        self.rate = rate
        self.burst = burst
        self._bucket = TokenBucket(rate, burst)
        self._request_count = 0
        self._rejected_count = 0
    
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        await self._bucket.wait_for_token()
        self._request_count += 1
    
    def call(self, func: Callable) -> Callable:
        """
        Decorator to wrap function with rate limiter.
        
        Args:
            func: Async function to wrap
            
        Returns:
            Wrapped function
        """
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("RateLimiter only works with async functions")
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            await self.acquire()
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self._rejected_count += 1
                raise
        return wrapper
    
    def __call__(self, func: Callable) -> Callable:
        """Allow using as decorator without parentheses."""
        return self.call(func)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "name": self.name,
            "rate": self.rate,
            "burst": self.burst,
            "request_count": self._request_count,
            "rejected_count": self._rejected_count,
        }


# Global rate limiters for Sarthi services
_telegram_limiter: Optional[RateLimiter] = None
_azure_openai_limiter: Optional[RateLimiter] = None
_grpc_limiter: Optional[RateLimiter] = None


def get_telegram_limiter() -> RateLimiter:
    """
    Get or create Telegram API rate limiter.
    
    Telegram limits: 5 requests per second for bots
    """
    global _telegram_limiter
    if _telegram_limiter is None:
        _telegram_limiter = RateLimiter(
            name="telegram",
            rate=5.0,  # 5 requests per second
            burst=10,  # Allow burst of 10
        )
    return _telegram_limiter


def get_azure_openai_limiter() -> RateLimiter:
    """
    Get or create Azure OpenAI rate limiter.
    
    Azure OpenAI limits vary by deployment and region.
    Default: 20 requests per minute (0.33 req/s) for standard deployments.
    Adjust based on your specific deployment limits.
    """
    global _azure_openai_limiter
    if _azure_openai_limiter is None:
        _azure_openai_limiter = RateLimiter(
            name="azure_openai",
            rate=0.5,  # Conservative: 0.5 requests per second
            burst=5,  # Allow burst of 5
        )
    return _azure_openai_limiter


def get_grpc_limiter() -> RateLimiter:
    """
    Get or create gRPC rate limiter.
    
    gRPC to Python agents: 10 requests per second
    """
    global _grpc_limiter
    if _grpc_limiter is None:
        _grpc_limiter = RateLimiter(
            name="grpc",
            rate=10.0,  # 10 requests per second
            burst=20,  # Allow burst of 20
        )
    return _grpc_limiter


def reset_all_limiters() -> None:
    """Reset all rate limiters (for testing)."""
    global _telegram_limiter, _azure_openai_limiter, _grpc_limiter
    
    _telegram_limiter = None
    _azure_openai_limiter = None
    _grpc_limiter = None
