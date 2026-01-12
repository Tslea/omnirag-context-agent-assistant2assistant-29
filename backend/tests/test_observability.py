"""
Tests for Observability Module

Tests correlation IDs, structured logging, and metrics collection.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import patch

from backend.observability import (
    # Correlation
    CorrelationContext,
    correlation_scope,
    async_correlation_scope,
    # Logging
    LogContext,
    StructuredLogger,
    get_logger,
    # Metrics
    MetricsCollector,
    TimingMetric,
    metrics,
    # Tracing
    AgentSpan,
    RequestTrace,
    timed_operation,
    timed_operation_sync,
    traced,
    traced_sync,
)


class TestCorrelationContext:
    """Tests for correlation ID management."""
    
    def setup_method(self):
        """Clear context before each test."""
        CorrelationContext.clear()
    
    def test_generate_id(self):
        """Should generate unique IDs."""
        id1 = CorrelationContext.generate()
        id2 = CorrelationContext.generate()
        
        assert id1.startswith("req-")
        assert id2.startswith("req-")
        assert id1 != id2
    
    def test_get_set(self):
        """Should get/set correlation ID."""
        assert CorrelationContext.get() is None
        
        CorrelationContext.set("test-123")
        assert CorrelationContext.get() == "test-123"
    
    def test_push_pop(self):
        """Should push/pop IDs on stack."""
        CorrelationContext.set("outer")
        CorrelationContext.push("inner")
        
        assert CorrelationContext.get() == "inner"
        
        CorrelationContext.pop()
        assert CorrelationContext.get() == "outer"
    
    def test_correlation_scope(self):
        """Should scope correlation ID."""
        assert CorrelationContext.get() is None
        
        with correlation_scope("scoped-123") as cid:
            assert cid == "scoped-123"
            assert CorrelationContext.get() == "scoped-123"
        
        assert CorrelationContext.get() is None
    
    @pytest.mark.asyncio
    async def test_async_correlation_scope(self):
        """Should scope correlation ID in async context."""
        async with async_correlation_scope("async-456") as cid:
            assert cid == "async-456"
            assert CorrelationContext.get() == "async-456"
        
        assert CorrelationContext.get() is None


class TestLogContext:
    """Tests for LogContext."""
    
    def test_default_values(self):
        """Should have sensible defaults."""
        ctx = LogContext()
        assert ctx.correlation_id is None
        assert ctx.agent_id is None
        assert ctx.extra == {}
    
    def test_to_dict(self):
        """Should convert to dict."""
        ctx = LogContext(
            correlation_id="test-123",
            agent_id="security",
            operation="validate",
        )
        d = ctx.to_dict()
        
        assert d["correlation_id"] == "test-123"
        assert d["agent_id"] == "security"
        assert d["operation"] == "validate"
        assert "timestamp" in d
    
    def test_to_dict_excludes_none(self):
        """Should exclude None values."""
        ctx = LogContext(agent_id="security")
        d = ctx.to_dict()
        
        assert "workspace" not in d  # Was None
        assert "agent_id" in d


class TestStructuredLogger:
    """Tests for StructuredLogger."""
    
    def test_with_context(self):
        """Should create logger with added context."""
        log = get_logger("test")
        log2 = log.with_context(agent_id="security", operation="scan")
        
        assert log2._context.agent_id == "security"
        assert log2._context.operation == "scan"
    
    def test_format_message(self):
        """Should format message with context."""
        log = get_logger("test", correlation_id="req-123", agent_id="security")
        msg = log._format_message("Hello", extra_field="value")
        
        assert "[req-123]" in msg
        assert "[security]" in msg
        assert "Hello" in msg
        assert "extra_field=value" in msg


class TestMetricsCollector:
    """Tests for MetricsCollector."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        metrics.reset()
    
    @pytest.mark.asyncio
    async def test_record_timing(self):
        """Should record timing metrics."""
        await metrics.record_timing("test_op", 100.5, agent_id="test")
        
        stats = metrics.get_timing_stats()
        assert stats["count"] == 1
        assert stats["avg_ms"] == 100.5
    
    @pytest.mark.asyncio
    async def test_increment_counter(self):
        """Should increment counters."""
        await metrics.increment_counter("test.counter")
        await metrics.increment_counter("test.counter")
        await metrics.increment_counter("test.counter", value=5)
        
        assert metrics.get_counter("test.counter") == 7
    
    @pytest.mark.asyncio
    async def test_set_gauge(self):
        """Should set gauge values."""
        await metrics.set_gauge("test.gauge", 42.5)
        assert metrics.get_gauge("test.gauge") == 42.5
    
    @pytest.mark.asyncio
    async def test_timing_stats(self):
        """Should calculate timing statistics."""
        for i in range(10):
            await metrics.record_timing("op", float(i * 10))
        
        stats = metrics.get_timing_stats()
        assert stats["count"] == 10
        assert stats["min_ms"] == 0
        assert stats["max_ms"] == 90
        assert stats["avg_ms"] == 45.0  # (0+10+...+90)/10
    
    @pytest.mark.asyncio
    async def test_timing_stats_filter_by_operation(self):
        """Should filter stats by operation."""
        await metrics.record_timing("op1", 100)
        await metrics.record_timing("op2", 200)
        await metrics.record_timing("op1", 150)
        
        stats = metrics.get_timing_stats(operation="op1")
        assert stats["count"] == 2
        assert stats["avg_ms"] == 125.0
    
    def test_get_all_metrics(self):
        """Should get all metrics."""
        metrics.increment_counter_sync("c1")
        metrics.record_timing_sync("op", 50)
        
        all_metrics = metrics.get_all_metrics()
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "timing_stats" in all_metrics


