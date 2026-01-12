# File Summaries

> Last updated: 2026-01-10T15:19:07.621696

Detailed summaries of each file for senior developers.

---

## Backend Files

### `backend\tests\__init__.py`
**Language:** python | **Lines:** 5

**Purpose:** OMNI Backend Test Suite

### `backend\core\timeout.py`
**Language:** python | **Lines:** 351

**Purpose:** Timeout Management

**Classes:**
- `TimeoutConfig`: Configuration for timeout behavior.
  - Methods: to_dict
- `TimeoutResult`: Result from a timed operation.
- `TimeoutTracker`: Tracks elapsed time during timeout context.
  - Methods: __init__, elapsed_seconds, remaining_seconds, mark_timeout, mark_complete
- `TimeoutBudget`: Manages timeout budget across multiple operations.

Useful for workflows where total time is limited
  - Methods: __init__, elapsed_seconds, remaining_seconds, is_expired, step (+1 more)
- `StepContext`: Context for a budget step.
  - Methods: elapsed, remaining

**Key Imports:** logging, dataclasses, contextlib, typing, datetime

**Depends on:** backend.core.exceptions

### `backend\core\interfaces\workflow.py`
**Language:** python | **Lines:** 339

**Purpose:** Workflow Interface

**Classes:**
- `WorkflowStatus`: Workflow execution states.
- `StepStatus`: Individual step execution states.
- `WorkflowStep`: A single step in a workflow.

Attributes:
    id: Unique step identifier
    name: Human-readable st
- `StepResult`: Result of executing a workflow step.
- `WorkflowContext`: Runtime context for workflow execution.

Attributes:
    workflow_id: Unique workflow run identifier
  - Methods: get_input, get_state, set_state, get_step_output
- `WorkflowMetadata`: Metadata describing a workflow.
- `WorkflowResult`: Final result of a workflow execution.
  - Methods: is_success
- `WorkflowBase`: Abstract base class for workflows.

Workflows define multi-step processes using LangChain/LangGraph.
  - Methods: __init__, metadata, status, steps, current_step (+5 more)

**Key Imports:** abc, dataclasses, uuid, enum, typing

### `demo\__init__.py`
**Language:** python | **Lines:** 1

**Purpose:** Demo module for OMNI.

### `backend\tests\agents\test_context_persistence.py`
**Language:** python | **Lines:** 618

**Purpose:** Tests for Context Agent persistence and unified DetailedFileSummary.

**Responsibilities:**
- Agent logic and behavior implementation

**Classes:**
- `TestDetailedFileSummary`: Tests for DetailedFileSummary dataclass.
  - Methods: test_to_dict_serialization, test_from_dict_deserialization, test_to_compact_string, test_to_markdown
- `TestProjectStructure`: Tests for ProjectStructure with unified files dict.
  - Methods: test_to_dict_with_files, test_from_dict_with_files, test_legacy_format_migration, test_get_file, test_search_by_class (+2 more)
- `TestContextAgentPersistence`: Tests for ContextAgent persistence functionality.
  - Methods: test_save_and_load_project_structure, test_no_load_when_persist_disabled, test_set_workspace_with_auto_load
- `TestContextAgentIntegration`: Integration tests for ContextAgent with unified summaries.
  - Methods: test_get_file_summary_returns_detailed, test_project_context_uses_detailed_files
- `TestVersionTracking`: Tests for ProjectStructure version tracking.
  - Methods: test_version_increments_on_change, test_change_history_recorded, test_change_history_limited_to_50, test_version_persisted_to_json, test_version_loaded_from_json (+3 more)

**Key Imports:** pytest, datetime, json, tempfile, unittest

**Depends on:** backend.agents.context_agent

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive

### `backend\agents\base_agents.py`
**Language:** python | **Lines:** 348

**Purpose:** Base Agent Implementations

**Responsibilities:**
- Agent logic and behavior implementation
- `AssistantAgent`: AI agent implementation
- `CodeAgent`: AI agent implementation
- `PlannerAgent`: AI agent implementation

**Classes:**
- `AssistantAgent`: General-purpose assistant agent.

Provides conversational AI capabilities with tool use support.
  - Methods: __init__, metadata, set_llm, get_system_prompt, process
- `CodeAgent`: Specialized agent for code-related tasks.

Handles code generation, review, and analysis.
  - Methods: __init__, metadata, set_llm, get_system_prompt, process
- `PlannerAgent`: Planning and orchestration agent.

Breaks down complex tasks and coordinates other agents.
  - Methods: __init__, metadata, set_llm, get_system_prompt, process

**Key Imports:** json, typing

**Depends on:** backend.core.interfaces.agent, backend.core.interfaces.llm

### `backend\core\interfaces\llm.py`
**Language:** python | **Lines:** 229

**Purpose:** LLM Provider Interface

**Classes:**
- `LLMRole`: Message roles for chat completions.
- `LLMMessage`: A single message in a conversation.
- `LLMConfig`: Configuration for LLM requests.
- `LLMUsage`: Token usage statistics.
- `LLMToolCall`: A tool/function call from the LLM.
- `LLMResponse`: Response from an LLM completion request.
- `LLMProvider`: Abstract base class for LLM providers.

All LLM adapters (OpenAI, Anthropic, local LLMs, etc.) must 
  - Methods: provider_name, is_available, complete, stream, embed (+3 more)
- `LLMProviderError`: Base exception for LLM provider errors.
  - Methods: __init__
- `LLMRateLimitError`: Raised when rate limited by the provider.
- `LLMAuthenticationError`: Raised when authentication fails.
- `LLMContextLengthError`: Raised when the context length is exceeded.

**Key Imports:** abc, dataclasses, typing, enum

**⚠️ Security Notes:**
- hardcoded_secret

**📋 Compliance Notes:**
- logging_sensitive

### `backend\agents\__init__.py`
**Language:** python | **Lines:** 29

**Purpose:** Agent Plugin System

**Responsibilities:**
- Agent logic and behavior implementation

**Depends on:** backend.agents.loader, backend.agents.orchestrator, backend.agents.base_agents, backend.agents.context_agent, backend.agents.rag_agent

### `backend\adapters\llm\factory.py`
**Language:** python | **Lines:** 158

**Purpose:** LLM Factory

**Classes:**
- `LLMFactory`: Factory for creating LLM providers.

Supports dynamic provider selection based on configuration.

Ex
  - Methods: register, create, from_config, list_providers, create_with_health_check

**Key Imports:** typing

**Depends on:** backend.core.interfaces.llm, backend.adapters.llm.openai_adapter, backend.adapters.llm.anthropic_adapter, backend.adapters.llm.local_adapter

**⚠️ Security Notes:**
- hardcoded_secret

### `backend\tests\agents\__init__.py`
**Language:** python | **Lines:** 5

**Purpose:** Agent Tests Package

**Responsibilities:**
- Agent logic and behavior implementation

### `backend\agents\loader.py`
**Language:** python | **Lines:** 485

**Purpose:** Agent Loader and Registry

**Responsibilities:**
- Agent logic and behavior implementation

**Classes:**
- `AgentRegistry`: Registry for agent plugins.

Maintains a catalog of available agents and their metadata.
Supports en
  - Methods: __init__, register, unregister, enable, disable (+5 more)
- `AgentLoader`: Dynamic agent plugin loader.

Loads agent plugins from:
- Built-in agents directory
- Custom plugin 
  - Methods: __init__, load_builtin_agents, load_from_directory, load_file, load_module (+3 more)

**Key Imports:** sys, typing, os, pathlib, importlib

**Depends on:** backend.core.interfaces.agent, backend.agents.base_agents, backend.agents.security_agent, backend.agents.compliance_agent, backend.agents.context_agent

### `backend\autogen\__init__.py`
**Language:** python | **Lines:** 22

**Purpose:** AutoGen Multi-Agent Runtime Module

**Depends on:** backend.autogen.runtime

### `backend\core\state.py`
**Language:** python | **Lines:** 334

**Purpose:** Thread-Safe State Management

**Classes:**
- `StateVersion`: Tracks version information for state changes.
  - Methods: increment
- `ThreadSafeState`: Thread-safe wrapper for mutable state in async contexts.

Provides:
- Automatic locking for all oper
  - Methods: __init__, version, read, write, get (+5 more)
- `ReadContext`: Context manager for reading state.
  - Methods: __init__, __aenter__, __aexit__
- `WriteContext`: Context manager for writing state.
  - Methods: __init__, __aenter__, __aexit__
- `SharedContext`: Typed shared context for agent communication.

Replaces the untyped `shared_state: dict` in AgentCon
  - Methods: to_dict
- `ThreadSafeSharedContext`: Thread-safe wrapper for SharedContext.

