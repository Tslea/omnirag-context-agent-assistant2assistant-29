"""
Tests for Timeout Management

Tests the timeout utilities and budget management.
"""

import asyncio
import pytest
from datetime import datetime

from backend.core.timeout import (
    TimeoutConfig,
    TimeoutResult,
    TimeoutTracker,
    TimeoutBudget,
    timeout_context,
    with_timeout,
    run_with_timeout,
    DEFAULT_TIMEOUT_CONFIG,
)
from backend.core.exceptions import AgentTimeoutError, WorkflowTimeoutError


class TestTimeoutConfig:
    """Tests for TimeoutConfig."""
    
    def test_default_values(self):
        """Should have sensible defaults."""
        config = TimeoutConfig()
        assert config.agent_timeout == 30.0
        assert config.workflow_timeout == 300.0
        assert config.llm_timeout == 60.0
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        config = TimeoutConfig()
        d = config.to_dict()
        assert "agent_timeout" in d
        assert "workflow_timeout" in d


class TestTimeoutContext:
    """Tests for timeout_context."""
    
    @pytest.mark.asyncio
    async def test_success_within_timeout(self):
        """Should complete successfully within timeout."""
        async with timeout_context(1.0, "test_op") as tracker:
            await asyncio.sleep(0.01)
            result = "done"
        
        assert result == "done"
        assert not tracker.timed_out
        assert tracker.elapsed_seconds < 1.0
    
    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """Should raise error on timeout."""
        with pytest.raises(AgentTimeoutError) as exc_info:
            async with timeout_context(0.05, "slow_op"):
                await asyncio.sleep(1.0)
        
        assert "slow_op timed out" in str(exc_info.value)
        assert exc_info.value.timeout_seconds == 0.05
    
    @pytest.mark.asyncio
    async def test_tracker_remaining_time(self):
        """Should track remaining time."""
        async with timeout_context(1.0, "test_op") as tracker:
            assert tracker.remaining_seconds > 0.9
            await asyncio.sleep(0.1)
            assert tracker.remaining_seconds < 0.95


class TestWithTimeoutDecorator:
    """Tests for with_timeout decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Decorated function should work within timeout."""
        @with_timeout(1.0)
        async def quick_func():
            return "result"
        
        result = await quick_func()
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_decorator_timeout(self):
        """Decorated function should timeout."""
        @with_timeout(0.05)
        async def slow_func():
            await asyncio.sleep(1.0)
            return "never"
        
        with pytest.raises(AgentTimeoutError):
            await slow_func()


class TestRunWithTimeout:
    """Tests for run_with_timeout function."""
    
    @pytest.mark.asyncio
    async def test_success_result(self):
        """Should return success result."""
        async def quick():
            return 42
        
        result = await run_with_timeout(quick(), 1.0, "test")
        
        assert result.success is True
        assert result.value == 42
        assert result.timed_out is False
    
    @pytest.mark.asyncio
    async def test_timeout_with_raise(self):
        """Should raise on timeout by default."""
        async def slow():
            await asyncio.sleep(1.0)
        
        with pytest.raises(AgentTimeoutError):
            await run_with_timeout(slow(), 0.05, "slow_test")
    
    @pytest.mark.asyncio
    async def test_timeout_with_default(self):
        """Should return default on timeout if not raising."""
        async def slow():
            await asyncio.sleep(1.0)
        
        result = await run_with_timeout(
            slow(),
            0.05,
            "slow_test",
            default_on_timeout="fallback",
            raise_on_timeout=False,
        )
        
        assert result.success is False
        assert result.value == "fallback"
        assert result.timed_out is True
    
    @pytest.mark.asyncio
    async def test_error_result(self):
        """Should capture errors."""
        async def failing():
            raise ValueError("oops")
        
        result = await run_with_timeout(
            failing(),
            1.0,
            "failing_test",
            raise_on_timeout=False,
        )
        
        assert result.success is False
        assert "oops" in result.error


class TestTimeoutBudget:
    """Tests for TimeoutBudget."""
    
    @pytest.mark.asyncio
    async def test_budget_tracking(self):
        """Should track budget across steps."""
        budget = TimeoutBudget(total_seconds=1.0, name="test_workflow")
        
        async with budget.step("step1", max_seconds=0.3):
            await asyncio.sleep(0.1)
        
        assert len(budget.steps) == 1
        assert budget.steps[0]["completed"] is True
        assert budget.remaining_seconds < 1.0
    
    @pytest.mark.asyncio
    async def test_budget_exhaustion(self):
        """Should raise when budget exhausted."""
        # Create budget with very short time
        budget = TimeoutBudget(total_seconds=0.05, name="short_workflow")
        
        # Wait for budget to expire naturally
        await asyncio.sleep(0.1)
        
        # Budget should now be expired
        assert budget.is_expired
        
        # Next step should fail immediately
        with pytest.raises(WorkflowTimeoutError) as exc_info:
            async with budget.step("step_after_expiry"):
                pass
        
        assert "Budget exhausted" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_step_timeout(self):
        """Should timeout individual steps."""
        budget = TimeoutBudget(total_seconds=10.0, name="workflow")
        
        with pytest.raises(WorkflowTimeoutError) as exc_info:
            async with budget.step("slow_step", max_seconds=0.05):
                await asyncio.sleep(1.0)
        
        assert "slow_step timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_multiple_steps(self):
        """Should handle multiple steps."""
        budget = TimeoutBudget(total_seconds=2.0, name="multi_step")
        
        async with budget.step("context", max_seconds=0.5):
            await asyncio.sleep(0.05)
        
        async with budget.step("security", max_seconds=0.5):
            await asyncio.sleep(0.05)
        
        async with budget.step("compliance", max_seconds=0.5):
            await asyncio.sleep(0.05)
        
        summary = budget.get_summary()
        assert len(summary["steps"]) == 3
        assert all(s["completed"] for s in summary["steps"])
    
    @pytest.mark.asyncio
    async def test_summary(self):
        """Should provide useful summary."""
        budget = TimeoutBudget(total_seconds=5.0, name="test")
        
        async with budget.step("step1"):
            await asyncio.sleep(0.01)
        
        summary = budget.get_summary()
        
        assert summary["name"] == "test"
        assert summary["total_seconds"] == 5.0
        assert summary["elapsed_seconds"] > 0
        assert summary["remaining_seconds"] < 5.0


class TestTimeoutTracker:
    """Tests for TimeoutTracker."""
    
    def test_elapsed_time(self):
        """Should track elapsed time."""
        tracker = TimeoutTracker(10.0, "test")
        assert tracker.elapsed_seconds >= 0
        assert tracker.remaining_seconds <= 10.0
    
    def test_mark_complete(self):
        """Should mark completion."""
        tracker = TimeoutTracker(10.0, "test")
        tracker.mark_complete()
        
        assert tracker.end_time is not None
        assert not tracker.timed_out
    
    def test_mark_timeout(self):
        """Should mark timeout."""
        tracker = TimeoutTracker(10.0, "test")
        tracker.mark_timeout()
        
        assert tracker.timed_out is True
        assert tracker.end_time is not None


class TestDefaultConfig:
    """Tests for default timeout configuration."""
    
    def test_default_config_exists(self):
        """Should have default config available."""
        assert DEFAULT_TIMEOUT_CONFIG is not None
        assert DEFAULT_TIMEOUT_CONFIG.agent_timeout > 0
