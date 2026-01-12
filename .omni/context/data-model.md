# Data Model

> Last updated: 2026-01-10T15:19:07.625349

Classes and data-bearing modules inferred from the codebase.

## `backend\core\timeout.py`

**Classes:**
- `TimeoutConfig` — Configuration for timeout behavior.
- `TimeoutResult` — Result from a timed operation.
- `TimeoutTracker` — Tracks elapsed time during timeout context.
- `TimeoutBudget` — Manages timeout budget across multiple operations.

Useful for workflows where total time is limited and
each step consu...
- `StepContext` — Context for a budget step.

**Constants / exports:**
- `T`
- `DEFAULT_TIMEOUT_CONFIG`

## `backend\core\interfaces\workflow.py`

**Classes:**
- `WorkflowStatus` — Workflow execution states.
- `StepStatus` — Individual step execution states.
- `WorkflowStep` — A single step in a workflow.

Attributes:
    id: Unique step identifier
    name: Human-readable step name
    descript...
- `StepResult` — Result of executing a workflow step.
- `WorkflowContext` — Runtime context for workflow execution.

Attributes:
    workflow_id: Unique workflow run identifier
    inputs: Initial...
- `WorkflowMetadata` — Metadata describing a workflow.
- `WorkflowResult` — Final result of a workflow execution.
- `WorkflowBase` — Abstract base class for workflows.

Workflows define multi-step processes using LangChain/LangGraph.
They orchestrate ag...

**Constants / exports:**
- `T`
- `PENDING`
- `RUNNING`
- `PAUSED`
- `COMPLETED`
- `FAILED`
- `CANCELLED`
- `PENDING`
- `RUNNING`
- `COMPLETED`

## `backend\tests\agents\test_context_persistence.py`

**Classes:**
- `TestDetailedFileSummary` — Tests for DetailedFileSummary dataclass.
- `TestProjectStructure` — Tests for ProjectStructure with unified files dict.
- `TestContextAgentPersistence` — Tests for ContextAgent persistence functionality.
- `TestContextAgentIntegration` — Integration tests for ContextAgent with unified summaries.
- `TestVersionTracking` — Tests for ProjectStructure version tracking.

## `backend\agents\base_agents.py`

**Classes:**
- `AssistantAgent` — General-purpose assistant agent.

Provides conversational AI capabilities with tool use support.
- `CodeAgent` — Specialized agent for code-related tasks.

Handles code generation, review, and analysis.
- `PlannerAgent` — Planning and orchestration agent.

Breaks down complex tasks and coordinates other agents.

## `backend\core\interfaces\llm.py`

**Classes:**
- `LLMRole` — Message roles for chat completions.
- `LLMMessage` — A single message in a conversation.
- `LLMConfig` — Configuration for LLM requests.
- `LLMUsage` — Token usage statistics.
- `LLMToolCall` — A tool/function call from the LLM.
- `LLMResponse` — Response from an LLM completion request.
- `LLMProvider` — Abstract base class for LLM providers.

All LLM adapters (OpenAI, Anthropic, local LLMs, etc.) must implement this inter...
- `LLMProviderError` — Base exception for LLM provider errors.
- `LLMRateLimitError` — Raised when rate limited by the provider.
- `LLMAuthenticationError` — Raised when authentication fails.
- `LLMContextLengthError` — Raised when the context length is exceeded.

**Constants / exports:**
- `SYSTEM`
- `USER`
- `ASSISTANT`
- `FUNCTION`
- `TOOL`

## `vscode-extension\out\events\eventBus.js`

**Classes:**
- `EventBus` — 

## `backend\adapters\llm\factory.py`

**Classes:**
- `LLMFactory` — Factory for creating LLM providers.

Supports dynamic provider selection based on configuration.

