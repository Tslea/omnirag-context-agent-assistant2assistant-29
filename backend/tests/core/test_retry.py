"""
Tests for Retry Logic

Tests the retry utilities and exponential backoff.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.core.retry import (
    RetryConfig,
    RetryContext,
    RETRY_FAST,
    RETRY_STANDARD,
    RETRY_PATIENT,
    retry_async,
    with_retry,
    with_timeout_and_retry,
    should_retry,
)
from backend.core.exceptions import (
    AgentTimeoutError,
    AgentValidationError,
    LLMRateLimitError,
    LLMAuthenticationError,
)


class TestRetryConfig:
    """Tests for RetryConfig."""
    
    def test_default_values(self):
        """Should have sensible defaults."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_custom_values(self):
        """Should accept custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
    
    def test_calculate_delay_exponential(self):
        """Should calculate exponential backoff."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        assert config.calculate_delay(0) == 1.0   # 1 * 2^0 = 1
        assert config.calculate_delay(1) == 2.0   # 1 * 2^1 = 2
        assert config.calculate_delay(2) == 4.0   # 1 * 2^2 = 4
        assert config.calculate_delay(3) == 8.0   # 1 * 2^3 = 8
    
    def test_calculate_delay_max_cap(self):
        """Should cap delay at max_delay."""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, jitter=False)
        
        assert config.calculate_delay(0) == 10.0
        assert config.calculate_delay(1) == 15.0  # Would be 20, capped at 15
        assert config.calculate_delay(5) == 15.0  # Would be 320, capped at 15
    
    def test_calculate_delay_with_jitter(self):
        """Jitter should add randomization."""
        config = RetryConfig(base_delay=10.0, jitter=True)
        
        # Run multiple times - values should vary
        delays = [config.calculate_delay(0) for _ in range(10)]
        
        # All should be within ±25% of base (7.5 to 12.5)
        for delay in delays:
            assert 7.5 <= delay <= 12.5
        
        # Should have some variation (not all the same)
        assert len(set(delays)) > 1


class TestShouldRetry:
    """Tests for should_retry function."""
    
    def test_retryable_exceptions(self):
        """Should retry on retryable exception types."""
        config = RetryConfig()
        
        assert should_retry(AgentTimeoutError("timeout"), config) is True
        assert should_retry(LLMRateLimitError("rate limited"), config) is True
        assert should_retry(asyncio.TimeoutError(), config) is True
        assert should_retry(ConnectionError(), config) is True
    
    def test_non_retryable_exceptions(self):
        """Should not retry on non-retryable exceptions."""
        config = RetryConfig()
        
        # Validation errors are not recoverable
        assert should_retry(AgentValidationError("invalid"), config) is False
        
        # Auth errors are not recoverable
        assert should_retry(LLMAuthenticationError("bad key"), config) is False
        
        # Standard exceptions without recoverable flag
        assert should_retry(ValueError("bad value"), config) is False
        assert should_retry(KeyError("missing"), config) is False


class TestRetryAsync:
    """Tests for retry_async function."""
    
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Should return immediately on success."""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_async(mock_func, config=RETRY_FAST)
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Should retry on timeout errors."""
        mock_func = AsyncMock(side_effect=[
            AgentTimeoutError("timeout"),
            AgentTimeoutError("timeout"),
            "success",
        ])
        
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        result = await retry_async(mock_func, config=config)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_fail_after_max_retries(self):
        """Should fail after max retries exceeded."""
        mock_func = AsyncMock(side_effect=AgentTimeoutError("always timeout"))
        
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        
        with pytest.raises(AgentTimeoutError):
            await retry_async(mock_func, config=config)
        
        assert mock_func.call_count == 3  # Initial + 2 retries
    
    @pytest.mark.asyncio
    async def test_no_retry_on_non_recoverable(self):
        """Should not retry non-recoverable errors."""
        mock_func = AsyncMock(side_effect=AgentValidationError("invalid"))
        
        config = RetryConfig(max_retries=3, base_delay=0.01)
        
        with pytest.raises(AgentValidationError):
            await retry_async(mock_func, config=config)
        
        assert mock_func.call_count == 1  # No retries
    
    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        """Should call on_retry callback on each retry."""
        mock_func = AsyncMock(side_effect=[
            AgentTimeoutError("timeout"),
            "success",
        ])
        on_retry = MagicMock()
        
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        await retry_async(mock_func, config=config, on_retry=on_retry)
        
        assert on_retry.call_count == 1
        on_retry.assert_called_once()
        # First arg is exception, second is attempt number
        call_args = on_retry.call_args[0]
        assert isinstance(call_args[0], AgentTimeoutError)
        assert call_args[1] == 1


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Decorated function should work normally on success."""
        call_count = 0
        
        @with_retry(config=RETRY_FAST)
        async def my_func():
            nonlocal call_count
            call_count += 1
            return "result"
        
        result = await my_func()
        
        assert result == "result"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_decorator_retry(self):
        """Decorated function should retry on recoverable errors."""
        call_count = 0
        
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        
        @with_retry(config=config)
        async def my_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AgentTimeoutError("timeout")
            return "success"
        
        result = await my_func()
        
        assert result == "success"
        assert call_count == 3


class TestRetryContext:
    """Tests for RetryContext context manager."""
    
    @pytest.mark.asyncio
    async def test_context_success(self):
        """Should work for successful operations."""
        async with RetryContext() as ctx:
            assert ctx.should_continue() is True
            assert ctx.attempt == 0
    
    @pytest.mark.asyncio
    async def test_context_retry_tracking(self):
        """Should track retry attempts."""
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        
        async with RetryContext(config=config) as ctx:
            attempt_count = 0
            while ctx.should_continue():
                try:
                    attempt_count += 1
                    if attempt_count < 3:
                        raise AgentTimeoutError("timeout")
                    break
                except AgentTimeoutError as e:
                    await ctx.handle_error(e)
            
            assert attempt_count == 3
            assert ctx.retries_remaining == 1  # Started with 3, used 2
    
    @pytest.mark.asyncio
    async def test_context_max_retries(self):
        """Should raise after max retries."""
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        
        with pytest.raises(AgentTimeoutError):
            async with RetryContext(config=config) as ctx:
                while ctx.should_continue():
                    try:
                        raise AgentTimeoutError("always fails")
                    except AgentTimeoutError as e:
                        await ctx.handle_error(e)


class TestWithTimeoutAndRetry:
    """Tests for with_timeout_and_retry function."""
    
    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """Should retry when operation times out."""
        call_count = 0
        
        async def slow_then_fast():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                await asyncio.sleep(1.0)  # Will timeout
            return "success"
        
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        result = await with_timeout_and_retry(
            slow_then_fast,
            timeout=0.05,
            config=config,
        )
        
        assert result == "success"
        assert call_count == 3


class TestPresetConfigs:
    """Tests for preset configurations."""
    
    def test_retry_fast(self):
        """RETRY_FAST should be for quick retries."""
        assert RETRY_FAST.max_retries == 2
        assert RETRY_FAST.base_delay == 0.5
        assert RETRY_FAST.max_delay == 5.0
    
    def test_retry_standard(self):
        """RETRY_STANDARD should be balanced."""
        assert RETRY_STANDARD.max_retries == 3
        assert RETRY_STANDARD.base_delay == 1.0
        assert RETRY_STANDARD.max_delay == 30.0
    
    def test_retry_patient(self):
        """RETRY_PATIENT should be for long operations."""
        assert RETRY_PATIENT.max_retries == 5
        assert RETRY_PATIENT.base_delay == 2.0
        assert RETRY_PATIENT.max_delay == 60.0