Provides field-level locking for efficient concurrent access
  - Methods: __init__, version, get_project_structure, set_project_structure, add_security_finding (+5 more)

**Key Imports:** logging, dataclasses, typing, datetime, asyncio

### `backend\integrations\__init__.py`
**Language:** python | **Lines:** 27

**Purpose:** OMNI Integrations Package

**Depends on:** backend.integrations.copilot_integration, backend.integrations.file_analyzer

### `backend\core\dependencies.py`
**Language:** python | **Lines:** 382

**Purpose:** Agent Dependency Management

**Classes:**
- `DependencyError`: Base exception for dependency-related errors.
- `MissingDependencyError`: Raised when a required dependency is missing.
  - Methods: __init__
- `CircularDependencyError`: Raised when circular dependencies are detected.
  - Methods: __init__
- `DependencyValidationError`: Raised when dependency validation fails.
  - Methods: __init__
- `DependencyStatus`: Status of a dependency.
- `DependencyInfo`: Information about a single dependency.
- `DependencyGraph`: Represents the dependency graph between agents.

Provides methods for:
- Validating all dependencies
  - Methods: add_agent, add_agent_metadata, get_dependencies, get_dependents, get_provides (+5 more)

**Key Imports:** dataclasses, typing, interfaces, enum

### `backend\observability.py`
**Language:** python | **Lines:** 665

**Purpose:** Observability Module

**Classes:**
- `CorrelationContext`: Thread-local storage for correlation IDs.

Allows tracing a request across all agent calls.
  - Methods: get, set, generate, push, pop (+1 more)
- `LogContext`: Context attached to log entries.
  - Methods: to_dict
- `StructuredLogger`: Logger with structured context and correlation IDs.