Example:
    ```python...

## `backend\agents\loader.py`

**Classes:**
- `AgentRegistry` — Registry for agent plugins.

Maintains a catalog of available agents and their metadata.
Supports enabling/disabling age...
- `AgentLoader` — Dynamic agent plugin loader.

Loads agent plugins from:
- Built-in agents directory
- Custom plugin directories
- Python...

## `backend\core\state.py`

**Classes:**
- `StateVersion` — Tracks version information for state changes.
- `ThreadSafeState` — Thread-safe wrapper for mutable state in async contexts.

Provides:
- Automatic locking for all operations
- Version tra...
- `ReadContext` — Context manager for reading state.
- `WriteContext` — Context manager for writing state.
- `SharedContext` — Typed shared context for agent communication.

Replaces the untyped `shared_state: dict` in AgentContext with
explicit, ...
- `ThreadSafeSharedContext` — Thread-safe wrapper for SharedContext.

Provides field-level locking for efficient concurrent access.

**Constants / exports:**
- `T`

## `backend\core\dependencies.py`

**Classes:**
- `DependencyError` — Base exception for dependency-related errors.
- `MissingDependencyError` — Raised when a required dependency is missing.
- `CircularDependencyError` — Raised when circular dependencies are detected.
- `DependencyValidationError` — Raised when dependency validation fails.
- `DependencyStatus` — Status of a dependency.
- `DependencyInfo` — Information about a single dependency.
- `DependencyGraph` — Represents the dependency graph between agents.

Provides methods for:
- Validating all dependencies are satisfied
- Det...

**Constants / exports:**
- `SATISFIED`
- `MISSING`
- `UNAVAILABLE`

## `backend\observability.py`

**Classes:**
- `CorrelationContext` — Thread-local storage for correlation IDs.

Allows tracing a request across all agent calls.
- `LogContext` — Context attached to log entries.
- `StructuredLogger` — Logger with structured context and correlation IDs.

Usage:
    log = StructuredLogger("agent.security")
    log.info("S...
- `TimingMetric` — A single timing measurement.
- `MetricsCollector` — Collects and aggregates metrics.

Thread-safe collector for timing and counter metrics.
- `AgentSpan` — Represents a traced span for agent execution.

Use this to wrap agent.process() calls for full observability.
- `RequestTrace` — Traces an entire request through all agents.

Usage:
    trace = RequestTrace()
    
    async with trace.span("context_...

**Constants / exports:**
- `T`
- `METRIC_NAMES`

## `backend\agents\context_agent.py`

**Classes:**
- `DetailedFileSummary` — Detailed summary of a single file - the UNIFIED format.

This replaces the old short summaries (~200 chars) with compreh...
- `ContextAgentConfig` — Configuration for Context Agent.
- `ProjectStructure` — Persistent knowledge about the project structure.

UNIFIED APPROACH: Uses DetailedFileSummary for ALL files instead of
s...
- `ImportantFact` — An important fact extracted from conversation.
- `CurrentTask` — Tracks the current task being worked on.
- `ContextAgent` — Agent that manages global session context.

This agent is responsible for:
1. Extracting important information from ever...

**Constants / exports:**
- `FILE_PATTERN`
- `ERROR_PATTERN`
- `SECURITY_PATTERN`
- `COMPLIANCE_PATTERN`
- `TASK_PATTERNS`
- `BACKEND_PATTERNS`
- `FRONTEND_PATTERNS`
- `DATABASE_PATTERNS`

## `backend\core\interfaces\agent.py`

**Classes:**
- `MessageType` — Types of messages agents can send/receive.
- `AgentStatus` — Agent lifecycle states.
- `AgentMessage` — A message exchanged between agents or with the user.

Attributes:
    id: Unique message identifier
    type: Message ty...
- `AgentTool` — A tool that an agent can use.

Attributes:
    name: Tool name (used for invocation)
    description: Human-readable des...
- `AgentContext` — Runtime context provided to agents during execution.

Attributes:
    session_id: Current session identifier
    workspa...
- `AgentCapability` — Describes a capability an agent provides.
- `AgentConfig` — Configuration for creating/configuring an agent.

Attributes:
    name: Agent name
    description: What this agent does...
- `AgentMetadata` — Metadata describing an agent.

Attributes:
    id: Unique agent identifier
    name: Human-readable name
    description...
- `AgentBase` — Abstract base class for all agents.

Agents are loaded as plugins and orchestrated by AutoGen.
Each agent has a specific...

**Constants / exports:**
- `TEXT`
- `TOOL_CALL`
- `TOOL_RESULT`
- `SYSTEM`
- `ERROR`
- `STATUS`
- `IDLE`
- `THINKING`
- `EXECUTING`
- `WAITING`

## `backend\tests\core\test_state.py`

**Classes:**
- `TestStateVersion` — Tests for StateVersion.
- `TestThreadSafeState` — Tests for ThreadSafeState wrapper.
- `TestSharedContext` — Tests for SharedContext dataclass.
- `TestThreadSafeSharedContext` — Tests for ThreadSafeSharedContext.
- `TestConcurrencyStress` — Stress tests for concurrency safety.

## `backend\tests\core\test_retry.py`

**Classes:**
- `TestRetryConfig` — Tests for RetryConfig.
- `TestShouldRetry` — Tests for should_retry function.
- `TestRetryAsync` — Tests for retry_async function.
- `TestWithRetryDecorator` — Tests for with_retry decorator.
- `TestRetryContext` — Tests for RetryContext context manager.
- `TestWithTimeoutAndRetry` — Tests for with_timeout_and_retry function.
- `TestPresetConfigs` — Tests for preset configurations.

## `vscode-extension\out\backend\backendManager.d.ts`

**Classes:**
- `BackendManager` — 

## `backend\core\connection_pool.py`

**Classes:**
- `ConnectionState` — State of a pooled connection.
- `PoolConfig` — Configuration for connection pool.
- `PoolStats` — Statistics for a connection pool.
- `PooledConnection` — Wrapper for a pooled connection.
- `ConnectionFactory` — Abstract factory for creating connections.
- `PoolError` — Base exception for pool errors.
- `PoolExhaustedError` — Raised when pool is exhausted and timeout reached.
- `PoolClosedError` — Raised when trying to use a closed pool.
- `ConnectionPool` — Async connection pool with health checks and metrics.

Example:
    ```python
    class VectorDBFactory(ConnectionFactor...
- `SimpleConnectionFactory` — Simple connection factory using callables.

Example:
    factory = SimpleConnectionFactory(
        create_fn=lambda: My...

**Constants / exports:**
- `T`
- `IDLE`
- `IN_USE`
- `CLOSING`
- `CLOSED`

## `backend\adapters\vectordb\chroma_adapter.py`

**Classes:**
- `ChromaAdapter` — ChromaDB vector database adapter.

Supports persistent and in-memory modes.

Example:
    ```python
    # Persistent mod...

## `backend\core\retry.py`

**Classes:**
- `RetryConfig` — Configuration for retry behavior.
- `RetryContext` — Context manager for retry operations with state tracking.

Useful when you need to track retry state across operations.
...

**Constants / exports:**
- `T`
- `RETRY_FAST`
- `RETRY_STANDARD`
- `RETRY_PATIENT`

## `backend\tests\core\test_timeout.py`

**Classes:**
- `TestTimeoutConfig` — Tests for TimeoutConfig.
- `TestTimeoutContext` — Tests for timeout_context.
- `TestWithTimeoutDecorator` — Tests for with_timeout decorator.
- `TestRunWithTimeout` — Tests for run_with_timeout function.
- `TestTimeoutBudget` — Tests for TimeoutBudget.
- `TestTimeoutTracker` — Tests for TimeoutTracker.
- `TestDefaultConfig` — Tests for default timeout configuration.

## `backend\adapters\llm\openai_adapter.py`

**Classes:**
- `OpenAIAdapter` — OpenAI LLM adapter supporting GPT-4, GPT-3.5, and embeddings.

Example:
    ```python
    adapter = OpenAIAdapter(
     ...

## `vscode-extension\out\views\agentsTreeProvider.d.ts`

**Classes:**
- `AgentsTreeProvider` — 
- `AgentTreeItem` — 

## `vscode-extension\src\views\chatViewProvider.ts`

**Classes:**
- `ChatViewProvider` — 

## `vscode-extension\out\commands\commandHandler.d.ts`

**Classes:**
- `CommandHandler` — 

## `vscode-extension\src\events\eventBus.ts`

**Classes:**
- `EventBus` — 

## `backend\rag\service.py`

**Classes:**
- `RAGConfig` — RAG configuration.
- `ContextVersion` — Tracks version of indexed content.
- `RAGResult` — Result from RAG query.
- `RAGService` — RAG Service using LlamaIndex for orchestration.

This service is:
- Completely optional (disabled by default)
- Safe if ...

**Constants / exports:**
- `LLAMAINDEX_AVAILABLE`
- `LLAMAINDEX_AVAILABLE`

## `vscode-extension\out\backend\websocketClient.d.ts`

**Classes:**
- `WebSocketClient` — 

## `vscode-extension\src\watchers\fileWatcher.ts`

**Classes:**
- `FileWatcher` — 

## `backend\core\interfaces\vectordb.py`

**Classes:**
- `DistanceMetric` — Distance metrics for similarity search.
- `Document` — A document to be stored in the vector database.

Attributes:
    id: Unique identifier (auto-generated if not provided)
...
- `SearchResult` — A single search result from the vector database.

Attributes:
    document: The matched document
    score: Similarity s...
- `CollectionConfig` — Configuration for creating a collection.
- `SearchConfig` — Configuration for search queries.
- `VectorDBProvider` — Abstract base class for vector database providers.

All vector DB adapters (Qdrant, Chroma, FAISS, etc.) must implement ...
- `VectorDBError` — Base exception for vector database errors.
- `CollectionNotFoundError` — Raised when a collection does not exist.
- `CollectionExistsError` — Raised when trying to create a collection that already exists.

**Constants / exports:**
- `COSINE`
- `EUCLIDEAN`
- `DOT_PRODUCT`

## `backend\integrations\file_analyzer.py`

**Classes:**
- `ClassInfo` — Information about a class.
- `FunctionInfo` — Information about a function.
- `FileAnalysis` — Complete analysis of a source file.
- `FileAnalyzer` — Analyzes source files to generate detailed summaries.

Example:
    ```python
    analyzer = FileAnalyzer()
    
    # A...

**Constants / exports:**
- `SECURITY_PATTERNS`
- `COMPLIANCE_PATTERNS`

## `backend\agents\coding_agent.py`

**Classes:**
- `PatchValidationError` — Raised when a patch fails validation.
- `PatchType` — Types of code changes.
- `PatchResult` — Result of code generation - always a patch.
- `CodingAgentConfig` — Configuration for coding agent.
- `CodingAgent` — Coding agent that produces patches only.

This agent:
- NEVER writes files - only produces unified diffs
- Validates all...

**Constants / exports:**
- `FEATURE`
- `BUGFIX`
- `REFACTOR`
- `TEST`
- `DOCS`
- `PROMPT_TEMPLATE`
- `PROMPT_TEMPLATE_WITH_CONTEXT`

## `backend\tests\agents\test_registry.py`

**Classes:**
- `TestAgent` — A simple test agent for registry tests.
- `AnotherTestAgent` — Another test agent for registry tests.
- `TestAgentRegistryRegister` — Tests for agent registration functionality.
- `TestAgentRegistryGet` — Tests for retrieving agents from registry.
- `TestAgentRegistryUnregister` — Tests for unregistering agents.
- `TestAgentRegistryEnableDisable` — Tests for enabling/disabling agents.
- `TestAgentRegistryInfo` — Tests for getting agent information.

## `backend\agents\workflow.py`

**Classes:**
- `WorkflowResult` — Result from a complete workflow execution.
- `WorkflowOrchestrator` — Orchestrates the full analysis workflow.

Flow:
1. CONTEXT AGENT: Analyze project structure, create summary
2. RAG AGENT...

## `backend\tests\test_observability.py`

**Classes:**
- `TestCorrelationContext` — Tests for correlation ID management.
- `TestLogContext` — Tests for LogContext.
- `TestStructuredLogger` — Tests for StructuredLogger.
- `TestMetricsCollector` — Tests for MetricsCollector.
- `TestTimedOperation` — Tests for timed_operation context managers.
- `TestTracedDecorator` — Tests for traced decorator.
- `TestAgentSpan` — Tests for AgentSpan.
- `TestRequestTrace` — Tests for RequestTrace.

## `vscode-extension\out\watchers\fileWatcher.d.ts`

**Classes:**
- `FileWatcher` — 

## `benchmark\run_benchmark.py`

**Classes:**
- `TokenEstimate` — Stima dei token per un testo.
- `TaskResult` — Risultato di un singolo task.
- `BenchmarkReport` — Report completo del benchmark.
- `BenchmarkRunner` — Esegue il benchmark e raccoglie metriche.

## `vscode-extension\out\views\agentsTreeProvider.js`

**Classes:**
- `AgentsTreeProvider` — 
- `AgentTreeItem` — 

## `backend\adapters\llm\local_adapter.py`

**Classes:**
- `LocalLLMAdapter` — Local LLM adapter supporting LM Studio, Ollama, and llama.cpp.

All these tools provide OpenAI-compatible APIs, so we ca...

## `backend\autogen\runtime.py`

**Classes:**
- `AutoGenConfig` — Configuration for AutoGen runtime.
- `GroupChatResult` — Result of a group chat session.
- `OmniAgentWrapper` — Wraps an OMNI agent as an AutoGen-compatible agent.

This wrapper allows existing OMNI agents to participate
in AutoGen ...
- `AutoGenRuntime` — AutoGen Multi-Agent Runtime.

This runtime:
- Is completely optional (disabled by default)
- Wraps existing OMNI agents ...

**Constants / exports:**
- `AUTOGEN_AVAILABLE`
- `AUTOGEN_AVAILABLE`

## `backend\adapters\vectordb\base.py`

**Classes:**
- `BaseVectorDBAdapter` — Base class for vector database adapters with common functionality.

Provides:
- Configuration management
- Connection ha...

## `backend\config\settings.py`

**Classes:**
- `ServerSettings` — WebSocket server settings.
- `OpenAISettings` — OpenAI provider settings.
- `AnthropicSettings` — Anthropic provider settings.
- `LocalLLMSettings` — Local LLM provider settings.
- `LLMSettings` — LLM configuration.
- `QdrantSettings` — Qdrant settings.
- `ChromaSettings` — ChromaDB settings.
- `FAISSSettings` — FAISS settings.
- `VectorDBSettings` — Vector database configuration.
- `RAGSettings` — RAG configuration.
- `AgentSettings` — Agent configuration.
- `WorkflowSettings` — Workflow configuration.
- `LoggingSettings` — Logging configuration.
- `SecuritySettings` — Security configuration.
- `FeatureFlags` — Feature flags.
- `Settings` — Main settings class.

Loads configuration from:
1. Default values
2. YAML config file
3. Environment variables (OMNI_ pr...

## `backend\agents\orchestrator.py`

**Classes:**
- `AgentOrchestrator` — Orchestrates multi-agent conversations and workflows.

Supports various patterns:
- Sequential: Agents respond in order
...

## `backend\agents\rag_agent.py`

**Classes:**
- `RAGAgentConfig` — Configuration for RAG Agent.
- `FileSummary` — Compact file summary for token-efficient retrieval.
Instead of returning 50k of raw code, we return ~200 chars of summar...
- `RAGQueryResult` — Result from a RAG query.
- `RAGAgent` — Agent that intelligently manages RAG operations.

Unlike the passive RAGService, this agent:
1. DECIDES which domains to...
- `RAGService` — 
- `RAGResult` — 
- `RAGConfig` — 

**Constants / exports:**
- `RAG_SERVICE_AVAILABLE`
- `DOMAIN_PATTERNS`
- `NOISE_WORDS`
- `RAG_SERVICE_AVAILABLE`

## `backend\tests\conftest.py`

**Classes:**
- `FakeLLMProvider` — Fake LLM provider for testing purposes.

This provider returns predictable, configurable responses
without making any ex...
- `FakeVectorStore` — Fake vector store for testing purposes.

This provider stores documents in memory and provides
basic similarity search u...

## `backend\config\loader.py`

**Classes:**
- `ConfigLoader` — Loads configuration from YAML files with environment variable support.

Features:
- Environment variable substitution: $...

**Constants / exports:**
- `ENV_PATTERN`

## `backend\tests\core\test_dependencies.py`

**Classes:**
- `MockAgent` — Mock agent for testing.
- `TestDependencyGraph` — Tests for DependencyGraph.
- `TestDependencyValidation` — Tests for dependency validation.
- `TestCircularDependencies` — Tests for circular dependency detection.
- `TestTopologicalSort` — Tests for initialization order.
- `TestTransitiveDependencies` — Tests for transitive dependency resolution.
- `TestDependencyVisualization` — Tests for dependency visualization.
- `TestDependencyInfo` — Tests for detailed dependency info.
- `TestConvenienceFunctions` — Tests for convenience functions.
- `TestRealAgents` — Tests with real OMNI agents.

## `vscode-extension\out\views\chatViewProvider.d.ts`

**Classes:**
- `ChatViewProvider` — 

## `vscode-extension\out\backend\websocketClient.js`

**Classes:**
- `WebSocketClient` — 

## `backend\adapters\llm\anthropic_adapter.py`

**Classes:**
- `AnthropicAdapter` — Anthropic Claude adapter.

Example:
    ```python
    adapter = AnthropicAdapter(
        api_key="sk-ant-...",
        ...

## `vscode-extension\out\events\eventBus.d.ts`

**Classes:**
- `EventBus` — 

## `backend\integrations\copilot_integration.py`

**Classes:**
- `FileSummary` — Detailed summary of a single file for senior developers.
- `ProjectContext` — Complete project context for Copilot.
- `CopilotIntegration` — Generates and maintains files for Copilot integration.

Creates a .omni/ folder structure:
```
.omni/
├── context/
│   ├...

## `backend\utils\gitignore.py`

**Constants / exports:**
- `_DEFAULT_IGNORE_PATTERNS`

## `backend\adapters\llm\base.py`

**Classes:**
- `BaseLLMAdapter` — Base class for LLM adapters with common functionality.

Provides:
- Configuration management
- Request/response logging
...

## `backend\core\exceptions.py`

**Classes:**
- `ErrorContext` — Additional context for debugging errors.

Attributes:
    agent_id: ID of the agent that raised the error
    operation:...
- `OMNIError` — Base exception for all OMNI errors.

All custom exceptions inherit from this class, allowing:
- Catching all OMNI errors...
- `AgentError` — Base class for agent-related errors.
- `AgentTimeoutError` — Raised when an agent operation times out.

This is a RECOVERABLE error - the operation can be retried.

Example:
    try...
- `AgentValidationError` — Raised when input validation fails.

This is NOT recoverable without fixing the input.

Example:
    if not message.cont...
- `AgentConfigurationError` — Raised when agent configuration is invalid.

This is NOT recoverable without fixing configuration.

Example:
    if not ...
- `AgentNotFoundError` — Raised when a requested agent is not registered.

Example:
    agent = registry.get("unknown_agent")
    if not agent:
 ...
- `AgentFatalError` — Raised when an unrecoverable error occurs.

This indicates the agent should be stopped/restarted.

Example:
    try:
   ...
- `AgentDependencyError` — Raised when a required agent dependency is missing.

Example:
    if not self._context_agent:
        raise AgentDepende...
- `LLMError` — Base class for LLM provider errors.
- `LLMTimeoutError` — Raised when LLM call times out.

This is RECOVERABLE - can retry with backoff.
- `LLMRateLimitError` — Raised when LLM rate limit is hit.

This is RECOVERABLE - retry after delay.

Attributes:
    retry_after_seconds: Sugge...
- `LLMAuthenticationError` — Raised when LLM authentication fails.

This is NOT recoverable without fixing credentials.
- `LLMResponseError` — Raised when LLM returns invalid response.

This is RECOVERABLE - can retry.
- `VectorDBError` — Base class for vector database errors.
- `VectorDBConnectionError` — Raised when VectorDB connection fails.

This is RECOVERABLE - can retry connection.
- `VectorDBQueryError` — Raised when VectorDB query fails.

This is RECOVERABLE - can retry query.
- `VectorDBIndexError` — Raised when VectorDB indexing fails.

This is RECOVERABLE - can retry indexing.
- `RAGError` — Base class for RAG service errors.
- `RAGIndexError` — Raised when RAG indexing fails.

## `backend\adapters\vectordb\qdrant_adapter.py`

**Classes:**
- `QdrantAdapter` — Qdrant vector database adapter.

Supports both local (in-memory/disk) and cloud Qdrant instances.

Example:
    ```pytho...

## `vscode-extension\out\watchers\fileWatcher.js`

**Classes:**
- `FileWatcher` — 

## `demo\sample_project\auth.py`

**Classes:**
- `UserSession` — User session manager.

**Constants / exports:**
- `API_KEY`
- `DATABASE_URL`

## `vscode-extension\out\views\chatViewProvider.js`

**Classes:**
- `ChatViewProvider` — 

## `backend\tests\core\test_exceptions.py`

**Classes:**
- `TestErrorContext` — Tests for ErrorContext dataclass.
- `TestOMNIError` — Tests for base OMNIError class.
- `TestAgentErrors` — Tests for agent-related exceptions.
- `TestLLMErrors` — Tests for LLM-related exceptions.
- `TestVectorDBErrors` — Tests for VectorDB-related exceptions.
- `TestWorkflowErrors` — Tests for workflow-related exceptions.
- `TestHelperFunctions` — Tests for helper functions.
- `TestExceptionCatching` — Tests for catching exceptions at different levels.

## `backend\tests\core\test_llm_adapter.py`

**Classes:**
- `TestFakeLLMProviderHealth` — Tests for LLM provider health check functionality.
- `TestFakeLLMProviderComplete` — Tests for LLM provider text generation (complete) functionality.
- `TestFakeLLMProviderStream` — Tests for LLM provider streaming functionality.
- `TestFakeLLMProviderEmbed` — Tests for LLM provider embedding functionality.

## `backend\agents\compliance_agent.py`

**Classes:**
- `ComplianceSeverity` — Compliance finding severity.
- `ComplianceStatus` — Compliance check status.
- `ComplianceRule` — A single compliance rule.

Rules are loaded from external files and define what to check.
- `ComplianceFinding` — A compliance finding from rule evaluation.
- `ComplianceAgentConfig` — Configuration for compliance agent.
- `ComplianceAgent` — Compliance checking agent using external rulesets.

This agent:
- Loads rules from JSON/YAML files (no hardcoded regulat...

**Constants / exports:**
- `CRITICAL`
- `MAJOR`
- `MINOR`
- `ADVISORY`
- `PASS`
- `FAIL`
- `WARNING`
- `NOT_APPLICABLE`
- `MANUAL_REVIEW`

## `test_omni_simple.py`

**Classes:**
- `Severity` — 
- `SecurityFinding` — 
- `ComplianceFinding` — 
- `SimpleSecurityChecker` — Security checker semplificato per demo.
- `SimpleComplianceChecker` — Compliance checker semplificato per demo.

**Constants / exports:**
- `CRITICAL`
- `HIGH`
- `MEDIUM`
- `LOW`
- `INFO`
- `PATTERNS`

## `vscode-extension\src\commands\commandHandler.ts`

**Classes:**
- `CommandHandler` — 

## `backend\tests\core\test_connection_pool.py`

**Classes:**
- `MockConnection` — Mock connection for testing.
- `MockConnectionFactory` — Mock factory for testing.
- `TestPooledConnection` — Tests for PooledConnection wrapper.
- `TestPoolConfig` — Tests for PoolConfig.
- `TestPoolStats` — Tests for PoolStats.
- `TestConnectionPool` — Tests for ConnectionPool.
- `TestSimpleConnectionFactory` — Tests for SimpleConnectionFactory.
- `TestCreatePool` — Tests for create_pool convenience function.
- `TestPoolHealthChecks` — Tests for health check behavior.

## `backend\tests\core\test_vectordb_adapter.py`

**Classes:**
- `TestFakeVectorStoreHealth` — Tests for vector store health check functionality.
- `TestFakeVectorStoreCollections` — Tests for vector store collection management.
- `TestFakeVectorStoreDocuments` — Tests for vector store document operations.
- `TestFakeVectorStoreSearch` — Tests for vector store search functionality.

## `backend\agents\security_agent.py`

**Classes:**
- `Severity` — Security finding severity levels.
- `FindingCategory` — Categories of security findings.
- `SecurityFinding` — A single security finding.

Structured output format for security issues.
- `SecurityAgentConfig` — Configuration for security agent.
- `SecurityAgent` — Read-only security analysis agent.

This agent:
- NEVER writes files
- Runs Semgrep for static analysis
- Optionally use...

**Constants / exports:**
- `CRITICAL`
- `HIGH`
- `MEDIUM`
- `LOW`
- `INFO`
- `INJECTION`
- `XSS`
- `AUTHENTICATION`
- `AUTHORIZATION`
- `CRYPTOGRAPHY`

## `vscode-extension\out\commands\commandHandler.js`

**Classes:**
- `CommandHandler` — 

## `vscode-extension\src\backend\websocketClient.ts`

**Classes:**
- `WebSocketClient` — 

## `backend\server\websocket_handler.py`

**Classes:**
- `WebSocketHandler` — Handles WebSocket connections from VS Code extension.

Routes messages to appropriate handlers and manages
the agent orc...

## `backend\adapters\vectordb\faiss_adapter.py`

**Classes:**
- `FAISSCollection` — Internal representation of a FAISS collection.
- `FAISSAdapter` — FAISS vector database adapter.

Supports in-memory and disk-persisted indexes.

Example:
    ```python
    # In-memory m...

## `backend\adapters\vectordb\factory.py`

**Classes:**
- `VectorDBFactory` — Factory for creating vector database providers.

Example:
    ```python
    # Create from config
    db = VectorDBFactor...

## `vscode-extension\out\backend\backendManager.js`

**Classes:**
- `BackendManager` — 

## `vscode-extension\src\views\historyTreeProvider.ts`

**Classes:**
- `HistoryTreeProvider` — 
- `HistoryTreeItem` — 
- `SessionTreeItem` — 
- `EmptyHistoryItem` — 

## `vscode-extension\src\views\agentsTreeProvider.ts`

**Classes:**
- `AgentsTreeProvider` — 
- `AgentTreeItem` — 

## `demo\demo_mode.py`

**Classes:**
- `DemoConfig` — Demo configuration.

## `backend\server\message_types.py`

**Classes:**
- `MessageType` — Types of messages exchanged between frontend and backend.
- `Message` — A message in the communication protocol.

Attributes:
    type: Message type
    data: Message payload
    id: Optional ...

**Constants / exports:**
- `CHAT_MESSAGE`
- `GET_AGENTS`
- `SELECT_AGENT`
- `GET_HISTORY`
- `CANCEL`
- `ANALYZE_CODE`
- `SCAN_WORKSPACE`
- `CHAT_RESPONSE`
- `STREAM_START`
- `STREAM_CHUNK`

## `vscode-extension\out\views\historyTreeProvider.d.ts`

**Classes:**
- `HistoryTreeProvider` — 
- `HistoryTreeItem` — 

## `vscode-extension\src\backend\backendManager.ts`

**Classes:**
- `BackendManager` — 

## `vscode-extension\out\views\historyTreeProvider.js`

**Classes:**
- `HistoryTreeProvider` — 
- `HistoryTreeItem` — 
- `SessionTreeItem` — 
- `EmptyHistoryItem` — 
