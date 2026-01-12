"""
Observability Module

Provides distributed tracing, structured logging, and metrics collection.

Key features:
- Correlation IDs for request tracing across agents
- Structured logging with context
- Timing metrics for performance monitoring
- Integration hooks for external monitoring
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

# Use standard logging with structured formatting
# (structlog can be added as optional dependency)
logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Correlation ID Management
# ============================================================================

class CorrelationContext:
    """
    Thread-local storage for correlation IDs.
    
    Allows tracing a request across all agent calls.
    """
    _current: Optional[str] = None
    _stack: List[str] = []
    
    @classmethod
    def get(cls) -> Optional[str]:
        """Get current correlation ID."""
        return cls._current
    
    @classmethod
    def set(cls, correlation_id: str) -> None:
        """Set correlation ID for current context."""
        cls._current = correlation_id
    
    @classmethod
    def generate(cls) -> str:
        """Generate a new correlation ID."""
        return f"req-{uuid.uuid4().hex[:12]}"
    
    @classmethod
    def push(cls, correlation_id: Optional[str] = None) -> str:
        """Push a new correlation ID onto the stack."""
        if cls._current:
            cls._stack.append(cls._current)
        new_id = correlation_id or cls.generate()
        cls._current = new_id
        return new_id
    
    @classmethod
    def pop(cls) -> Optional[str]:
        """Pop correlation ID from stack."""
        old = cls._current
        cls._current = cls._stack.pop() if cls._stack else None
        return old
    
    @classmethod
    def clear(cls) -> None:
        """Clear all correlation context."""
        cls._current = None
        cls._stack.clear()


@contextmanager
def correlation_scope(correlation_id: Optional[str] = None):
    """
    Context manager for correlation ID scope.
    
    Usage:
        with correlation_scope() as cid:
            # All logs/traces in this scope will have cid
            await process_request(...)
    """
    cid = CorrelationContext.push(correlation_id)
    try:
        yield cid
    finally:
        CorrelationContext.pop()


@asynccontextmanager
async def async_correlation_scope(correlation_id: Optional[str] = None):
    """Async version of correlation_scope."""
    cid = CorrelationContext.push(correlation_id)
    try:
        yield cid
    finally:
        CorrelationContext.pop()


# ============================================================================
# Structured Logging
# ============================================================================

@dataclass
class LogContext:
    """Context attached to log entries."""
    correlation_id: Optional[str] = None
    agent_id: Optional[str] = None
    operation: Optional[str] = None
    workspace: Optional[str] = None
    user_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "correlation_id": self.correlation_id or CorrelationContext.get(),
            "agent_id": self.agent_id,
            "operation": self.operation,
            "workspace": self.workspace,
            "user_id": self.user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        d.update(self.extra)
        return {k: v for k, v in d.items() if v is not None}


class StructuredLogger:
    """
    Logger with structured context and correlation IDs.
    
    Usage:
        log = StructuredLogger("agent.security")
        log.info("Scanning file", file_path="/app/main.py", issues=3)
    """
    
    def __init__(self, name: str, context: Optional[LogContext] = None):
        self._logger = logging.getLogger(name)
        self._context = context or LogContext()
    
    def with_context(self, **kwargs) -> "StructuredLogger":
        """Create logger with additional context."""
        new_context = LogContext(
            correlation_id=kwargs.get("correlation_id", self._context.correlation_id),
            agent_id=kwargs.get("agent_id", self._context.agent_id),
            operation=kwargs.get("operation", self._context.operation),
            workspace=kwargs.get("workspace", self._context.workspace),
            user_id=kwargs.get("user_id", self._context.user_id),
            extra={**self._context.extra, **{k: v for k, v in kwargs.items() 
                   if k not in ("correlation_id", "agent_id", "operation", "workspace", "user_id")}},
        )
        return StructuredLogger(self._logger.name, new_context)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context."""
        ctx = self._context.to_dict()
        ctx.update(kwargs)
        
        # Build context string
        parts = []
        if ctx.get("correlation_id"):
            parts.append(f"[{ctx['correlation_id']}]")
        if ctx.get("agent_id"):
            parts.append(f"[{ctx['agent_id']}]")
        
        prefix = " ".join(parts) + " " if parts else ""
        
        # Add extra fields
        extras = {k: v for k, v in kwargs.items() if v is not None}
        extra_str = " | ".join(f"{k}={v}" for k, v in extras.items()) if extras else ""
        
        if extra_str:
            return f"{prefix}{message} | {extra_str}"
        return f"{prefix}{message}"
    
    def debug(self, message: str, **kwargs) -> None:
        self._logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs) -> None:
        self._logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs) -> None:
        self._logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs) -> None:
        self._logger.error(self._format_message(message, **kwargs))
    
    def exception(self, message: str, **kwargs) -> None:
        self._logger.exception(self._format_message(message, **kwargs))