class TestTimedOperation:
    """Tests for timed_operation context managers."""
    
    def setup_method(self):
        metrics.reset()
    
    @pytest.mark.asyncio
    async def test_timed_operation_success(self):
        """Should record successful operation."""
        async with timed_operation("test_op", agent_id="test", log=False):
            await asyncio.sleep(0.01)
        
        stats = metrics.get_timing_stats(operation="test_op")
        assert stats["count"] == 1
        assert stats["success_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_timed_operation_failure(self):
        """Should record failed operation."""
        with pytest.raises(ValueError):
            async with timed_operation("failing_op", log=False):
                raise ValueError("oops")
        
        stats = metrics.get_timing_stats(operation="failing_op")
        assert stats["count"] == 1
        assert stats["success_rate"] == 0.0
    
    def test_timed_operation_sync(self):
        """Should work synchronously."""
        with timed_operation_sync("sync_op", log=False):
            pass
        
        stats = metrics.get_timing_stats(operation="sync_op")
        assert stats["count"] == 1


class TestTracedDecorator:
    """Tests for traced decorator."""
    
    def setup_method(self):
        metrics.reset()
    
    @pytest.mark.asyncio
    async def test_traced_async(self):
        """Should trace async function."""
        @traced(operation="decorated_op")
        async def my_func():
            return "result"
        
        result = await my_func()
        
        assert result == "result"
        stats = metrics.get_timing_stats(operation="decorated_op")
        assert stats["count"] == 1
    
    def test_traced_sync(self):
        """Should trace sync function."""
        @traced_sync(operation="sync_decorated")
        def my_func():
            return 42
        
        result = my_func()
        
        assert result == 42
        stats = metrics.get_timing_stats(operation="sync_decorated")
        assert stats["count"] == 1


class TestAgentSpan:
    """Tests for AgentSpan."""
    
    def test_create_span(self):
        """Should create span with defaults."""
        span = AgentSpan(
            agent_id="security",
            operation="validate",
            correlation_id="req-123",
            start_time=datetime.utcnow(),
        )
        
        assert span.status == "in_progress"
        assert span.end_time is None
    
    def test_complete_span(self):
        """Should complete span."""
        span = AgentSpan(
            agent_id="security",
            operation="validate",
            correlation_id="req-123",
            start_time=datetime.utcnow(),
        )
        
        span.complete("success")
        
        assert span.status == "success"
        assert span.end_time is not None
    
    def test_duration(self):
        """Should calculate duration."""
        span = AgentSpan(
            agent_id="security",
            operation="validate",
            correlation_id="req-123",
            start_time=datetime.utcnow(),
        )
        
        # Duration should be >= 0
        assert span.duration_ms >= 0
    
    def test_to_dict(self):
        """Should convert to dict."""
        span = AgentSpan(
            agent_id="security",
            operation="validate",
            correlation_id="req-123",
            start_time=datetime.utcnow(),
        )
        d = span.to_dict()
        
        assert d["agent_id"] == "security"
        assert d["operation"] == "validate"
        assert d["correlation_id"] == "req-123"


class TestRequestTrace:
    """Tests for RequestTrace."""
    
    def setup_method(self):
        metrics.reset()
        CorrelationContext.clear()
    
    @pytest.mark.asyncio
    async def test_create_trace(self):
        """Should create trace with correlation ID."""
        trace = RequestTrace()
        assert trace.correlation_id.startswith("req-")
    
    @pytest.mark.asyncio
    async def test_span_records_timing(self):
        """Should record timing for spans."""
        trace = RequestTrace(correlation_id="test-trace")
        
        async with trace.span("security", "validate"):
            await asyncio.sleep(0.01)
        
        assert len(trace.spans) == 1
        assert trace.spans[0].agent_id == "security"
        assert trace.spans[0].status == "success"
    
    @pytest.mark.asyncio
    async def test_span_error_handling(self):
        """Should handle errors in spans."""
        trace = RequestTrace()
        
        with pytest.raises(ValueError):
            async with trace.span("security", "validate"):
                raise ValueError("test error")
        
        assert trace.spans[0].status == "error"
        assert "test error" in trace.spans[0].error
    
    @pytest.mark.asyncio
    async def test_nested_spans(self):
        """Should handle nested spans."""
        trace = RequestTrace()
        
        async with trace.span("workflow", "analyze"):
            async with trace.span("context", "extract"):
                await asyncio.sleep(0.001)
            async with trace.span("security", "scan"):
                await asyncio.sleep(0.001)
        
        # Top-level span should have children
        assert len(trace.spans) == 1
        assert len(trace.spans[0].children) == 2
    
    @pytest.mark.asyncio
    async def test_trace_summary(self):
        """Should get trace summary."""
        trace = RequestTrace(correlation_id="summary-test")
        
        async with trace.span("agent1", "op1"):
            await asyncio.sleep(0.001)
        
        summary = trace.get_summary()
        
        assert summary["correlation_id"] == "summary-test"
        assert summary["span_count"] == 1
        assert "total_duration_ms" in summary
