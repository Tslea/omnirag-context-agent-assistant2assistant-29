"""
Tests for OMNI Exception Hierarchy

Tests the custom exception classes and helper functions.
"""

import pytest
from datetime import datetime

from backend.core.exceptions import (
    # Base
    OMNIError,
    ErrorContext,
    # Agent errors
    AgentError,
    AgentTimeoutError,
    AgentValidationError,
    AgentConfigurationError,
    AgentNotFoundError,
    AgentFatalError,
    AgentDependencyError,
    # LLM errors
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMResponseError,
    # VectorDB errors
    VectorDBError,
    VectorDBConnectionError,
    VectorDBQueryError,
    VectorDBIndexError,
    # RAG errors
    RAGError,
    RAGIndexError,
    RAGQueryError,
    # Workflow errors
    WorkflowError,
    WorkflowTimeoutError,
    WorkflowValidationError,
    WorkflowStageError,
    # Helpers
    is_recoverable,
    wrap_exception,
)


class TestErrorContext:
    """Tests for ErrorContext dataclass."""
    
    def test_default_values(self):
        """Should have sensible defaults."""
        ctx = ErrorContext()
        assert ctx.agent_id is None
        assert ctx.operation is None
        assert ctx.correlation_id is None
        assert isinstance(ctx.timestamp, datetime)
        assert ctx.metadata == {}
    
    def test_with_values(self):
        """Should store provided values."""
        ctx = ErrorContext(
            agent_id="test_agent",
            operation="process",
            correlation_id="req-123",
            metadata={"key": "value"},
        )
        assert ctx.agent_id == "test_agent"
        assert ctx.operation == "process"
        assert ctx.correlation_id == "req-123"
        assert ctx.metadata == {"key": "value"}
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        ctx = ErrorContext(
            agent_id="test_agent",
            operation="process",
        )
        d = ctx.to_dict()
        assert d["agent_id"] == "test_agent"
        assert d["operation"] == "process"
        assert "timestamp" in d


class TestOMNIError:
    """Tests for base OMNIError class."""
    
    def test_basic_error(self):
        """Should create basic error."""
        err = OMNIError("Something went wrong")
        assert str(err) == "Something went wrong"
        assert err.message == "Something went wrong"
        assert err.recoverable is False
        assert err.cause is None
    
    def test_with_context(self):
        """Should include context in string."""
        ctx = ErrorContext(agent_id="test_agent", operation="process")
        err = OMNIError("Error", context=ctx)
        assert "[agent=test_agent]" in str(err)
        assert "[op=process]" in str(err)
    
    def test_recoverable_flag(self):
        """Should respect recoverable flag."""
        err = OMNIError("Retry me", recoverable=True)
        assert err.recoverable is True
    
    def test_with_cause(self):
        """Should store original cause."""
        original = ValueError("Original error")
        err = OMNIError("Wrapped error", cause=original)
        assert err.cause is original
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        err = OMNIError("Error", recoverable=True)
        d = err.to_dict()
        assert d["error_type"] == "OMNIError"
        assert d["message"] == "Error"
        assert d["recoverable"] is True


class TestAgentErrors:
    """Tests for agent-related exceptions."""
    
    def test_agent_error_hierarchy(self):
        """Agent errors should inherit from OMNIError."""
        assert issubclass(AgentError, OMNIError)
        assert issubclass(AgentTimeoutError, AgentError)
        assert issubclass(AgentValidationError, AgentError)
        assert issubclass(AgentConfigurationError, AgentError)
        assert issubclass(AgentNotFoundError, AgentError)
        assert issubclass(AgentFatalError, AgentError)
        assert issubclass(AgentDependencyError, AgentError)
    
    def test_timeout_error_is_recoverable(self):
        """Timeout errors should be recoverable."""
        err = AgentTimeoutError("Timed out", timeout_seconds=30)
        assert err.recoverable is True
        assert err.timeout_seconds == 30
    
    def test_validation_error_is_not_recoverable(self):
        """Validation errors should not be recoverable."""
        err = AgentValidationError("Invalid input", field="content", value=None)
        assert err.recoverable is False
        assert err.field == "content"
        assert err.value is None
    
    def test_configuration_error(self):
        """Should store config key."""
        err = AgentConfigurationError("Missing key", config_key="api_key")
        assert err.config_key == "api_key"
        assert err.recoverable is False
    
    def test_not_found_error(self):
        """Should format agent ID in message."""
        err = AgentNotFoundError("unknown_agent")
        assert "unknown_agent" in str(err)
        assert err.agent_id == "unknown_agent"
    
    def test_fatal_error(self):
        """Fatal errors should not be recoverable."""
        err = AgentFatalError("Critical failure")
        assert err.recoverable is False
    
    def test_dependency_error(self):
        """Should store agent and dependency."""
        err = AgentDependencyError(
            agent_id="security_agent",
            dependency="context_agent",
        )
        assert err.agent_id == "security_agent"
        assert err.dependency == "context_agent"
        assert "security_agent" in str(err)
        assert "context_agent" in str(err)