def get_logger(name: str, **context) -> StructuredLogger:
    """Get a structured logger with optional context."""
    return StructuredLogger(name, LogContext(**context))


# ============================================================================
# Timing and Metrics
# ============================================================================

@dataclass
class TimingMetric:
    """A single timing measurement."""
    operation: str
    duration_ms: float
    agent_id: Optional[str] = None
    correlation_id: Optional[str] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """
    Collects and aggregates metrics.
    
    Thread-safe collector for timing and counter metrics.
    """
    
    _instance: Optional["MetricsCollector"] = None
    
    def __init__(self):
        self._timings: List[TimingMetric] = []
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._max_timings = 10000  # Keep last N timings
    
    @classmethod
    def get_instance(cls) -> "MetricsCollector":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = MetricsCollector()
        return cls._instance
    
    async def record_timing(
        self,
        operation: str,
        duration_ms: float,
        agent_id: Optional[str] = None,
        success: bool = True,
        **metadata,
    ) -> None:
        """Record a timing metric."""
        metric = TimingMetric(
            operation=operation,
            duration_ms=duration_ms,
            agent_id=agent_id,
            correlation_id=CorrelationContext.get(),
            success=success,
            metadata=metadata,
        )
        
        async with self._lock:
            self._timings.append(metric)
            # Trim old entries
            if len(self._timings) > self._max_timings:
                self._timings = self._timings[-self._max_timings:]
    
    def record_timing_sync(
        self,
        operation: str,
        duration_ms: float,
        agent_id: Optional[str] = None,
        success: bool = True,
        **metadata,
    ) -> None:
        """Synchronous version for non-async contexts."""
        metric = TimingMetric(
            operation=operation,
            duration_ms=duration_ms,
            agent_id=agent_id,
            correlation_id=CorrelationContext.get(),
            success=success,
            metadata=metadata,
        )
        self._timings.append(metric)
    
    async def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        async with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value
    
    def increment_counter_sync(self, name: str, value: int = 1) -> None:
        """Synchronous counter increment."""
        self._counters[name] = self._counters.get(name, 0) + value
    
    async def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        async with self._lock:
            self._gauges[name] = value
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self._counters.get(name, 0)
    
    def get_gauge(self, name: str) -> float:
        """Get gauge value."""
        return self._gauges.get(name, 0.0)
    
    def get_timing_stats(
        self,
        operation: Optional[str] = None,
        agent_id: Optional[str] = None,
        last_n: int = 100,
    ) -> Dict[str, Any]:
        """Get timing statistics."""
        # Filter timings
        filtered = self._timings[-last_n:]
        if operation:
            filtered = [t for t in filtered if t.operation == operation]
        if agent_id:
            filtered = [t for t in filtered if t.agent_id == agent_id]
        
        if not filtered:
            return {"count": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0, "p95_ms": 0}
        
        durations = [t.duration_ms for t in filtered]
        sorted_durations = sorted(durations)
        
        return {
            "count": len(durations),
            "avg_ms": sum(durations) / len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "p95_ms": sorted_durations[int(len(sorted_durations) * 0.95)] if len(sorted_durations) > 1 else sorted_durations[0],
            "success_rate": sum(1 for t in filtered if t.success) / len(filtered),
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timing_stats": self.get_timing_stats(),
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._timings.clear()
        self._counters.clear()
        self._gauges.clear()


# Global metrics collector
metrics = MetricsCollector.get_instance()


# ============================================================================
# Decorators and Context Managers
# ============================================================================

@asynccontextmanager
async def timed_operation(
    operation: str,
    agent_id: Optional[str] = None,
    log: bool = True,
    **metadata,
):
    """
    Context manager for timing async operations.
    
    Usage:
        async with timed_operation("process_message", agent_id="security"):
            result = await agent.process(message)
    """
    start_time = time.perf_counter()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        await metrics.record_timing(
            operation=operation,
            duration_ms=duration_ms,
            agent_id=agent_id,
            success=success,
            **metadata,
        )
        
        if log:
            log_msg = f"Operation {operation} completed in {duration_ms:.2f}ms"
            if agent_id:
                log_msg = f"[{agent_id}] {log_msg}"
            if success:
                logger.debug(log_msg)
            else:
                logger.warning(f"{log_msg} (failed)")


@contextmanager
def timed_operation_sync(
    operation: str,
    agent_id: Optional[str] = None,
    log: bool = True,
    **metadata,
):
    """Synchronous version of timed_operation."""
    start_time = time.perf_counter()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics.record_timing_sync(
            operation=operation,
            duration_ms=duration_ms,
            agent_id=agent_id,
            success=success,
            **metadata,
        )
        
        if log:
            log_msg = f"Operation {operation} completed in {duration_ms:.2f}ms"
            if agent_id:
                log_msg = f"[{agent_id}] {log_msg}"
            if success:
                logger.debug(log_msg)
            else:
                logger.warning(f"{log_msg} (failed)")


def traced(
    operation: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """
    Decorator for tracing async functions.
    
    Usage:
        @traced(operation="validate_code", agent_id="security")
        async def validate(code: str) -> bool:
            ...
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            async with timed_operation(op_name, agent_id=agent_id):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def traced_sync(
    operation: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Synchronous version of traced decorator."""
    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with timed_operation_sync(op_name, agent_id=agent_id):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Agent Instrumentation
# ============================================================================

@dataclass
class AgentSpan:
    """
    Represents a traced span for agent execution.
    
    Use this to wrap agent.process() calls for full observability.
    """
    agent_id: str
    operation: str
    correlation_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "in_progress"  # in_progress, success, error
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["AgentSpan"] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (datetime.utcnow() - self.start_time).total_seconds() * 1000
        return (self.end_time - self.start_time).total_seconds() * 1000
    
    def complete(self, status: str = "success", error: Optional[str] = None) -> None:
        """Mark span as complete."""
        self.end_time = datetime.utcnow()
        self.status = status
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
        }


class RequestTrace:
    """
    Traces an entire request through all agents.
    
    Usage:
        trace = RequestTrace()
        
        async with trace.span("context_agent", "analyze_project"):
            await context_agent.process(...)
        
        async with trace.span("security_agent", "validate_code"):
            await security_agent.process(...)
        
        print(trace.get_summary())
    """
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or CorrelationContext.generate()
        self.start_time = datetime.utcnow()
        self.spans: List[AgentSpan] = []
        self._current_span: Optional[AgentSpan] = None
    
    @asynccontextmanager
    async def span(
        self,
        agent_id: str,
        operation: str,
        **metadata,
    ):
        """Create a traced span for an agent operation."""
        span = AgentSpan(
            agent_id=agent_id,
            operation=operation,
            correlation_id=self.correlation_id,
            start_time=datetime.utcnow(),
            metadata=metadata,
        )
        
        # Add as child if there's a current span
        if self._current_span:
            self._current_span.children.append(span)
        else:
            self.spans.append(span)
        
        old_span = self._current_span
        self._current_span = span
        
        try:
            async with async_correlation_scope(self.correlation_id):
                yield span
            span.complete("success")
        except Exception as e:
            span.complete("error", str(e))
            raise
        finally:
            self._current_span = old_span
            
            # Record to metrics
            await metrics.record_timing(
                operation=f"{agent_id}.{operation}",
                duration_ms=span.duration_ms,
                agent_id=agent_id,
                success=(span.status == "success"),
            )
    
    @property
    def total_duration_ms(self) -> float:
        """Total trace duration."""
        return (datetime.utcnow() - self.start_time).total_seconds() * 1000
    
    def get_summary(self) -> Dict[str, Any]:
        """Get trace summary."""
        return {
            "correlation_id": self.correlation_id,
            "start_time": self.start_time.isoformat(),
            "total_duration_ms": self.total_duration_ms,
            "span_count": len(self.spans),
            "spans": [s.to_dict() for s in self.spans],
        }


# ============================================================================
# Metrics Definitions (for reference)
# ============================================================================

# Standard metric names used across OMNI
METRIC_NAMES = {
    # Agent metrics
    "agent_process_duration": "agent.process.duration_ms",
    "agent_errors": "agent.errors.count",
    "agent_success": "agent.success.count",
    
    # RAG metrics
    "rag_query_duration": "rag.query.duration_ms",
    "rag_cache_hits": "rag.cache.hits",
    "rag_cache_misses": "rag.cache.misses",
    "rag_indexed_files": "rag.indexed.files",
    
    # Security metrics
    "security_scan_duration": "security.scan.duration_ms",
    "security_findings_count": "security.findings.count",
    "security_findings_by_severity": "security.findings.by_severity",
    
    # Compliance metrics
    "compliance_check_duration": "compliance.check.duration_ms",
    "compliance_findings_count": "compliance.findings.count",
    
    # Workflow metrics
    "workflow_duration": "workflow.duration_ms",
    "workflow_success": "workflow.success.count",
    "workflow_failures": "workflow.failures.count",
    
    # WebSocket metrics
    "ws_messages_received": "websocket.messages.received",
    "ws_messages_sent": "websocket.messages.sent",
    "ws_connections_active": "websocket.connections.active",
}


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> None:
    """
    Setup logging configuration for OMNI.
    
    Call this at application startup.
    """
    fmt = format_string or "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Reduce noise from libraries
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
