"""
Timeout Management

Provides timeout utilities for async operations.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from backend.core.exceptions import (
    AgentTimeoutError,
    WorkflowTimeoutError,
    ErrorContext,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass 
class TimeoutConfig:
    """Configuration for timeout behavior."""
    # Default timeouts in seconds
    agent_timeout: float = 30.0  # Single agent operation
    workflow_timeout: float = 300.0  # Full workflow (5 min)
    llm_timeout: float = 60.0  # LLM API call
    vectordb_timeout: float = 30.0  # Vector DB operation
    
    # Timeout for specific operations
    workspace_scan_timeout: float = 600.0  # 10 min for full scan
    file_analysis_timeout: float = 30.0  # Single file
    code_validation_timeout: float = 15.0  # Quick validation
    
    # Partial results behavior
    return_partial_on_timeout: bool = True
    
    def to_dict(self) -> dict[str, float]:
        return {
            "agent_timeout": self.agent_timeout,
            "workflow_timeout": self.workflow_timeout,
            "llm_timeout": self.llm_timeout,
            "vectordb_timeout": self.vectordb_timeout,
            "workspace_scan_timeout": self.workspace_scan_timeout,
            "file_analysis_timeout": self.file_analysis_timeout,
            "code_validation_timeout": self.code_validation_timeout,
        }


# Global default config
DEFAULT_TIMEOUT_CONFIG = TimeoutConfig()


@dataclass
class TimeoutResult:
    """Result from a timed operation."""
    success: bool
    value: Any = None
    timed_out: bool = False
    elapsed_seconds: float = 0.0
    error: Optional[str] = None


@asynccontextmanager
async def timeout_context(
    seconds: float,
    operation: str = "operation",
    error_class: type = AgentTimeoutError,
    context: Optional[ErrorContext] = None,
):
    """
    Async context manager with timeout.
    
    Usage:
        async with timeout_context(30.0, "agent_process") as timer:
            result = await some_operation()
        # Raises AgentTimeoutError if takes > 30s
    
    Args:
        seconds: Timeout in seconds
        operation: Name of operation (for error messages)
        error_class: Exception class to raise on timeout
        context: Optional error context
        
    Yields:
        TimeoutTracker for optional progress checking
    """
    tracker = TimeoutTracker(seconds, operation)
    
    try:
        async with asyncio.timeout(seconds):
            yield tracker
    except asyncio.TimeoutError:
        tracker.mark_timeout()
        raise error_class(
            f"{operation} timed out after {seconds}s",
            timeout_seconds=seconds,
            context=context,
        )
    finally:
        tracker.mark_complete()


class TimeoutTracker:
    """Tracks elapsed time during timeout context."""
    
    def __init__(self, timeout_seconds: float, operation: str):
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.timed_out = False
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def remaining_seconds(self) -> float:
        """Get remaining time before timeout."""
        return max(0, self.timeout_seconds - self.elapsed_seconds)
    
    def mark_timeout(self) -> None:
        """Mark that operation timed out."""
        self.timed_out = True
        self.end_time = datetime.now()
    
    def mark_complete(self) -> None:
        """Mark operation as complete."""
        if self.end_time is None:
            self.end_time = datetime.now()


def with_timeout(
    seconds: float,
    error_class: type = AgentTimeoutError,
):
    """
    Decorator to add timeout to async functions.
    
    Usage:
        @with_timeout(30.0)
        async def my_operation():
            ...
    
    Args:
        seconds: Timeout in seconds
        error_class: Exception class to raise
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                async with asyncio.timeout(seconds):
                    return await func(*args, **kwargs)
            except asyncio.TimeoutError:
                raise error_class(
                    f"{func.__name__} timed out after {seconds}s",
                    timeout_seconds=seconds,
                )
        return wrapper
    return decorator


