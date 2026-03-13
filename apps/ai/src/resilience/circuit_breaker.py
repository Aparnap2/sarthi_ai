"""
Circuit Breaker Implementation — Sarthi v4.2 Phase 7.

Implements circuit breaker pattern for external service calls:
- Azure OpenAI
- gRPC calls
- Telegram API

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit tripped, requests fail fast
- HALF_OPEN: Testing if service recovered

Usage:
    from src.resilience.circuit_breaker import CircuitBreaker
    
    breaker = CircuitBreaker(
        name="azure_openai",
        failure_threshold=5,
        recovery_timeout=30,
    )
    
    @breaker
    def call_azure_openai():
        # ... implementation
"""

import time
import asyncio
from functools import wraps
from typing import Callable, Any, Optional, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Attributes:
        name: Unique identifier for this circuit breaker
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying again
        expected_exception: Exception type to count as failure
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit '{self.name}' entering HALF_OPEN state")
        return self._state
    
    def _record_success(self) -> None:
        """Record successful call."""
        self._failure_count = 0
        self._success_count += 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info(f"Circuit '{self.name}' closed after successful call")
    
    def _record_failure(self) -> None:
        """Record failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit '{self.name}' opened after {self._failure_count} failures"
            )
    
    def call(self, func: Callable) -> Callable:
        """
        Decorator to wrap function with circuit breaker.
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                if self.state == CircuitState.OPEN:
                    raise CircuitBreakerError(
                        f"Circuit '{self.name}' is OPEN - service unavailable"
                    )
                
                try:
                    result = await func(*args, **kwargs)
                    self._record_success()
                    return result
                except self.expected_exception as e:
                    self._record_failure()
                    raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                if self.state == CircuitState.OPEN:
                    raise CircuitBreakerError(
                        f"Circuit '{self.name}' is OPEN - service unavailable"
                    )
                
                try:
                    result = func(*args, **kwargs)
                    self._record_success()
                    return result
                except self.expected_exception as e:
                    self._record_failure()
                    raise
            return sync_wrapper
    
    def __call__(self, func: Callable) -> Callable:
        """Allow using as decorator without parentheses."""
        return self.call(func)
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        logger.info(f"Circuit '{self.name}' manually reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


# Global circuit breakers for Sarthi services
_azure_openai_breaker: Optional[CircuitBreaker] = None
_grpc_breaker: Optional[CircuitBreaker] = None
_telegram_breaker: Optional[CircuitBreaker] = None


def get_azure_openai_breaker() -> CircuitBreaker:
    """Get or create Azure OpenAI circuit breaker."""
    global _azure_openai_breaker
    if _azure_openai_breaker is None:
        _azure_openai_breaker = CircuitBreaker(
            name="azure_openai",
            failure_threshold=5,
            recovery_timeout=60.0,  # 1 minute
            expected_exception=Exception,
        )
    return _azure_openai_breaker


def get_grpc_breaker() -> CircuitBreaker:
    """Get or create gRPC circuit breaker."""
    global _grpc_breaker
    if _grpc_breaker is None:
        _grpc_breaker = CircuitBreaker(
            name="grpc",
            failure_threshold=3,
            recovery_timeout=30.0,  # 30 seconds
            expected_exception=Exception,
        )
    return _grpc_breaker


def get_telegram_breaker() -> CircuitBreaker:
    """Get or create Telegram API circuit breaker."""
    global _telegram_breaker
    if _telegram_breaker is None:
        _telegram_breaker = CircuitBreaker(
            name="telegram",
            failure_threshold=5,
            recovery_timeout=30.0,  # 30 seconds
            expected_exception=Exception,
        )
    return _telegram_breaker


def reset_all_breakers() -> None:
    """Reset all circuit breakers."""
    global _azure_openai_breaker, _grpc_breaker, _telegram_breaker
    
    for breaker in [_azure_openai_breaker, _grpc_breaker, _telegram_breaker]:
        if breaker is not None:
            breaker.reset()
