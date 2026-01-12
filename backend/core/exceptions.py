"""
OMNI Exception Hierarchy

Provides typed exceptions for better error handling and debugging.
All OMNI-specific exceptions inherit from OMNIError.

Exception Hierarchy:
    OMNIError (base)
    ├── AgentError (agent-related errors)
    │   ├── AgentTimeoutError (operation timed out)
    │   ├── AgentValidationError (input validation failed)
    │   ├── AgentConfigurationError (misconfiguration)
    │   ├── AgentNotFoundError (agent not registered)
    │   └── AgentFatalError (unrecoverable error)
    ├── LLMError (LLM provider errors)
    │   ├── LLMTimeoutError (LLM call timed out)
    │   ├── LLMRateLimitError (rate limit hit)
    │   ├── LLMAuthenticationError (auth failed)
    │   └── LLMResponseError (invalid response)
    ├── VectorDBError (vector database errors)
    │   ├── VectorDBConnectionError (connection failed)
    │   ├── VectorDBQueryError (query failed)
    │   └── VectorDBIndexError (indexing failed)
    ├── RAGError (RAG service errors)
    │   ├── RAGIndexError (indexing failed)
    │   └── RAGQueryError (query failed)
    └── WorkflowError (workflow errors)
        ├── WorkflowTimeoutError (workflow timed out)
        └── WorkflowValidationError (validation failed)

Usage:
    from backend.core.exceptions import AgentTimeoutError, AgentValidationError
    
    try:
        await agent.process(message, context)
    except AgentTimeoutError as e:
        # Handle timeout - maybe retry
        logger.warning(f"Agent timed out: {e}")
    except AgentValidationError as e:
        # Handle validation - return error to user
        logger.error(f"Validation failed: {e}")
    except AgentFatalError as e:
        # Handle fatal - stop agent
        logger.critical(f"Fatal error: {e}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ============================================================================
# Base Exception
# ============================================================================

@dataclass
class ErrorContext:
    """
    Additional context for debugging errors.
    
    Attributes:
        agent_id: ID of the agent that raised the error
        operation: What operation was being performed
        correlation_id: Request correlation ID for tracing
        timestamp: When the error occurred
        metadata: Additional debugging information
    """
    agent_id: Optional[str] = None
    operation: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "agent_id": self.agent_id,
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class OMNIError(Exception):
    """
    Base exception for all OMNI errors.
    
    All custom exceptions inherit from this class, allowing:
    - Catching all OMNI errors with `except OMNIError`
    - Adding context for debugging
    - Determining if error is recoverable
    
    Attributes:
        message: Human-readable error message
        context: Additional debugging context
        recoverable: Whether the operation can be retried
        cause: Original exception that caused this error
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext()
        self.recoverable = recoverable
        self.cause = cause
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.context.agent_id:
            parts.append(f"[agent={self.context.agent_id}]")
        if self.context.operation:
            parts.append(f"[op={self.context.operation}]")
        if self.context.correlation_id:
            parts.append(f"[corr={self.context.correlation_id}]")
        return " ".join(parts)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "recoverable": self.recoverable,
            "context": self.context.to_dict(),
            "cause": str(self.cause) if self.cause else None,
        }


# ============================================================================
# Agent Errors
# ============================================================================

class AgentError(OMNIError):
    """Base class for agent-related errors."""
    pass


class AgentTimeoutError(AgentError):
    """
    Raised when an agent operation times out.
    
    This is a RECOVERABLE error - the operation can be retried.
    
    Example:
        try:
            async with asyncio.timeout(30):
                result = await agent.process(message, context)
        except asyncio.TimeoutError:
            raise AgentTimeoutError(
                "Agent processing timed out after 30s",
                context=ErrorContext(agent_id=agent.metadata.id, operation="process"),
                recoverable=True,
            )
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.timeout_seconds = timeout_seconds


class AgentValidationError(AgentError):
    """
    Raised when input validation fails.
    
    This is NOT recoverable without fixing the input.
    
    Example:
        if not message.content:
            raise AgentValidationError(
                "Message content cannot be empty",
                field="content",
                value=message.content,
            )
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=False, cause=cause)
        self.field = field
        self.value = value


class AgentConfigurationError(AgentError):
    """
    Raised when agent configuration is invalid.
    
    This is NOT recoverable without fixing configuration.
    
    Example:
        if not config.api_key:
            raise AgentConfigurationError(
                "API key is required",
                config_key="api_key",
            )
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=False, cause=cause)
        self.config_key = config_key


class AgentNotFoundError(AgentError):
    """
    Raised when a requested agent is not registered.
    
    Example:
        agent = registry.get("unknown_agent")
        if not agent:
            raise AgentNotFoundError("unknown_agent")
    """
    
    def __init__(
        self,
        agent_id: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            f"Agent not found: {agent_id}",
            context,
            recoverable=False,
            cause=cause,
        )
        self.agent_id = agent_id


class AgentFatalError(AgentError):
    """
    Raised when an unrecoverable error occurs.
    
    This indicates the agent should be stopped/restarted.
    
    Example:
        try:
            # Critical operation
        except SomeUnrecoverableError as e:
            raise AgentFatalError(
                "Agent state corrupted",
                context=ErrorContext(agent_id=self.metadata.id),
                cause=e,
            )
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=False, cause=cause)