async def run_with_timeout(
    coro,
    timeout_seconds: float,
    operation: str = "operation",
    default_on_timeout: Any = None,
    raise_on_timeout: bool = True,
) -> TimeoutResult:
    """
    Run a coroutine with timeout and structured result.
    
    Args:
        coro: Coroutine to run
        timeout_seconds: Timeout in seconds
        operation: Name for logging
        default_on_timeout: Value to return if times out
        raise_on_timeout: Whether to raise or return default
        
    Returns:
        TimeoutResult with success/value/timeout info
    """
    start = datetime.now()
    
    try:
        async with asyncio.timeout(timeout_seconds):
            value = await coro
            elapsed = (datetime.now() - start).total_seconds()
            return TimeoutResult(
                success=True,
                value=value,
                elapsed_seconds=elapsed,
            )
    except asyncio.TimeoutError:
        elapsed = (datetime.now() - start).total_seconds()
        logger.warning(f"{operation} timed out after {elapsed:.2f}s (limit: {timeout_seconds}s)")
        
        if raise_on_timeout:
            raise AgentTimeoutError(
                f"{operation} timed out",
                timeout_seconds=timeout_seconds,
            )
        
        return TimeoutResult(
            success=False,
            value=default_on_timeout,
            timed_out=True,
            elapsed_seconds=elapsed,
            error=f"Timeout after {timeout_seconds}s",
        )
    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        return TimeoutResult(
            success=False,
            elapsed_seconds=elapsed,
            error=str(e),
        )


class TimeoutBudget:
    """
    Manages timeout budget across multiple operations.
    
    Useful for workflows where total time is limited and
    each step consumes part of the budget.
    
    Usage:
        budget = TimeoutBudget(total_seconds=60.0)
        
        # Step 1: uses up to 20s of budget
        async with budget.step("context", max_seconds=20) as step:
            await context_agent.process(...)
        
        # Step 2: uses remaining budget (up to 30s)
        async with budget.step("security", max_seconds=30) as step:
            await security_agent.process(...)
        
        print(f"Total elapsed: {budget.elapsed_seconds}")
    """
    
    def __init__(
        self,
        total_seconds: float,
        name: str = "workflow",
    ):
        self.total_seconds = total_seconds
        self.name = name
        self.start_time = datetime.now()
        self.steps: list[dict] = []
    
    @property
    def elapsed_seconds(self) -> float:
        """Total elapsed time."""
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def remaining_seconds(self) -> float:
        """Remaining budget."""
        return max(0, self.total_seconds - self.elapsed_seconds)
    
    @property
    def is_expired(self) -> bool:
        """Check if budget is exhausted."""
        return self.remaining_seconds <= 0
    
    @asynccontextmanager
    async def step(
        self,
        step_name: str,
        max_seconds: Optional[float] = None,
    ):
        """
        Execute a step within the budget.
        
        Args:
            step_name: Name of the step
            max_seconds: Max time for this step (capped by remaining)
            
        Yields:
            StepContext for the step
        """
        if self.is_expired:
            raise WorkflowTimeoutError(
                f"Budget exhausted before {step_name}",
                timeout_seconds=self.total_seconds,
                completed_stages=[s["name"] for s in self.steps],
            )
        
        # Calculate actual timeout
        actual_timeout = self.remaining_seconds
        if max_seconds:
            actual_timeout = min(actual_timeout, max_seconds)
        
        step_start = datetime.now()
        step_info = {
            "name": step_name,
            "started_at": step_start.isoformat(),
            "timeout": actual_timeout,
            "completed": False,
            "timed_out": False,
        }
        
        try:
            async with asyncio.timeout(actual_timeout):
                yield StepContext(step_name, actual_timeout)
                step_info["completed"] = True
        except asyncio.TimeoutError:
            step_info["timed_out"] = True
            raise WorkflowTimeoutError(
                f"Step {step_name} timed out",
                timeout_seconds=actual_timeout,
                completed_stages=[s["name"] for s in self.steps if s["completed"]],
            )
        finally:
            step_info["elapsed"] = (datetime.now() - step_start).total_seconds()
            self.steps.append(step_info)
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of all steps."""
        return {
            "name": self.name,
            "total_seconds": self.total_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "remaining_seconds": self.remaining_seconds,
            "steps": self.steps,
        }


@dataclass
class StepContext:
    """Context for a budget step."""
    name: str
    timeout_seconds: float
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def elapsed(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def remaining(self) -> float:
        return max(0, self.timeout_seconds - self.elapsed)
