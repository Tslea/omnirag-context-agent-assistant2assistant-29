"""
Retry Logic with Exponential Backoff

Provides retry utilities for handling transient failures.
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from backend.core.exceptions import (
    OMNIError,
    AgentError,
    AgentTimeoutError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    VectorDBConnectionError,
    is_recoverable,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default retryable exception types
DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    AgentTimeoutError,
    LLMTimeoutError,
    LLMRateLimitError,
    VectorDBConnectionError,
    asyncio.TimeoutError,
    ConnectionError,
    TimeoutError,
)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Tuple of exception types to retry on
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or DEFAULT_RETRYABLE_EXCEPTIONS
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Uses exponential backoff with optional jitter.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (exponential_base ^ attempt)
        delay = self.base_delay * (self.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter (±25% randomization)
        if self.jitter:
            jitter_range = delay * 0.25
            delay = delay + random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


# Default configurations for different scenarios
RETRY_FAST = RetryConfig(max_retries=2, base_delay=0.5, max_delay=5.0)
RETRY_STANDARD = RetryConfig(max_retries=3, base_delay=1.0, max_delay=30.0)
RETRY_PATIENT = RetryConfig(max_retries=5, base_delay=2.0, max_delay=60.0)


def should_retry(
    exception: Exception,
    config: RetryConfig,
) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exception: The exception that was raised
        config: Retry configuration
        
    Returns:
        True if should retry, False otherwise
    """
    # Check if it's a known retryable exception type
    if isinstance(exception, config.retryable_exceptions):
        return True
    
    # Check OMNI exception's recoverable flag
    if isinstance(exception, OMNIError):
        return exception.recoverable
    
    # Use helper function for other exceptions
    return is_recoverable(exception)


async def retry_async(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    **kwargs,
) -> Any:
    """
    Execute an async function with retry logic.
    
    Args:
        func: Async function to execute
        *args: Positional arguments to pass to func
        config: Retry configuration (default: RETRY_STANDARD)
        on_retry: Optional callback called on each retry (exception, attempt)
        **kwargs: Keyword arguments to pass to func
        
    Returns:
        Result from successful function execution
        
    Raises:
        The last exception if all retries fail
    """
    config = config or RETRY_STANDARD
    last_exception: Optional[Exception] = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
            
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            if attempt >= config.max_retries or not should_retry(e, config):
                raise
            
            # Calculate delay
            delay = config.calculate_delay(attempt)
            
            # Log retry attempt
            logger.warning(
                f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                f"after {delay:.2f}s due to: {e}"
            )
            
            # Call retry callback if provided
            if on_retry:
                try:
                    on_retry(e, attempt + 1)
                except Exception:
                    pass  # Don't let callback errors affect retry logic
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # Should not reach here, but just in case
    if last_exception:
        raise last_exception


def with_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        config: Retry configuration
        on_retry: Optional callback on retry
        
    Example:
        ```python
        @with_retry(config=RETRY_FAST)
        async def fetch_data():
            return await api.get("/data")
        ```
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await retry_async(
                func, *args, config=config, on_retry=on_retry, **kwargs
            )
        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry operations with state tracking.
    
    Useful when you need to track retry state across operations.
    
    Example:
        ```python
        async with RetryContext(config=RETRY_STANDARD) as ctx:
            while ctx.should_continue():
                try:
                    result = await risky_operation()
                    break
                except RecoverableError as e:
                    await ctx.handle_error(e)
        ```
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RETRY_STANDARD
        self.attempt = 0
        self.last_error: Optional[Exception] = None
        self.total_delay = 0.0
    
    async def __aenter__(self) -> "RetryContext":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Don't suppress exceptions
        return False
    
    def should_continue(self) -> bool:
        """Check if we should continue retrying."""
        return self.attempt <= self.config.max_retries
    
    async def handle_error(self, error: Exception) -> None:
        """
        Handle an error and wait before next attempt.
        
        Args:
            error: The exception that occurred
            
        Raises:
            The error if it's not retryable or max retries exceeded
        """
        self.last_error = error
        
        if not should_retry(error, self.config):
            raise error
        
        if self.attempt >= self.config.max_retries:
            raise error
        
        delay = self.config.calculate_delay(self.attempt)
        self.total_delay += delay
        
        logger.warning(
            f"RetryContext: attempt {self.attempt + 1}/{self.config.max_retries}, "
            f"waiting {delay:.2f}s"
        )
        
        await asyncio.sleep(delay)
        self.attempt += 1
    
    @property
    def retries_remaining(self) -> int:
        """Get number of retries remaining."""
        return max(0, self.config.max_retries - self.attempt)


# Convenience function for one-off retries
async def with_timeout_and_retry(
    func: Callable[..., Any],
    *args,
    timeout: float = 30.0,
    config: Optional[RetryConfig] = None,
    **kwargs,
) -> Any:
    """
    Execute an async function with both timeout and retry logic.
    
    Args:
        func: Async function to execute
        *args: Positional arguments
        timeout: Timeout in seconds for each attempt
        config: Retry configuration
        **kwargs: Keyword arguments
        
    Returns:
        Result from successful execution
    """
    config = config or RETRY_STANDARD
    
    async def timed_func(*a, **kw):
        return await asyncio.wait_for(func(*a, **kw), timeout=timeout)
    
    return await retry_async(timed_func, *args, config=config, **kwargs)