class TestLLMErrors:
    """Tests for LLM-related exceptions."""
    
    def test_llm_error_hierarchy(self):
        """LLM errors should inherit from OMNIError."""
        assert issubclass(LLMError, OMNIError)
        assert issubclass(LLMTimeoutError, LLMError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMAuthenticationError, LLMError)
        assert issubclass(LLMResponseError, LLMError)
    
    def test_timeout_is_recoverable(self):
        """LLM timeout should be recoverable."""
        err = LLMTimeoutError("Timeout", timeout_seconds=60)
        assert err.recoverable is True
    
    def test_rate_limit_is_recoverable(self):
        """Rate limit should be recoverable."""
        err = LLMRateLimitError("Rate limited", retry_after_seconds=30)
        assert err.recoverable is True
        assert err.retry_after_seconds == 30
    
    def test_auth_error_not_recoverable(self):
        """Auth errors should not be recoverable."""
        err = LLMAuthenticationError("Invalid API key", provider="openai")
        assert err.recoverable is False
        assert err.provider == "openai"


class TestVectorDBErrors:
    """Tests for VectorDB-related exceptions."""
    
    def test_vectordb_error_hierarchy(self):
        """VectorDB errors should inherit from OMNIError."""
        assert issubclass(VectorDBError, OMNIError)
        assert issubclass(VectorDBConnectionError, VectorDBError)
        assert issubclass(VectorDBQueryError, VectorDBError)
        assert issubclass(VectorDBIndexError, VectorDBError)
    
    def test_connection_error_is_recoverable(self):
        """Connection errors should be recoverable."""
        err = VectorDBConnectionError("Connection failed", provider="chroma")
        assert err.recoverable is True
        assert err.provider == "chroma"
    
    def test_query_error_stores_query(self):
        """Query errors should store the query."""
        err = VectorDBQueryError("Query failed", query="search term")
        assert err.query == "search term"


class TestWorkflowErrors:
    """Tests for workflow-related exceptions."""
    
    def test_workflow_error_hierarchy(self):
        """Workflow errors should inherit from OMNIError."""
        assert issubclass(WorkflowError, OMNIError)
        assert issubclass(WorkflowTimeoutError, WorkflowError)
        assert issubclass(WorkflowValidationError, WorkflowError)
        assert issubclass(WorkflowStageError, WorkflowError)
    
    def test_timeout_stores_completed_stages(self):
        """Timeout should store completed stages."""
        err = WorkflowTimeoutError(
            "Workflow timed out",
            timeout_seconds=300,
            completed_stages=["context", "rag"],
        )
        assert err.completed_stages == ["context", "rag"]
        assert err.recoverable is True
    
    def test_stage_error_stores_stage(self):
        """Stage error should store stage name."""
        err = WorkflowStageError("Stage failed", stage="security")
        assert err.stage == "security"


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_is_recoverable_with_omni_error(self):
        """Should check recoverable flag on OMNI errors."""
        recoverable = AgentTimeoutError("Timeout")
        not_recoverable = AgentValidationError("Invalid")
        
        assert is_recoverable(recoverable) is True
        assert is_recoverable(not_recoverable) is False
    
    def test_is_recoverable_with_standard_errors(self):
        """Should handle standard exceptions."""
        assert is_recoverable(TimeoutError()) is True
        assert is_recoverable(ConnectionError()) is True
        assert is_recoverable(ValueError()) is False
        assert is_recoverable(KeyError()) is False
    
    def test_wrap_exception(self):
        """Should wrap standard exception in OMNI error."""
        original = ValueError("Original")
        wrapped = wrap_exception(
            original,
            "Wrapped error",
            error_class=AgentError,
        )
        
        assert isinstance(wrapped, AgentError)
        assert wrapped.cause is original
        assert "Wrapped error" in str(wrapped)
    
    def test_wrap_exception_with_context(self):
        """Should include context in wrapped error."""
        original = ValueError("Original")
        ctx = ErrorContext(agent_id="test")
        wrapped = wrap_exception(
            original,
            "Wrapped",
            error_class=AgentError,
            context=ctx,
        )
        
        assert wrapped.context.agent_id == "test"


class TestExceptionCatching:
    """Tests for catching exceptions at different levels."""
    
    def test_catch_specific_agent_error(self):
        """Should catch specific agent errors."""
        with pytest.raises(AgentTimeoutError):
            raise AgentTimeoutError("Timeout")
    
    def test_catch_agent_error_base(self):
        """Should catch any agent error with base class."""
        with pytest.raises(AgentError):
            raise AgentTimeoutError("Timeout")
        
        with pytest.raises(AgentError):
            raise AgentValidationError("Invalid")
    
    def test_catch_omni_error_base(self):
        """Should catch any OMNI error with base class."""
        with pytest.raises(OMNIError):
            raise AgentTimeoutError("Timeout")
        
        with pytest.raises(OMNIError):
            raise LLMRateLimitError("Rate limited")
        
        with pytest.raises(OMNIError):
            raise VectorDBConnectionError("Connection failed")
