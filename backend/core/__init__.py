"""
OMNI Backend Core Package

This package contains the core interfaces, base classes, and abstractions
that define the contract for all adapters and plugins.
"""

from backend.core.interfaces.llm import LLMProvider, LLMResponse, LLMConfig, LLMMessage
from backend.core.interfaces.vectordb import VectorDBProvider, Document, SearchResult
from backend.core.interfaces.agent import AgentBase, AgentContext, AgentMessage
from backend.core.interfaces.workflow import WorkflowBase, WorkflowStep, WorkflowContext

# Exceptions (P0.1: Robust Error Handling)
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

# Retry utilities (P0.1: Robust Error Handling)
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

# Thread-safe state (P0.2: Thread-Safety)
from backend.core.state import (
    StateVersion,
    ThreadSafeState,
    SharedContext,
    ThreadSafeSharedContext,
)

# Timeout management (P0.3: Timeouts)
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

# Dependencies (P1.2: Explicit Agent Dependencies)
from backend.core.dependencies import (
    DependencyGraph,
    DependencyInfo,
    DependencyStatus,
    DependencyError,
    MissingDependencyError,
    CircularDependencyError,
    DependencyValidationError,
    validate_dependencies,
    get_initialization_order,
)

# Connection pooling (P1.3: Resource Pooling)
from backend.core.connection_pool import (
    ConnectionPool,
    ConnectionFactory,
    ConnectionState,
    PoolConfig,
    PoolStats,
    PooledConnection,
    PoolError,
    PoolExhaustedError,
    PoolClosedError,
    SimpleConnectionFactory,
    create_pool,
)

__all__ = [
    # LLM
    "LLMProvider",
    "LLMResponse", 
    "LLMConfig",
    "LLMMessage",
    # Vector DB
    "VectorDBProvider",
    "Document",
    "SearchResult",
    # Agent
    "AgentBase",
    "AgentContext",
    "AgentMessage",
    # Workflow
    "WorkflowBase",
    "WorkflowStep",
    "WorkflowContext",
    # Exceptions
    "OMNIError",
    "ErrorContext",
    "AgentError",
    "AgentTimeoutError",
    "AgentValidationError",
    "AgentConfigurationError",
    "AgentNotFoundError",
    "AgentFatalError",
    "AgentDependencyError",
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMResponseError",
    "VectorDBError",
    "VectorDBConnectionError",
    "VectorDBQueryError",
    "VectorDBIndexError",
    "RAGError",
    "RAGIndexError",
    "RAGQueryError",
    "WorkflowError",
    "WorkflowTimeoutError",
    "WorkflowValidationError",
    "WorkflowStageError",
    "is_recoverable",
    "wrap_exception",
    # Retry utilities
    "RetryConfig",
    "RetryContext",
    "RETRY_FAST",
    "RETRY_STANDARD",
    "RETRY_PATIENT",
    "retry_async",
    "with_retry",
    "with_timeout_and_retry",
    "should_retry",
    # Thread-safe state
    "StateVersion",
    "ThreadSafeState",
    "SharedContext",
    "ThreadSafeSharedContext",
    # Timeout management
    "TimeoutConfig",
    "TimeoutResult",
    "TimeoutTracker",
    "TimeoutBudget",
    "timeout_context",
    "with_timeout",
    "run_with_timeout",
    "DEFAULT_TIMEOUT_CONFIG",
    # Dependencies
    "DependencyGraph",
    "DependencyInfo",
    "DependencyStatus",
    "DependencyError",
    "MissingDependencyError",
    "CircularDependencyError",
    "DependencyValidationError",
    "validate_dependencies",
    "get_initialization_order",
    # Connection pooling
    "ConnectionPool",
    "ConnectionFactory",
    "ConnectionState",
    "PoolConfig",
    "PoolStats",
    "PooledConnection",
    "PoolError",
    "PoolExhaustedError",
    "PoolClosedError",
    "SimpleConnectionFactory",
    "create_pool",
]