Usage:
    log = StructuredLogger("agent.securi
  - Methods: __init__, with_context, _format_message, debug, info (+3 more)
- `TimingMetric`: A single timing measurement.
- `MetricsCollector`: Collects and aggregates metrics.

Thread-safe collector for timing and counter metrics.
  - Methods: __init__, get_instance, record_timing, record_timing_sync, increment_counter (+5 more)
- `AgentSpan`: Represents a traced span for agent execution.

Use this to wrap agent.process() calls for full obser
  - Methods: duration_ms, complete, to_dict
- `RequestTrace`: Traces an entire request through all agents.

Usage:
    trace = RequestTrace()
    
    async with 
  - Methods: __init__, span, total_duration_ms, get_summary

**Key Imports:** logging, dataclasses, contextlib, uuid, typing

### `backend\agents\context_agent.py`
**Language:** python | **Lines:** 1636

**Purpose:** Context Agent

**Responsibilities:**
- Agent logic and behavior implementation
- `ContextAgent`: AI agent implementation

**Classes:**
- `DetailedFileSummary`: Detailed summary of a single file - the UNIFIED format.

This replaces the old short summaries (~200
  - Methods: to_dict, from_dict, to_compact_string, to_markdown
- `ContextAgentConfig`: Configuration for Context Agent.
- `ProjectStructure`: Persistent knowledge about the project structure.

UNIFIED APPROACH: Uses DetailedFileSummary for AL
  - Methods: increment_version, on_change, to_dict, from_dict, _guess_language (+5 more)
- `ImportantFact`: An important fact extracted from conversation.
  - Methods: to_dict
- `CurrentTask`: Tracks the current task being worked on.
  - Methods: to_dict
- `ContextAgent`: Agent that manages global session context.

This agent is responsible for:
1. Extracting important i
  - Methods: __init__, _get_persistence_path, _load_project_structure, _save_project_structure, set_workspace (+5 more)

**Key Imports:** logging, dataclasses, re, typing, datetime

**Depends on:** backend.core.interfaces.agent, backend.core.interfaces.llm, backend.core.state, backend.utils.gitignore, backend.integrations.file_analyzer

**📋 Compliance Notes:**
- logging_sensitive

### `backend\core\interfaces\agent.py`
**Language:** python | **Lines:** 335

**Purpose:** Agent Interface

**Classes:**
- `MessageType`: Types of messages agents can send/receive.
- `AgentStatus`: Agent lifecycle states.
- `AgentMessage`: A message exchanged between agents or with the user.

Attributes:
    id: Unique message identifier

  - Methods: to_dict, from_dict
- `AgentTool`: A tool that an agent can use.

Attributes:
    name: Tool name (used for invocation)
    description
  - Methods: to_openai_format
- `AgentContext`: Runtime context provided to agents during execution.

Attributes:
    session_id: Current session id
  - Methods: get_config, set_shared, get_shared
- `AgentCapability`: Describes a capability an agent provides.
- `AgentConfig`: Configuration for creating/configuring an agent.

Attributes:
    name: Agent name
    description: 
- `AgentMetadata`: Metadata describing an agent.

Attributes:
    id: Unique agent identifier
    name: Human-readable 
  - Methods: to_dict
- `AgentBase`: Abstract base class for all agents.

Agents are loaded as plugins and orchestrated by AutoGen.
Each 
  - Methods: __init__, metadata, status, status, tools (+5 more)

**Key Imports:** abc, dataclasses, uuid, enum, typing

**📋 Compliance Notes:**
- logging_sensitive

### `backend\tests\core\test_state.py`
**Language:** python | **Lines:** 313

**Purpose:** Tests for Thread-Safe State Management

**Classes:**
- `TestStateVersion`: Tests for StateVersion.
  - Methods: test_initial_version, test_increment
- `TestThreadSafeState`: Tests for ThreadSafeState wrapper.
  - Methods: test_get_initial_value, test_set_value, test_version_increments_on_set, test_read_context, test_write_context (+5 more)
- `TestSharedContext`: Tests for SharedContext dataclass.
  - Methods: test_default_values, test_to_dict
- `TestThreadSafeSharedContext`: Tests for ThreadSafeSharedContext.
  - Methods: test_project_structure, test_security_findings, test_concurrent_finding_additions, test_version_tracking, test_to_dict
- `TestConcurrencyStress`: Stress tests for concurrency safety.
  - Methods: test_many_concurrent_writers, test_readers_and_writers

**Key Imports:** datetime, asyncio, pytest

**Depends on:** backend.core.state

### `backend\tests\core\test_retry.py`
**Language:** python | **Lines:** 312

**Purpose:** Tests for Retry Logic

**Classes:**
- `TestRetryConfig`: Tests for RetryConfig.
  - Methods: test_default_values, test_custom_values, test_calculate_delay_exponential, test_calculate_delay_max_cap, test_calculate_delay_with_jitter
- `TestShouldRetry`: Tests for should_retry function.
  - Methods: test_retryable_exceptions, test_non_retryable_exceptions
- `TestRetryAsync`: Tests for retry_async function.
  - Methods: test_success_no_retry, test_retry_on_timeout, test_fail_after_max_retries, test_no_retry_on_non_recoverable, test_on_retry_callback
- `TestWithRetryDecorator`: Tests for with_retry decorator.
  - Methods: test_decorator_success, test_decorator_retry
- `TestRetryContext`: Tests for RetryContext context manager.
  - Methods: test_context_success, test_context_retry_tracking, test_context_max_retries
- `TestWithTimeoutAndRetry`: Tests for with_timeout_and_retry function.
  - Methods: test_timeout_triggers_retry
- `TestPresetConfigs`: Tests for preset configurations.
  - Methods: test_retry_fast, test_retry_standard, test_retry_patient

**Key Imports:** unittest, asyncio, pytest

**Depends on:** backend.core.retry, backend.core.exceptions

### `vscode-extension\out\backend\backendManager.d.ts`
**Language:** typescript | **Lines:** 110

**Purpose:** General module

**Responsibilities:**
- `BackendManager`: React component

**Classes:**
- `BackendManager`: 

**Key Imports:** vscode

**Depends on:** ../events/eventBus

### `backend\core\connection_pool.py`
**Language:** python | **Lines:** 534

**Purpose:** Connection Pool

**Classes:**
- `ConnectionState`: State of a pooled connection.
- `PoolConfig`: Configuration for connection pool.
- `PoolStats`: Statistics for a connection pool.
  - Methods: to_dict
- `PooledConnection`: Wrapper for a pooled connection.
  - Methods: mark_in_use, mark_idle, is_expired, age_seconds
- `ConnectionFactory`: Abstract factory for creating connections.
  - Methods: create, close, is_healthy, on_acquire, on_release
- `PoolError`: Base exception for pool errors.
- `PoolExhaustedError`: Raised when pool is exhausted and timeout reached.
  - Methods: __init__
- `PoolClosedError`: Raised when trying to use a closed pool.
- `ConnectionPool`: Async connection pool with health checks and metrics.

Example:
    ```python
    class VectorDBFact
  - Methods: __init__, config, stats, start, close (+5 more)
- `SimpleConnectionFactory`: Simple connection factory using callables.

Example:
    factory = SimpleConnectionFactory(
        
  - Methods: __init__, create, close, is_healthy

**Key Imports:** logging, abc, dataclasses, contextlib, enum

### `backend\adapters\vectordb\chroma_adapter.py`
**Language:** python | **Lines:** 345

**Purpose:** ChromaDB Vector Database Adapter

**Classes:**
- `ChromaAdapter`: ChromaDB vector database adapter.

Supports persistent and in-memory modes.

Example:
    ```python

  - Methods: __init__, provider_name, is_available, _get_client, _get_distance_fn (+5 more)

**Key Imports:** typing, chromadb, os

**Depends on:** backend.adapters.vectordb.base, backend.core.interfaces.vectordb

**⚠️ Security Notes:**
- hardcoded_secret

### `backend\core\retry.py`
**Language:** python | **Lines:** 313

**Purpose:** Retry Logic with Exponential Backoff

**Classes:**
- `RetryConfig`: Configuration for retry behavior.
  - Methods: __init__, calculate_delay
- `RetryContext`: Context manager for retry operations with state tracking.

Useful when you need to track retry state
  - Methods: __init__, __aenter__, __aexit__, should_continue, handle_error (+1 more)

**Key Imports:** random, logging, typing, functools, asyncio

**Depends on:** backend.core.exceptions

### `backend\tests\core\test_timeout.py`
**Language:** python | **Lines:** 270

**Purpose:** Tests for Timeout Management

**Classes:**
- `TestTimeoutConfig`: Tests for TimeoutConfig.
  - Methods: test_default_values, test_to_dict
- `TestTimeoutContext`: Tests for timeout_context.
  - Methods: test_success_within_timeout, test_timeout_raises_error, test_tracker_remaining_time
- `TestWithTimeoutDecorator`: Tests for with_timeout decorator.
  - Methods: test_decorator_success, test_decorator_timeout
- `TestRunWithTimeout`: Tests for run_with_timeout function.
  - Methods: test_success_result, test_timeout_with_raise, test_timeout_with_default, test_error_result
- `TestTimeoutBudget`: Tests for TimeoutBudget.
  - Methods: test_budget_tracking, test_budget_exhaustion, test_step_timeout, test_multiple_steps, test_summary
- `TestTimeoutTracker`: Tests for TimeoutTracker.
  - Methods: test_elapsed_time, test_mark_complete, test_mark_timeout
- `TestDefaultConfig`: Tests for default timeout configuration.
  - Methods: test_default_config_exists

**Key Imports:** datetime, asyncio, pytest

**Depends on:** backend.core.timeout, backend.core.exceptions

### `backend\adapters\llm\openai_adapter.py`
**Language:** python | **Lines:** 235

**Purpose:** OpenAI LLM Adapter

**Classes:**
- `OpenAIAdapter`: OpenAI LLM adapter supporting GPT-4, GPT-3.5, and embeddings.

Example:
    ```python
    adapter = 
  - Methods: __init__, provider_name, is_available, _get_client, complete (+3 more)

**Key Imports:** openai, typing, os

**Depends on:** backend.adapters.llm.base, backend.core.interfaces.llm

**⚠️ Security Notes:**
- hardcoded_secret

**📋 Compliance Notes:**
- logging_sensitive

### `backend\__init__.py`
**Language:** python | **Lines:** 64

**Purpose:** OMNI Backend Package

**Depends on:** backend.core, backend.adapters.llm.factory, backend.adapters.vectordb.factory, backend.agents, backend.config

### `backend\rag\service.py`
**Language:** python | **Lines:** 506

**Purpose:** RAG Service using LlamaIndex

**Responsibilities:**
- `RAGService`: Business logic service

**Classes:**
- `RAGConfig`: RAG configuration.
- `ContextVersion`: Tracks version of indexed content.
- `RAGResult`: Result from RAG query.
- `RAGService`: RAG Service using LlamaIndex for orchestration.

This service is:
- Completely optional (disabled by
  - Methods: __init__, is_available, initialize, _init_domain_index, ingest_file (+5 more)

**Key Imports:** logging, hashlib, dataclasses, llama_index, typing

**Depends on:** backend.utils.gitignore

**📋 Compliance Notes:**
- logging_sensitive

### `vscode-extension\out\backend\websocketClient.d.ts`
**Language:** typescript | **Lines:** 58

**Purpose:** General module

**Responsibilities:**
- `WebSocketClient`: React component

**Classes:**
- `WebSocketClient`: 

### `backend\core\interfaces\vectordb.py`
**Language:** python | **Lines:** 295

**Purpose:** Vector Database Provider Interface

**Classes:**
- `DistanceMetric`: Distance metrics for similarity search.
- `Document`: A document to be stored in the vector database.

Attributes:
    id: Unique identifier (auto-generat
  - Methods: __post_init__
- `SearchResult`: A single search result from the vector database.

Attributes:
    document: The matched document
   
- `CollectionConfig`: Configuration for creating a collection.
  - Methods: __post_init__
- `SearchConfig`: Configuration for search queries.
- `VectorDBProvider`: Abstract base class for vector database providers.

All vector DB adapters (Qdrant, Chroma, FAISS, e
  - Methods: provider_name, is_available, create_collection, delete_collection, collection_exists (+5 more)
- `VectorDBError`: Base exception for vector database errors.
  - Methods: __init__
- `CollectionNotFoundError`: Raised when a collection does not exist.
- `CollectionExistsError`: Raised when trying to create a collection that already exists.

**Key Imports:** abc, dataclasses, uuid, typing, enum

### `backend\server\main.py`
**Language:** python | **Lines:** 167

**Purpose:** Main Server Entry Point

**Functions:**
- `create_app(settings)` → `FastAPI`
  - Create the FastAPI application.
- `run_websocket_server(settings, handler)` → `None`
  - Run the WebSocket server.
- `run_server(config_path, host, port)` → `None`
  - Run the OMNI backend server.

Args:
    config_path: Path to configuration file

- `health_check()`
  - Health check endpoint.
- `get_config()`
  - Get current configuration (non-sensitive).
- `signal_handler(signum, frame)`
- `main()`
  - Main async entry point.

**Key Imports:** signal, fastapi, logging, sys, typing

**Depends on:** backend.config.settings, backend.server.websocket_handler

### `backend\server\__init__.py`
**Language:** python | **Lines:** 16

**Purpose:** Backend Server Package

**Depends on:** backend.server.main, backend.server.websocket_handler, backend.server.message_types

### `backend\integrations\file_analyzer.py`
**Language:** python | **Lines:** 657

**Purpose:** File Analyzer

**Classes:**
- `ClassInfo`: Information about a class.
- `FunctionInfo`: Information about a function.
- `FileAnalysis`: Complete analysis of a source file.
- `FileAnalyzer`: Analyzes source files to generate detailed summaries.

Example:
    ```python
    analyzer = FileAna
  - Methods: __init__, analyze_file, _detect_language, _analyze_python, _analyze_js_ts (+5 more)

**Key Imports:** logging, ast, dataclasses, re, typing

**Depends on:** backend.integrations.copilot_integration

**⚠️ Security Notes:**
- sql_injection
- shell_injection
- eval_usage
- pickle_usage

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive
- no_encryption

### `backend\agents\coding_agent.py`
**Language:** python | **Lines:** 735

**Purpose:** Coding Agent Plugin

**Responsibilities:**
- Agent logic and behavior implementation
- `CodingAgent`: AI agent implementation

**Classes:**
- `PatchValidationError`: Raised when a patch fails validation.
- `PatchType`: Types of code changes.
- `PatchResult`: Result of code generation - always a patch.
  - Methods: to_dict
- `CodingAgentConfig`: Configuration for coding agent.
- `CodingAgent`: Coding agent that produces patches only.

This agent:
- NEVER writes files - only produces unified d
  - Methods: __init__, metadata, set_llm, set_rag, set_context_agent (+5 more)

**Key Imports:** logging, dataclasses, re, enum, typing

**Depends on:** backend.core.interfaces.agent, backend.core.interfaces.llm

**📋 Compliance Notes:**
- logging_sensitive

### `backend\tests\agents\test_registry.py`
**Language:** python | **Lines:** 269

**Purpose:** Unit Tests for Agent Registry

**Responsibilities:**
- Agent logic and behavior implementation
- `TestAgent`: AI agent implementation
- `AnotherTestAgent`: AI agent implementation

**Classes:**
- `TestAgent`: A simple test agent for registry tests.
  - Methods: metadata, initialize, shutdown, process
- `AnotherTestAgent`: Another test agent for registry tests.
  - Methods: metadata, initialize, shutdown, process
- `TestAgentRegistryRegister`: Tests for agent registration functionality.
  - Methods: test_register_agent_class, test_register_multiple_agents, test_register_duplicate_raises_error, test_register_with_custom_name
- `TestAgentRegistryGet`: Tests for retrieving agents from registry.
  - Methods: test_get_registered_agent, test_get_unregistered_agent_returns_none, test_get_creates_new_instance
- `TestAgentRegistryUnregister`: Tests for unregistering agents.
  - Methods: test_unregister_agent, test_unregister_nonexistent_agent
- `TestAgentRegistryEnableDisable`: Tests for enabling/disabling agents.
  - Methods: test_agent_enabled_by_default, test_disable_agent, test_enable_disabled_agent, test_get_disabled_agent_returns_none, test_list_only_enabled_agents (+1 more)
- `TestAgentRegistryInfo`: Tests for getting agent information.
  - Methods: test_get_agent_info, test_get_info_nonexistent_returns_none, test_get_all_agent_info

**Key Imports:** typing, pytest

**Depends on:** backend.core.interfaces.agent, backend.agents.loader

### `backend\agents\workflow.py`
**Language:** python | **Lines:** 1019

**Purpose:** Workflow Orchestrator

**Responsibilities:**
- Agent logic and behavior implementation

**Classes:**
- `WorkflowResult`: Result from a complete workflow execution.
  - Methods: to_dict, get_summary
- `WorkflowOrchestrator`: Orchestrates the full analysis workflow.

Flow:
1. CONTEXT AGENT: Analyze project structure, create 
  - Methods: __init__, _emit_progress, analyze_workspace, analyze_file, _get_agent (+5 more)

**Key Imports:** logging, dataclasses, typing, datetime, pathlib

**Depends on:** backend.core.interfaces.agent, backend.agents.orchestrator, backend.integrations.copilot_integration, backend.integrations.file_analyzer, backend.integrations.copilot_integration

**⚠️ Security Notes:**
- shell_injection
- eval_usage
- pickle_usage

**📋 Compliance Notes:**
- logging_sensitive

### `backend\tests\test_observability.py`
**Language:** python | **Lines:** 396

**Purpose:** Tests for Observability Module

**Classes:**
- `TestCorrelationContext`: Tests for correlation ID management.
  - Methods: setup_method, test_generate_id, test_get_set, test_push_pop, test_correlation_scope (+1 more)
- `TestLogContext`: Tests for LogContext.
  - Methods: test_default_values, test_to_dict, test_to_dict_excludes_none
- `TestStructuredLogger`: Tests for StructuredLogger.
  - Methods: test_with_context, test_format_message
- `TestMetricsCollector`: Tests for MetricsCollector.
  - Methods: setup_method, test_record_timing, test_increment_counter, test_set_gauge, test_timing_stats (+2 more)
- `TestTimedOperation`: Tests for timed_operation context managers.
  - Methods: setup_method, test_timed_operation_success, test_timed_operation_failure, test_timed_operation_sync
- `TestTracedDecorator`: Tests for traced decorator.
  - Methods: setup_method, test_traced_async, test_traced_sync
- `TestAgentSpan`: Tests for AgentSpan.
  - Methods: test_create_span, test_complete_span, test_duration, test_to_dict
- `TestRequestTrace`: Tests for RequestTrace.
  - Methods: setup_method, test_create_trace, test_span_records_timing, test_span_error_handling, test_nested_spans (+1 more)

**Key Imports:** datetime, unittest, asyncio, pytest

**Depends on:** backend.observability

### `benchmark\run_benchmark.py`
**Language:** python | **Lines:** 717

**Purpose:** Benchmark Runner: Copilot con vs senza OMNI

**Classes:**
- `TokenEstimate`: Stima dei token per un testo.
  - Methods: from_text
- `TaskResult`: Risultato di un singolo task.
  - Methods: to_dict
- `BenchmarkReport`: Report completo del benchmark.
- `BenchmarkRunner`: Esegue il benchmark e raccoglie metriche.
  - Methods: __init__, run, _simulate_task_completion, _generate_simulated_content, _run_task_without_omni (+3 more)

**Key Imports:** dataclasses, sys, typing, datetime, json

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive

### `backend\rag\__init__.py`
**Language:** python | **Lines:** 23

**Purpose:** RAG (Retrieval-Augmented Generation) Module

**Depends on:** backend.rag.service

### `backend\adapters\llm\local_adapter.py`
**Language:** python | **Lines:** 257

**Purpose:** Local LLM Adapter

**Classes:**
- `LocalLLMAdapter`: Local LLM adapter supporting LM Studio, Ollama, and llama.cpp.

All these tools provide OpenAI-compa
  - Methods: __init__, provider_name, is_available, _get_client, complete (+5 more)

**Key Imports:** openai, typing, os

**Depends on:** backend.adapters.llm.base, backend.core.interfaces.llm

**⚠️ Security Notes:**
- hardcoded_secret

**📋 Compliance Notes:**
- logging_sensitive

### `backend\utils\__init__.py`
**Language:** python | **Lines:** 1

**Purpose:** Utility helpers for backend services.

**Responsibilities:**
- Helper functions and utilities

### `backend\autogen\runtime.py`
**Language:** python | **Lines:** 459

**Purpose:** AutoGen Multi-Agent Runtime

**Classes:**
- `AutoGenConfig`: Configuration for AutoGen runtime.
- `GroupChatResult`: Result of a group chat session.
  - Methods: to_dict
- `OmniAgentWrapper`: Wraps an OMNI agent as an AutoGen-compatible agent.

This wrapper allows existing OMNI agents to par
  - Methods: __init__, name, description, create_autogen_agent, process_message
- `AutoGenRuntime`: AutoGen Multi-Agent Runtime.

This runtime:
- Is completely optional (disabled by default)
- Wraps e
  - Methods: __init__, is_available, wrap_agent, _get_user_proxy, run_group_chat (+1 more)

**Key Imports:** logging, autogen, dataclasses, typing, datetime

**Depends on:** backend.core.interfaces.agent

### `backend\adapters\vectordb\base.py`
**Language:** python | **Lines:** 67

**Purpose:** Base Vector Database Adapter

**Classes:**
- `BaseVectorDBAdapter`: Base class for vector database adapters with common functionality.

Provides:
- Configuration manage
  - Methods: __init__, _validate_documents, _merge_search_config, _handle_error

**Key Imports:** abc, typing

**Depends on:** backend.core.interfaces.vectordb

### `test_omni.py`
**Language:** python | **Lines:** 229

**Purpose:** Test OMNI - Assistant to the Assistant

**Functions:**
- `test_validation()`
  - Test completo del sistema di validazione.

**Key Imports:** asyncio, sys, pytest

**Depends on:** backend.agents.context_agent, backend.agents.rag_agent, backend.agents.security_agent, backend.agents.compliance_agent

**⚠️ Security Notes:**
- hardcoded_secret
- sql_injection
- eval_usage

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive

### `backend\config\settings.py`
**Language:** python | **Lines:** 267

**Purpose:** Settings Model

**Classes:**
- `ServerSettings`: WebSocket server settings.
- `OpenAISettings`: OpenAI provider settings.
- `AnthropicSettings`: Anthropic provider settings.
- `LocalLLMSettings`: Local LLM provider settings.
- `LLMSettings`: LLM configuration.
- `QdrantSettings`: Qdrant settings.
- `ChromaSettings`: ChromaDB settings.
- `FAISSSettings`: FAISS settings.
- `VectorDBSettings`: Vector database configuration.
- `RAGSettings`: RAG configuration.
- `AgentSettings`: Agent configuration.
- `WorkflowSettings`: Workflow configuration.
- `LoggingSettings`: Logging configuration.
- `SecuritySettings`: Security configuration.
- `FeatureFlags`: Feature flags.
- `Settings`: Main settings class.

Loads configuration from:
1. Default values
2. YAML config file
3. Environment
  - Methods: from_yaml, get_llm_config, get_vectordb_config

**Key Imports:** typing, functools, os, pathlib, pydantic

**Depends on:** backend.config.loader

**📋 Compliance Notes:**
- logging_sensitive

### `backend\agents\orchestrator.py`
**Language:** python | **Lines:** 708

**Purpose:** Agent Orchestrator

**Responsibilities:**
- Agent logic and behavior implementation

**Classes:**
- `AgentOrchestrator`: Orchestrates multi-agent conversations and workflows.

Supports various patterns:
- Sequential: Agen
  - Methods: __init__, add_agent, _wire_agent_integrations, remove_agent, add_hook (+5 more)

**Key Imports:** uuid, logging, asyncio, typing

**Depends on:** backend.core.interfaces.agent, backend.core.interfaces.llm, backend.core.exceptions, backend.core.retry, backend.agents.loader

**📋 Compliance Notes:**
- logging_sensitive

### `backend\config\__init__.py`
**Language:** python | **Lines:** 14

**Purpose:** Configuration Management

**Depends on:** backend.config.settings, backend.config.loader

### `backend\agents\rag_agent.py`
**Language:** python | **Lines:** 1000

**Purpose:** RAG Agent

**Responsibilities:**
- Agent logic and behavior implementation
- `RAGAgent`: AI agent implementation
- `RAGService`: Business logic service

**Classes:**
- `RAGAgentConfig`: Configuration for RAG Agent.
- `FileSummary`: Compact file summary for token-efficient retrieval.
Instead of returning 50k of raw code, we return 
  - Methods: to_dict, to_compact_string
- `RAGQueryResult`: Result from a RAG query.
  - Methods: to_dict
- `RAGAgent`: Agent that intelligently manages RAG operations.

Unlike the passive RAGService, this agent:
1. DECI
  - Methods: __init__, metadata, set_llm, set_rag_service, is_available (+5 more)
- `RAGService`: 
- `RAGResult`: 
- `RAGConfig`: 

**Key Imports:** logging, dataclasses, re, typing, datetime

**Depends on:** backend.core.interfaces.agent, backend.core.interfaces.llm, backend.rag.service

**📋 Compliance Notes:**
- logging_sensitive

### `backend\tests\conftest.py`
**Language:** python | **Lines:** 423

**Purpose:** Pytest Configuration and Shared Fixtures

**Responsibilities:**
- `FakeVectorStore`: State management store

**Classes:**
- `FakeLLMProvider`: Fake LLM provider for testing purposes.

This provider returns predictable, configurable responses
w
  - Methods: __init__, provider_name, is_available, set_response, set_stream_chunks (+5 more)
- `FakeVectorStore`: Fake vector store for testing purposes.

This provider stores documents in memory and provides
basic
  - Methods: __init__, provider_name, is_available, collection_exists, count (+5 more)

**Key Imports:** dataclasses, typing, os, pytest

**Depends on:** backend.core.interfaces.llm, backend.core.interfaces.vectordb, backend.core.interfaces.agent

**⚠️ Security Notes:**
- hardcoded_secret

**📋 Compliance Notes:**
- logging_sensitive

### `backend\config\loader.py`
**Language:** python | **Lines:** 245

**Purpose:** Configuration Loader

**Classes:**
- `ConfigLoader`: Loads configuration from YAML files with environment variable support.

Features:
- Environment vari
  - Methods: __init__, load_yaml, load_multiple, _resolve_path, _substitute_env_vars (+4 more)

**Key Imports:** re, typing, os, yaml, pathlib

### `backend\tests\core\test_dependencies.py`
**Language:** python | **Lines:** 404

**Purpose:** Tests for Agent Dependency Management

**Responsibilities:**
- `MockAgent`: AI agent implementation

**Classes:**
- `MockAgent`: Mock agent for testing.
  - Methods: __init__, metadata, process
- `TestDependencyGraph`: Tests for DependencyGraph.
  - Methods: test_add_agent, test_get_dependencies, test_get_dependents, test_get_provides
- `TestDependencyValidation`: Tests for dependency validation.
  - Methods: test_valid_dependencies, test_missing_dependency, test_validate_strict_raises, test_find_missing_dependencies
- `TestCircularDependencies`: Tests for circular dependency detection.
  - Methods: test_no_cycles, test_simple_cycle, test_longer_cycle, test_self_dependency
- `TestTopologicalSort`: Tests for initialization order.
  - Methods: test_simple_order, test_complex_order, test_topological_sort_raises_on_cycle, test_get_initialization_order_alias
- `TestTransitiveDependencies`: Tests for transitive dependency resolution.
  - Methods: test_get_all_transitive_dependencies, test_transitive_with_diamond
- `TestDependencyVisualization`: Tests for dependency visualization.
  - Methods: test_to_mermaid, test_to_dot
- `TestDependencyInfo`: Tests for detailed dependency info.
  - Methods: test_get_dependency_info
- `TestConvenienceFunctions`: Tests for convenience functions.
  - Methods: test_validate_dependencies_function, test_validate_dependencies_raises, test_get_initialization_order_function
- `TestRealAgents`: Tests with real OMNI agents.
  - Methods: test_omni_agent_dependencies

**Key Imports:** dataclasses, typing, pytest

**Depends on:** backend.core.dependencies, backend.core.interfaces.agent, backend.agents.context_agent, backend.agents.rag_agent, backend.agents.security_agent

### `vscode-extension\out\backend\websocketClient.js`
**Language:** javascript | **Lines:** 158

**Purpose:** General module

**Responsibilities:**
- `WebSocketClient`: React component

**Classes:**
- `WebSocketClient`: 

### `backend\adapters\llm\anthropic_adapter.py`
**Language:** python | **Lines:** 249

**Purpose:** Anthropic LLM Adapter

**Classes:**
- `AnthropicAdapter`: Anthropic Claude adapter.

Example:
    ```python
    adapter = AnthropicAdapter(
        api_key="s
  - Methods: __init__, provider_name, is_available, default_embedding_model, _get_client (+5 more)

**Key Imports:** anthropic, typing, os, json

**Depends on:** backend.adapters.llm.base, backend.core.interfaces.llm

**⚠️ Security Notes:**
- hardcoded_secret

**📋 Compliance Notes:**
- logging_sensitive

### `backend\core\interfaces\__init__.py`
**Language:** python | **Lines:** 21

**Purpose:** Core interfaces package.

**Depends on:** backend.core.interfaces.llm, backend.core.interfaces.vectordb, backend.core.interfaces.agent, backend.core.interfaces.workflow

### `backend\integrations\copilot_integration.py`
**Language:** python | **Lines:** 1093

**Purpose:** Copilot Integration

**Classes:**
- `FileSummary`: Detailed summary of a single file for senior developers.
  - Methods: to_markdown
- `ProjectContext`: Complete project context for Copilot.
- `CopilotIntegration`: Generates and maintains files for Copilot integration.

Creates a .omni/ folder structure:
```
.omni
  - Methods: __init__, _ensure_directories, _analyze_data_flow, generate_all, generate_copilot_instructions (+5 more)

**Key Imports:** logging, dataclasses, typing, datetime, os

**📋 Compliance Notes:**
- logging_sensitive

### `backend\utils\gitignore.py`
**Language:** python | **Lines:** 74

**Purpose:** Helpers for applying .gitignore-style filtering during scans.

**Responsibilities:**
- Helper functions and utilities

**Functions:**
- `_clean_patterns(patterns)` → `list[str]`
- `load_gitignore(root)` → `PathSpec`
  - Load .gitignore patterns from ``root`` plus default ignores.
- `should_ignore(path, root, spec)` → `bool`
  - Check whether ``path`` is ignored relative to ``root`` using ``spec``.

**Key Imports:** pathlib, pathspec, typing

### `backend\adapters\llm\base.py`
**Language:** python | **Lines:** 100

**Purpose:** Base LLM Adapter

**Classes:**
- `BaseLLMAdapter`: Base class for LLM adapters with common functionality.

Provides:
- Configuration management
- Reque
  - Methods: __init__, default_model, default_embedding_model, _merge_config, _convert_messages (+1 more)

**Key Imports:** abc, typing

**Depends on:** backend.core.interfaces.llm

**📋 Compliance Notes:**
- logging_sensitive

### `backend\core\exceptions.py`
**Language:** python | **Lines:** 652

**Purpose:** OMNI Exception Hierarchy

**Classes:**
- `ErrorContext`: Additional context for debugging errors.

Attributes:
    agent_id: ID of the agent that raised the 
  - Methods: to_dict
- `OMNIError`: Base exception for all OMNI errors.

All custom exceptions inherit from this class, allowing:
- Catc
  - Methods: __init__, __str__, to_dict
- `AgentError`: Base class for agent-related errors.
- `AgentTimeoutError`: Raised when an agent operation times out.

This is a RECOVERABLE error - the operation can be retrie
  - Methods: __init__
- `AgentValidationError`: Raised when input validation fails.

This is NOT recoverable without fixing the input.

Example:
   
  - Methods: __init__
- `AgentConfigurationError`: Raised when agent configuration is invalid.

This is NOT recoverable without fixing configuration.


  - Methods: __init__
- `AgentNotFoundError`: Raised when a requested agent is not registered.

Example:
    agent = registry.get("unknown_agent")
  - Methods: __init__
- `AgentFatalError`: Raised when an unrecoverable error occurs.

This indicates the agent should be stopped/restarted.

E
  - Methods: __init__
- `AgentDependencyError`: Raised when a required agent dependency is missing.

Example:
    if not self._context_agent:
      
  - Methods: __init__
- `LLMError`: Base class for LLM provider errors.
- `LLMTimeoutError`: Raised when LLM call times out.

This is RECOVERABLE - can retry with backoff.
  - Methods: __init__
- `LLMRateLimitError`: Raised when LLM rate limit is hit.

This is RECOVERABLE - retry after delay.

Attributes:
    retry_
  - Methods: __init__
- `LLMAuthenticationError`: Raised when LLM authentication fails.

This is NOT recoverable without fixing credentials.
  - Methods: __init__
- `LLMResponseError`: Raised when LLM returns invalid response.

This is RECOVERABLE - can retry.
  - Methods: __init__
- `VectorDBError`: Base class for vector database errors.
- `VectorDBConnectionError`: Raised when VectorDB connection fails.

This is RECOVERABLE - can retry connection.
  - Methods: __init__
- `VectorDBQueryError`: Raised when VectorDB query fails.

This is RECOVERABLE - can retry query.
  - Methods: __init__
- `VectorDBIndexError`: Raised when VectorDB indexing fails.

This is RECOVERABLE - can retry indexing.
  - Methods: __init__
- `RAGError`: Base class for RAG service errors.
- `RAGIndexError`: Raised when RAG indexing fails.
  - Methods: __init__
- `RAGQueryError`: Raised when RAG query fails.
  - Methods: __init__
- `WorkflowError`: Base class for workflow errors.
- `WorkflowTimeoutError`: Raised when workflow times out.

This is RECOVERABLE - partial results may be available.
  - Methods: __init__
- `WorkflowValidationError`: Raised when workflow validation fails.
  - Methods: __init__
- `WorkflowStageError`: Raised when a workflow stage fails.
  - Methods: __init__

**Key Imports:** datetime, dataclasses, typing

### `backend\adapters\vectordb\qdrant_adapter.py`
**Language:** python | **Lines:** 354

**Purpose:** Qdrant Vector Database Adapter

**Classes:**
- `QdrantAdapter`: Qdrant vector database adapter.

Supports both local (in-memory/disk) and cloud Qdrant instances.

E
  - Methods: __init__, provider_name, is_available, _get_client, _get_distance (+5 more)

**Key Imports:** qdrant_client, typing, os

**Depends on:** backend.adapters.vectordb.base, backend.core.interfaces.vectordb

**⚠️ Security Notes:**
- hardcoded_secret

### `demo\sample_project\auth.py`
**Language:** python | **Lines:** 62

**Purpose:** Sample Authentication Module

**Classes:**
- `UserSession`: User session manager.
  - Methods: __init__, log_activity

**Key Imports:** logging, hashlib

**⚠️ Security Notes:**
- hardcoded_secret

**📋 Compliance Notes:**
- pii_handling

### `backend\tests\core\test_exceptions.py`
**Language:** python | **Lines:** 325

**Purpose:** Tests for OMNI Exception Hierarchy

**Classes:**
- `TestErrorContext`: Tests for ErrorContext dataclass.
  - Methods: test_default_values, test_with_values, test_to_dict
- `TestOMNIError`: Tests for base OMNIError class.
  - Methods: test_basic_error, test_with_context, test_recoverable_flag, test_with_cause, test_to_dict
- `TestAgentErrors`: Tests for agent-related exceptions.
  - Methods: test_agent_error_hierarchy, test_timeout_error_is_recoverable, test_validation_error_is_not_recoverable, test_configuration_error, test_not_found_error (+2 more)
- `TestLLMErrors`: Tests for LLM-related exceptions.
  - Methods: test_llm_error_hierarchy, test_timeout_is_recoverable, test_rate_limit_is_recoverable, test_auth_error_not_recoverable
- `TestVectorDBErrors`: Tests for VectorDB-related exceptions.
  - Methods: test_vectordb_error_hierarchy, test_connection_error_is_recoverable, test_query_error_stores_query
- `TestWorkflowErrors`: Tests for workflow-related exceptions.
  - Methods: test_workflow_error_hierarchy, test_timeout_stores_completed_stages, test_stage_error_stores_stage
- `TestHelperFunctions`: Tests for helper functions.
  - Methods: test_is_recoverable_with_omni_error, test_is_recoverable_with_standard_errors, test_wrap_exception, test_wrap_exception_with_context
- `TestExceptionCatching`: Tests for catching exceptions at different levels.
  - Methods: test_catch_specific_agent_error, test_catch_agent_error_base, test_catch_omni_error_base

**Key Imports:** datetime, pytest

**Depends on:** backend.core.exceptions

### `backend\tests\core\test_llm_adapter.py`
**Language:** python | **Lines:** 249

**Purpose:** Unit Tests for LLM Adapter Interface

**Classes:**
- `TestFakeLLMProviderHealth`: Tests for LLM provider health check functionality.
  - Methods: test_health_check_returns_false_before_init, test_health_check_returns_true_after_init, test_health_check_can_be_set_unhealthy, test_health_check_returns_false_after_shutdown
- `TestFakeLLMProviderComplete`: Tests for LLM provider text generation (complete) functionality.
  - Methods: test_complete_returns_response, test_complete_returns_configured_response, test_complete_includes_model_in_response, test_complete_includes_usage_stats, test_complete_increments_call_count (+1 more)
- `TestFakeLLMProviderStream`: Tests for LLM provider streaming functionality.
  - Methods: test_stream_yields_chunks, test_stream_yields_configured_chunks
- `TestFakeLLMProviderEmbed`: Tests for LLM provider embedding functionality.
  - Methods: test_embed_returns_embeddings, test_embed_returns_consistent_dimension, test_embed_returns_configured_embedding

**Key Imports:** typing, pytest

**Depends on:** backend.core.interfaces.llm, backend.tests.conftest

**📋 Compliance Notes:**
- logging_sensitive

### `backend\adapters\vectordb\__init__.py`
**Language:** python | **Lines:** 20

**Purpose:** Vector Database Adapters Package

**Depends on:** backend.adapters.vectordb.base, backend.adapters.vectordb.qdrant_adapter, backend.adapters.vectordb.chroma_adapter, backend.adapters.vectordb.faiss_adapter, backend.adapters.vectordb.factory

### `backend\agents\compliance_agent.py`
**Language:** python | **Lines:** 948

**Purpose:** Compliance Agent Plugin

**Responsibilities:**
- Agent logic and behavior implementation
- `ComplianceAgent`: AI agent implementation

**Classes:**
- `ComplianceSeverity`: Compliance finding severity.
- `ComplianceStatus`: Compliance check status.
- `ComplianceRule`: A single compliance rule.

Rules are loaded from external files and define what to check.
- `ComplianceFinding`: A compliance finding from rule evaluation.
  - Methods: to_dict
- `ComplianceAgentConfig`: Configuration for compliance agent.
- `ComplianceAgent`: Compliance checking agent using external rulesets.

This agent:
- Loads rules from JSON/YAML files (
  - Methods: __init__, metadata, set_llm, set_rag, set_context_agent (+5 more)

**Key Imports:** logging, dataclasses, re, enum, typing

**Depends on:** backend.core.interfaces.agent, backend.core.interfaces.llm

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive

### `test_omni_simple.py`
**Language:** python | **Lines:** 357

**Purpose:** Test OMNI - Assistant to the Assistant

**Classes:**
- `Severity`: 
- `SecurityFinding`: 
- `ComplianceFinding`: 
- `SimpleSecurityChecker`: Security checker semplificato per demo.
  - Methods: check
- `SimpleComplianceChecker`: Compliance checker semplificato per demo.
  - Methods: check

**Key Imports:** dataclasses, re, sys, typing, enum

**⚠️ Security Notes:**
- hardcoded_secret
- sql_injection
- shell_injection
- eval_usage

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive

### `backend\tests\fakes\__init__.py`
**Language:** python | **Lines:** 20

**Purpose:** Fake Provider Implementations for Testing

**Depends on:** backend.tests.conftest

### `backend\tests\core\test_connection_pool.py`
**Language:** python | **Lines:** 414

**Purpose:** Tests for Connection Pool

**Classes:**
- `MockConnection`: Mock connection for testing.
  - Methods: __init__, close
- `MockConnectionFactory`: Mock factory for testing.
  - Methods: __init__, create, close, is_healthy
- `TestPooledConnection`: Tests for PooledConnection wrapper.
  - Methods: test_initial_state, test_mark_in_use, test_mark_idle, test_is_expired, test_in_use_not_expired
- `TestPoolConfig`: Tests for PoolConfig.
  - Methods: test_defaults
- `TestPoolStats`: Tests for PoolStats.
  - Methods: test_to_dict
- `TestConnectionPool`: Tests for ConnectionPool.
  - Methods: test_start_creates_min_connections, test_acquire_returns_connection, test_connection_reused, test_creates_new_when_all_in_use, test_exhausted_pool_timeout (+5 more)
- `TestSimpleConnectionFactory`: Tests for SimpleConnectionFactory.
  - Methods: test_create_sync_function, test_create_async_function, test_health_check
- `TestCreatePool`: Tests for create_pool convenience function.
  - Methods: test_create_pool
- `TestPoolHealthChecks`: Tests for health check behavior.
  - Methods: test_unhealthy_connection_removed, test_healthy_connection_kept

**Key Imports:** datetime, unittest, asyncio, pytest

**Depends on:** backend.core.connection_pool

### `backend\tests\core\test_vectordb_adapter.py`
**Language:** python | **Lines:** 195

**Purpose:** Unit Tests for VectorDB Adapter Interface

**Classes:**
- `TestFakeVectorStoreHealth`: Tests for vector store health check functionality.
  - Methods: test_health_check_returns_false_before_init, test_health_check_returns_true_after_init, test_health_check_can_be_set_unhealthy
- `TestFakeVectorStoreCollections`: Tests for vector store collection management.
  - Methods: test_create_collection, test_delete_collection, test_list_collections_empty
- `TestFakeVectorStoreDocuments`: Tests for vector store document operations.
  - Methods: test_upsert_documents, test_get_documents_by_id, test_delete_documents
- `TestFakeVectorStoreSearch`: Tests for vector store search functionality.
  - Methods: test_search_returns_results, test_search_with_filter, test_search_empty_collection

**Key Imports:** typing, pytest

**Depends on:** backend.core.interfaces.vectordb, backend.tests.conftest

### `backend\agents\security_agent.py`
**Language:** python | **Lines:** 756

**Purpose:** Security Agent Plugin

**Responsibilities:**
- Agent logic and behavior implementation
- `SecurityAgent`: AI agent implementation

**Classes:**
- `Severity`: Security finding severity levels.
- `FindingCategory`: Categories of security findings.
- `SecurityFinding`: A single security finding.

Structured output format for security issues.
  - Methods: to_dict
- `SecurityAgentConfig`: Configuration for security agent.
- `SecurityAgent`: Read-only security analysis agent.

This agent:
- NEVER writes files
- Runs Semgrep for static analy
  - Methods: __init__, metadata, set_llm, set_context_agent, set_rag_agent (+5 more)

**Key Imports:** logging, subprocess, dataclasses, re, enum

**Depends on:** backend.core.interfaces.agent, backend.core.interfaces.llm, backend.core.interfaces.llm

**⚠️ Security Notes:**
- shell_injection
- eval_usage

**📋 Compliance Notes:**
- logging_sensitive

### `vscode-extension\src\backend\websocketClient.ts`
**Language:** typescript | **Lines:** 187

**Purpose:** General module

**Responsibilities:**
- `WebSocketClient`: React component

**Classes:**
- `WebSocketClient`: 

**Functions:**
- `resolve()`
- `reject()`

**Key Imports:** ws

### `backend\server\websocket_handler.py`
**Language:** python | **Lines:** 670

**Purpose:** WebSocket Handler

**Responsibilities:**
- `WebSocketHandler`: Request handling

**Classes:**
- `WebSocketHandler`: Handles WebSocket connections from VS Code extension.

Routes messages to appropriate handlers and m
  - Methods: __init__, _initialize_agents, handle_connection, _route_message, _handle_chat_message (+5 more)

**Key Imports:** logging, uuid, typing, json, websockets

**Depends on:** backend.server.message_types, backend.core.interfaces.agent, backend.core.exceptions, backend.agents.orchestrator, backend.agents.workflow

### `backend\adapters\vectordb\faiss_adapter.py`
**Language:** python | **Lines:** 413

**Purpose:** FAISS Vector Database Adapter

**Classes:**
- `FAISSCollection`: Internal representation of a FAISS collection.
- `FAISSAdapter`: FAISS vector database adapter.

Supports in-memory and disk-persisted indexes.

Example:
    ```pyth
  - Methods: __init__, provider_name, is_available, _get_faiss, _get_index_type (+5 more)

**Key Imports:** faiss, dataclasses, typing, json, os

**Depends on:** backend.adapters.vectordb.base, backend.core.interfaces.vectordb

### `backend\adapters\vectordb\factory.py`
**Language:** python | **Lines:** 104

**Purpose:** Vector Database Factory

**Classes:**
- `VectorDBFactory`: Factory for creating vector database providers.

Example:
    ```python
    # Create from config
   
  - Methods: register, create, from_config, list_providers, create_with_health_check

**Key Imports:** typing

**Depends on:** backend.core.interfaces.vectordb, backend.adapters.vectordb.qdrant_adapter, backend.adapters.vectordb.chroma_adapter, backend.adapters.vectordb.faiss_adapter

### `vscode-extension\out\backend\backendManager.js`
**Language:** javascript | **Lines:** 370

**Purpose:** General module

**Responsibilities:**
- `BackendManager`: React component

**Classes:**
- `BackendManager`: 

**Functions:**
- `onOpen()`
- `onClose()`
- `onError()`
- `onMessage()`

### `demo\demo_mode.py`
**Language:** python | **Lines:** 248

**Purpose:** OMNI Demo Mode

**Classes:**
- `DemoConfig`: Demo configuration.

**Key Imports:** logging, asyncio, sys, argparse, pathlib

**Depends on:** backend.tests.conftest, backend.core.interfaces.llm, backend.core.interfaces.vectordb, backend.core.interfaces.agent, backend.agents.base_agents

### `backend\server\message_types.py`
**Language:** python | **Lines:** 173

**Purpose:** Message Types

**Classes:**
- `MessageType`: Types of messages exchanged between frontend and backend.
- `Message`: A message in the communication protocol.

Attributes:
    type: Message type
    data: Message paylo
  - Methods: to_dict, from_dict, chat_response, stream_start, stream_chunk (+5 more)

**Key Imports:** dataclasses, uuid, typing, enum, datetime

### `backend\adapters\llm\__init__.py`
**Language:** python | **Lines:** 20

**Purpose:** LLM Adapters Package

**Depends on:** backend.adapters.llm.base, backend.adapters.llm.openai_adapter, backend.adapters.llm.anthropic_adapter, backend.adapters.llm.local_adapter, backend.adapters.llm.factory

### `backend\tests\core\__init__.py`
**Language:** python | **Lines:** 5

**Purpose:** Core Tests Package

### `backend\core\__init__.py`
**Language:** python | **Lines:** 204

**Purpose:** OMNI Backend Core Package

**Depends on:** backend.core.interfaces.llm, backend.core.interfaces.vectordb, backend.core.interfaces.agent, backend.core.interfaces.workflow, backend.core.exceptions

### `vscode-extension\src\backend\backendManager.ts`
**Language:** typescript | **Lines:** 389

**Purpose:** General module

**Responsibilities:**
- `BackendManager`: React component

**Classes:**
- `BackendManager`: 

**Functions:**
- `onOpen()`
- `onClose()`
- `onError()`
- `onMessage()`

**Key Imports:** fs, vscode, path, child_process

**Depends on:** ../events/eventBus, ./websocketClient

## Frontend Files

### `vscode-extension\src\extension.ts`
**Language:** typescript | **Lines:** 144

**Purpose:** General module

**Functions:**
- `activate()`
- `deactivate()`

**Key Imports:** vscode

**Depends on:** ./backend/backendManager, ./views/chatViewProvider, ./views/agentsTreeProvider, ./views/historyTreeProvider, ./commands/commandHandler

### `vscode-extension\src\tests\eventBus.test.ts`
**Language:** typescript | **Lines:** 220

**Purpose:** Test File

**Responsibilities:**
- Unit/integration tests

**Depends on:** ../events/eventBus

### `vscode-extension\src\tests\websocketClient.test.ts`
**Language:** typescript | **Lines:** 279

**Purpose:** Test File

**Responsibilities:**
- Unit/integration tests

**Functions:**
- `simulateOpen()`
- `simulateClose()`
- `simulateMessage()`
- `simulateError()`

**Depends on:** ../backend/websocketClient

### `vscode-extension\src\views\chatViewProvider.ts`
**Language:** typescript | **Lines:** 912

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `ChatViewProvider`: React component

**Classes:**
- `ChatViewProvider`: 

**Functions:**
- `setConnected()`
- `setAgent()`
- `addMessage()`
- `addMessageToDOM()`
- `formatMessage()`
- `addCopyButton()`
- `startStreaming()`
- `appendStreamChunk()`
- `endStreaming()`
- `showError()`
- ... and 4 more functions

**Key Imports:** vscode

**Depends on:** ../backend/backendManager, ../events/eventBus

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive

### `vscode-extension\src\events\eventBus.ts`
**Language:** typescript | **Lines:** 211

**Purpose:** General module

**Responsibilities:**
- `EventBus`: React component

**Classes:**
- `EventBus`: 

**Functions:**
- `dispose()`

**Key Imports:** vscode

### `vscode-extension\src\watchers\fileWatcher.ts`
**Language:** typescript | **Lines:** 402

**Purpose:** General module

**Responsibilities:**
- `FileWatcher`: React component

**Classes:**
- `FileWatcher`: 

**Key Imports:** vscode

**Depends on:** ../events/eventBus, ../backend/backendManager

### `vscode-extension\src\commands\commandHandler.ts`
**Language:** typescript | **Lines:** 249

**Purpose:** Request Handler

**Responsibilities:**
- Handles incoming requests
- `CommandHandler`: Request handling

**Classes:**
- `CommandHandler`: 

**Functions:**
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- ... and 6 more functions

**Key Imports:** vscode

**Depends on:** ../backend/backendManager, ../views/chatViewProvider, ../views/agentsTreeProvider, ../views/historyTreeProvider, ../events/eventBus

### `vscode-extension\src\tests\setup.ts`
**Language:** typescript | **Lines:** 126

**Purpose:** General module

**Functions:**
- `dispose()`

### `vscode-extension\src\views\historyTreeProvider.ts`
**Language:** typescript | **Lines:** 337

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `HistoryTreeProvider`: React component
- `HistoryTreeItem`: React component
- `SessionTreeItem`: React component
- `EmptyHistoryItem`: React component

**Classes:**
- `HistoryTreeProvider`: 
- `HistoryTreeItem`: 
- `SessionTreeItem`: 
- `EmptyHistoryItem`: 

**Key Imports:** vscode

**Depends on:** ../events/eventBus

### `vscode-extension\src\views\agentsTreeProvider.ts`
**Language:** typescript | **Lines:** 277

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `AgentsTreeProvider`: React component
- `AgentTreeItem`: React component

**Classes:**
- `AgentsTreeProvider`: 
- `AgentTreeItem`: 

**Key Imports:** vscode

**Depends on:** ../backend/backendManager, ../events/eventBus

## Other Files

### `vscode-extension\out\events\eventBus.js`
**Language:** javascript | **Lines:** 183

**Purpose:** General module

**Responsibilities:**
- `EventBus`: React component

**Classes:**
- `EventBus`: 

**Functions:**
- `wrapper()`
- `dispose()`

### `vscode-extension\out\tests\websocketClient.test.d.ts`
**Language:** typescript | **Lines:** 9

**Purpose:** Test File

**Responsibilities:**
- Unit/integration tests

### `vscode-extension\out\tests\setup.js`
**Language:** javascript | **Lines:** 115

**Purpose:** General module

**Functions:**
- `dispose()`

### `benchmark\tasks.yaml`
**Language:** yaml | **Lines:** 178

**Purpose:** General module

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive

### `vscode-extension\out\tests\websocketClient.test.js`
**Language:** javascript | **Lines:** 226

**Purpose:** Test File

**Responsibilities:**
- Unit/integration tests

**Functions:**
- `simulateOpen()`
- `simulateClose()`
- `simulateMessage()`
- `simulateError()`

### `vscode-extension\out\views\agentsTreeProvider.d.ts`
**Language:** typescript | **Lines:** 56

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `AgentsTreeProvider`: React component
- `AgentTreeItem`: React component

**Classes:**
- `AgentsTreeProvider`: 
- `AgentTreeItem`: 

**Key Imports:** vscode

**Depends on:** ../backend/backendManager, ../events/eventBus

### `vscode-extension\out\commands\commandHandler.d.ts`
**Language:** typescript | **Lines:** 42

**Purpose:** Request Handler

**Responsibilities:**
- Handles incoming requests
- `CommandHandler`: Request handling

**Classes:**
- `CommandHandler`: 

**Key Imports:** vscode

**Depends on:** ../backend/backendManager, ../views/chatViewProvider, ../views/agentsTreeProvider, ../views/historyTreeProvider, ../events/eventBus

### `vscode-extension\out\extension.d.ts`
**Language:** typescript | **Lines:** 10

**Purpose:** General module

**Functions:**
- `activate()`
- `deactivate()`

**Key Imports:** vscode

### `backend\config\default.yaml`
**Language:** yaml | **Lines:** 136

**Purpose:** General module

**📋 Compliance Notes:**
- logging_sensitive

### `vscode-extension\out\tests\setup.d.ts`
**Language:** typescript | **Lines:** 11

**Purpose:** General module

### `vscode-extension\out\watchers\fileWatcher.d.ts`
**Language:** typescript | **Lines:** 77

**Purpose:** General module

**Responsibilities:**
- `FileWatcher`: React component

**Classes:**
- `FileWatcher`: 

**Key Imports:** vscode

**Depends on:** ../events/eventBus, ../backend/backendManager

### `vscode-extension\out\views\agentsTreeProvider.js`
**Language:** javascript | **Lines:** 268

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `AgentsTreeProvider`: React component
- `AgentTreeItem`: React component

**Classes:**
- `AgentsTreeProvider`: 
- `AgentTreeItem`: 

### `vscode-extension\out\extension.js`
**Language:** javascript | **Lines:** 132

**Purpose:** General module

**Functions:**
- `activate()`
- `deactivate()`

### `backend\rulesets\gdpr-sample.yaml`
**Language:** yaml | **Lines:** 70

**Purpose:** General module

**📋 Compliance Notes:**
- pii_handling

### `vscode-extension\out\views\chatViewProvider.d.ts`
**Language:** typescript | **Lines:** 31

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `ChatViewProvider`: React component

**Classes:**
- `ChatViewProvider`: 

**Key Imports:** vscode

**Depends on:** ../backend/backendManager, ../events/eventBus

**📋 Compliance Notes:**
- logging_sensitive

### `.github\workflows\ci.yml`
**Language:** yaml | **Lines:** 197

**Purpose:** General module

### `vscode-extension\out\events\eventBus.d.ts`
**Language:** typescript | **Lines:** 99

**Purpose:** General module

**Responsibilities:**
- `EventBus`: React component

**Classes:**
- `EventBus`: 

**Key Imports:** vscode

### `vscode-extension\out\watchers\fileWatcher.js`
**Language:** javascript | **Lines:** 362

**Purpose:** General module

**Responsibilities:**
- `FileWatcher`: React component

**Classes:**
- `FileWatcher`: 

### `vscode-extension\out\views\chatViewProvider.js`
**Language:** javascript | **Lines:** 880

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `ChatViewProvider`: React component

**Classes:**
- `ChatViewProvider`: 

**Functions:**
- `setConnected()`
- `setAgent()`
- `addMessage()`
- `addMessageToDOM()`
- `formatMessage()`
- `addCopyButton()`
- `startStreaming()`
- `appendStreamChunk()`
- `endStreaming()`
- `showError()`
- ... and 4 more functions

**📋 Compliance Notes:**
- pii_handling
- logging_sensitive

### `vscode-extension\out\tests\eventBus.test.js`
**Language:** javascript | **Lines:** 169

**Purpose:** Test File

**Responsibilities:**
- Unit/integration tests

### `vscode-extension\out\commands\commandHandler.js`
**Language:** javascript | **Lines:** 235

**Purpose:** Request Handler

**Responsibilities:**
- Handles incoming requests
- `CommandHandler`: Request handling

**Classes:**
- `CommandHandler`: 

**Functions:**
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- ... and 6 more functions

### `demo\sample_project\config.yaml`
**Language:** yaml | **Lines:** 20

**Purpose:** Configuration File

**Responsibilities:**
- Application settings and constants

### `vscode-extension\jest.config.js`
**Language:** javascript | **Lines:** 64

**Purpose:** Configuration File

**Responsibilities:**
- Application settings and constants

### `vscode-extension\out\views\historyTreeProvider.d.ts`
**Language:** typescript | **Lines:** 53

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `HistoryTreeProvider`: React component
- `HistoryTreeItem`: React component

**Classes:**
- `HistoryTreeProvider`: 
- `HistoryTreeItem`: 

**Key Imports:** vscode

**Depends on:** ../events/eventBus

### `vscode-extension\out\views\historyTreeProvider.js`
**Language:** javascript | **Lines:** 308

**Purpose:** Page Component

**Responsibilities:**
- Full page/route component
- `HistoryTreeProvider`: React component
- `HistoryTreeItem`: React component
- `SessionTreeItem`: React component
- `EmptyHistoryItem`: React component

**Classes:**
- `HistoryTreeProvider`: 
- `HistoryTreeItem`: 
- `SessionTreeItem`: 
- `EmptyHistoryItem`: 

### `vscode-extension\out\tests\eventBus.test.d.ts`
**Language:** typescript | **Lines:** 10

**Purpose:** Test File

**Responsibilities:**
- Unit/integration tests
