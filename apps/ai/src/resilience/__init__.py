"""
Resilience module for Sarthi v4.2.

Provides circuit breakers and rate limiters for external service calls.

Usage:
    from src.resilience import (
        get_azure_openai_breaker,
        get_telegram_limiter,
    )
    
    @get_azure_openai_breaker()
    @get_azure_openai_limiter()
    async def call_azure_openai():
        # ... implementation
"""

from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    get_azure_openai_breaker,
    get_grpc_breaker,
    get_telegram_breaker,
    reset_all_breakers,
)

from src.resilience.rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    get_azure_openai_limiter,
    get_grpc_limiter,
    get_telegram_limiter,
    reset_all_limiters,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitState",
    "get_azure_openai_breaker",
    "get_grpc_breaker",
    "get_telegram_breaker",
    "reset_all_breakers",
    # Rate Limiter
    "RateLimiter",
    "RateLimitExceeded",
    "get_azure_openai_limiter",
    "get_grpc_limiter",
    "get_telegram_limiter",
    "reset_all_limiters",
]