class AgentDependencyError(AgentError):
    """
    Raised when a required agent dependency is missing.
    
    Example:
        if not self._context_agent:
            raise AgentDependencyError(
                agent_id="security_agent",
                dependency="context_agent",
            )
    """
    
    def __init__(
        self,
        agent_id: str,
        dependency: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            f"Agent '{agent_id}' requires '{dependency}' but it's not available",
            context,
            recoverable=False,
            cause=cause,
        )
        self.agent_id = agent_id
        self.dependency = dependency


# ============================================================================
# LLM Errors
# ============================================================================

class LLMError(OMNIError):
    """Base class for LLM provider errors."""
    pass


class LLMTimeoutError(LLMError):
    """
    Raised when LLM call times out.
    
    This is RECOVERABLE - can retry with backoff.
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.timeout_seconds = timeout_seconds


class LLMRateLimitError(LLMError):
    """
    Raised when LLM rate limit is hit.
    
    This is RECOVERABLE - retry after delay.
    
    Attributes:
        retry_after_seconds: Suggested wait time before retry
    """
    
    def __init__(
        self,
        message: str,
        retry_after_seconds: Optional[float] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.retry_after_seconds = retry_after_seconds


class LLMAuthenticationError(LLMError):
    """
    Raised when LLM authentication fails.
    
    This is NOT recoverable without fixing credentials.
    """
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=False, cause=cause)
        self.provider = provider


class LLMResponseError(LLMError):
    """
    Raised when LLM returns invalid response.
    
    This is RECOVERABLE - can retry.
    """
    
    def __init__(
        self,
        message: str,
        response: Any = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.response = response


# ============================================================================
# VectorDB Errors
# ============================================================================

class VectorDBError(OMNIError):
    """Base class for vector database errors."""
    pass


class VectorDBConnectionError(VectorDBError):
    """
    Raised when VectorDB connection fails.
    
    This is RECOVERABLE - can retry connection.
    """
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.provider = provider


class VectorDBQueryError(VectorDBError):
    """
    Raised when VectorDB query fails.
    
    This is RECOVERABLE - can retry query.
    """
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.query = query


class VectorDBIndexError(VectorDBError):
    """
    Raised when VectorDB indexing fails.
    
    This is RECOVERABLE - can retry indexing.
    """
    
    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.document_id = document_id


# ============================================================================
# RAG Errors
# ============================================================================

class RAGError(OMNIError):
    """Base class for RAG service errors."""
    pass


class RAGIndexError(RAGError):
    """
    Raised when RAG indexing fails.
    """
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        domain: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.file_path = file_path
        self.domain = domain


class RAGQueryError(RAGError):
    """
    Raised when RAG query fails.
    """
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        domain: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.query = query
        self.domain = domain


# ============================================================================
# Workflow Errors
# ============================================================================

class WorkflowError(OMNIError):
    """Base class for workflow errors."""
    pass


class WorkflowTimeoutError(WorkflowError):
    """
    Raised when workflow times out.
    
    This is RECOVERABLE - partial results may be available.
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        completed_stages: Optional[list[str]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.timeout_seconds = timeout_seconds
        self.completed_stages = completed_stages or []


class WorkflowValidationError(WorkflowError):
    """
    Raised when workflow validation fails.
    """
    
    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=False, cause=cause)
        self.stage = stage


class WorkflowStageError(WorkflowError):
    """
    Raised when a workflow stage fails.
    """
    
    def __init__(
        self,
        message: str,
        stage: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, context, recoverable=True, cause=cause)
        self.stage = stage


# ============================================================================
# Helper Functions
# ============================================================================

def is_recoverable(error: Exception) -> bool:
    """
    Check if an error is recoverable.
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error can be retried
    """
    if isinstance(error, OMNIError):
        return error.recoverable
    
    # Standard library exceptions that are recoverable
    recoverable_types = (
        TimeoutError,
        ConnectionError,
        ConnectionResetError,
        ConnectionRefusedError,
    )
    return isinstance(error, recoverable_types)


def wrap_exception(
    error: Exception,
    message: str,
    error_class: type[OMNIError] = OMNIError,
    context: Optional[ErrorContext] = None,
) -> OMNIError:
    """
    Wrap a standard exception in an OMNI exception.
    
    Args:
        error: Original exception
        message: Human-readable message
        error_class: OMNI exception class to use
        context: Additional context
        
    Returns:
        Wrapped OMNI exception
    """
    return error_class(message, context=context, cause=error)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Base
    "OMNIError",
    "ErrorContext",
    
    # Agent errors
    "AgentError",
    "AgentTimeoutError",
    "AgentValidationError",
    "AgentConfigurationError",
    "AgentNotFoundError",
    "AgentFatalError",
    "AgentDependencyError",
    
    # LLM errors
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMResponseError",
    
    # VectorDB errors
    "VectorDBError",
    "VectorDBConnectionError",
    "VectorDBQueryError",
    "VectorDBIndexError",
    
    # RAG errors
    "RAGError",
    "RAGIndexError",
    "RAGQueryError",
    
    # Workflow errors
    "WorkflowError",
    "WorkflowTimeoutError",
    "WorkflowValidationError",
    "WorkflowStageError",
    
    # Helpers
    "is_recoverable",
    "wrap_exception",
]
