# Interfaces and APIs

> Last updated: 2026-01-10T15:19:07.624372

Functions, classes, and modules that look like entrypoints or public surfaces.

## `backend\core\timeout.py`
Timeout Management

**Classes:**
- `TimeoutConfig` (to_dict)
- `TimeoutResult` ()
- `TimeoutTracker` (__init__, elapsed_seconds, remaining_seconds, mark_timeout, mark_complete)
- `TimeoutBudget` (__init__, elapsed_seconds, remaining_seconds, is_expired, step ...)
- `StepContext` (elapsed, remaining)

## `backend\core\interfaces\workflow.py`
Workflow Interface

**Classes:**
- `WorkflowStatus` ()
- `StepStatus` ()
- `WorkflowStep` ()
- `StepResult` ()
- `WorkflowContext` (get_input, get_state, set_state, get_step_output)
- `WorkflowMetadata` ()
- `WorkflowResult` (is_success)
- `WorkflowBase` (__init__, metadata, status, steps, current_step ...)

## `backend\tests\agents\test_context_persistence.py`
Tests for Context Agent persistence and unified DetailedFileSummary.

**Classes:**
- `TestDetailedFileSummary` (test_to_dict_serialization, test_from_dict_deserialization, test_to_compact_string, test_to_markdown)
- `TestProjectStructure` (test_to_dict_with_files, test_from_dict_with_files, test_legacy_format_migration, test_get_file, test_search_by_class ...)
- `TestContextAgentPersistence` (test_save_and_load_project_structure, test_no_load_when_persist_disabled, test_set_workspace_with_auto_load)
- `TestContextAgentIntegration` (test_get_file_summary_returns_detailed, test_project_context_uses_detailed_files)
- `TestVersionTracking` (test_version_increments_on_change, test_change_history_recorded, test_change_history_limited_to_50, test_version_persisted_to_json, test_version_loaded_from_json ...)

## `backend\agents\base_agents.py`
Base Agent Implementations

**Classes:**
- `AssistantAgent` (__init__, metadata, set_llm, get_system_prompt, process)
- `CodeAgent` (__init__, metadata, set_llm, get_system_prompt, process)
- `PlannerAgent` (__init__, metadata, set_llm, get_system_prompt, process)

## `backend\core\interfaces\llm.py`
LLM Provider Interface

**Classes:**
- `LLMRole` ()
- `LLMMessage` ()
- `LLMConfig` ()
- `LLMUsage` ()
- `LLMToolCall` ()
- `LLMResponse` ()
- `LLMProvider` (provider_name, is_available, complete, stream, embed ...)
- `LLMProviderError` (__init__)
- `LLMRateLimitError` ()
- `LLMAuthenticationError` ()

## `vscode-extension\out\events\eventBus.js`
General module

**Classes:**
- `EventBus` ()

**Functions:**
- `wrapper()`
- `dispose()`

## `backend\adapters\llm\factory.py`
LLM Factory

**Classes:**
- `LLMFactory` (register, create, from_config, list_providers, create_with_health_check)

## `backend\agents\loader.py`
Agent Loader and Registry

**Classes:**
- `AgentRegistry` (__init__, register, unregister, enable, disable ...)
- `AgentLoader` (__init__, load_builtin_agents, load_from_directory, load_file, load_module ...)

## `backend\core\state.py`
Thread-Safe State Management

**Classes:**
- `StateVersion` (increment)
- `ThreadSafeState` (__init__, version, read, write, get ...)
- `ReadContext` (__init__, __aenter__, __aexit__)
- `WriteContext` (__init__, __aenter__, __aexit__)
- `SharedContext` (to_dict)
- `ThreadSafeSharedContext` (__init__, version, get_project_structure, set_project_structure, add_security_finding ...)

## `vscode-extension\src\extension.ts`
General module

**Functions:**
- `activate()`
- `deactivate()`

## `backend\core\dependencies.py`
Agent Dependency Management

**Classes:**
- `DependencyError` ()
- `MissingDependencyError` (__init__)
- `CircularDependencyError` (__init__)
- `DependencyValidationError` (__init__)
- `DependencyStatus` ()
- `DependencyInfo` ()
- `DependencyGraph` (add_agent, add_agent_metadata, get_dependencies, get_dependents, get_provides ...)

## `backend\observability.py`
Observability Module

**Classes:**
- `CorrelationContext` (get, set, generate, push, pop ...)
- `LogContext` (to_dict)
- `StructuredLogger` (__init__, with_context, _format_message, debug, info ...)
- `TimingMetric` ()
- `MetricsCollector` (__init__, get_instance, record_timing, record_timing_sync, increment_counter ...)
- `AgentSpan` (duration_ms, complete, to_dict)
- `RequestTrace` (__init__, span, total_duration_ms, get_summary)

## `backend\agents\context_agent.py`
Context Agent

**Classes:**
- `DetailedFileSummary` (to_dict, from_dict, to_compact_string, to_markdown)
- `ContextAgentConfig` ()
- `ProjectStructure` (increment_version, on_change, to_dict, from_dict, _guess_language ...)
- `ImportantFact` (to_dict)
- `CurrentTask` (to_dict)
- `ContextAgent` (__init__, _get_persistence_path, _load_project_structure, _save_project_structure, set_workspace ...)

## `backend\core\interfaces\agent.py`
Agent Interface

**Classes:**
- `MessageType` ()
- `AgentStatus` ()
- `AgentMessage` (to_dict, from_dict)
- `AgentTool` (to_openai_format)
- `AgentContext` (get_config, set_shared, get_shared)
- `AgentCapability` ()
- `AgentConfig` ()
- `AgentMetadata` (to_dict)
- `AgentBase` (__init__, metadata, status, status, tools ...)

## `backend\tests\core\test_state.py`
Tests for Thread-Safe State Management

**Classes:**
- `TestStateVersion` (test_initial_version, test_increment)
- `TestThreadSafeState` (test_get_initial_value, test_set_value, test_version_increments_on_set, test_read_context, test_write_context ...)
- `TestSharedContext` (test_default_values, test_to_dict)
- `TestThreadSafeSharedContext` (test_project_structure, test_security_findings, test_concurrent_finding_additions, test_version_tracking, test_to_dict)
- `TestConcurrencyStress` (test_many_concurrent_writers, test_readers_and_writers)

## `backend\tests\core\test_retry.py`
Tests for Retry Logic

**Classes:**
- `TestRetryConfig` (test_default_values, test_custom_values, test_calculate_delay_exponential, test_calculate_delay_max_cap, test_calculate_delay_with_jitter)
- `TestShouldRetry` (test_retryable_exceptions, test_non_retryable_exceptions)
- `TestRetryAsync` (test_success_no_retry, test_retry_on_timeout, test_fail_after_max_retries, test_no_retry_on_non_recoverable, test_on_retry_callback)
- `TestWithRetryDecorator` (test_decorator_success, test_decorator_retry)
- `TestRetryContext` (test_context_success, test_context_retry_tracking, test_context_max_retries)
- `TestWithTimeoutAndRetry` (test_timeout_triggers_retry)
- `TestPresetConfigs` (test_retry_fast, test_retry_standard, test_retry_patient)

## `vscode-extension\out\tests\setup.js`
General module

**Functions:**
- `dispose()`

## `vscode-extension\out\backend\backendManager.d.ts`
General module

**Classes:**
- `BackendManager` ()

## `backend\core\connection_pool.py`
Connection Pool

**Classes:**
- `ConnectionState` ()
- `PoolConfig` ()
- `PoolStats` (to_dict)
- `PooledConnection` (mark_in_use, mark_idle, is_expired, age_seconds)
- `ConnectionFactory` (create, close, is_healthy, on_acquire, on_release)
- `PoolError` ()
- `PoolExhaustedError` (__init__)
- `PoolClosedError` ()
- `ConnectionPool` (__init__, config, stats, start, close ...)
- `SimpleConnectionFactory` (__init__, create, close, is_healthy)

## `vscode-extension\src\tests\websocketClient.test.ts`
Test File

**Functions:**
- `simulateOpen()`
- `simulateClose()`
- `simulateMessage()`
- `simulateError()`

## `backend\adapters\vectordb\chroma_adapter.py`
ChromaDB Vector Database Adapter

**Classes:**
- `ChromaAdapter` (__init__, provider_name, is_available, _get_client, _get_distance_fn ...)

## `backend\core\retry.py`
Retry Logic with Exponential Backoff

**Classes:**
- `RetryConfig` (__init__, calculate_delay)
- `RetryContext` (__init__, __aenter__, __aexit__, should_continue, handle_error ...)

## `backend\tests\core\test_timeout.py`
Tests for Timeout Management

**Classes:**
- `TestTimeoutConfig` (test_default_values, test_to_dict)
- `TestTimeoutContext` (test_success_within_timeout, test_timeout_raises_error, test_tracker_remaining_time)
- `TestWithTimeoutDecorator` (test_decorator_success, test_decorator_timeout)
- `TestRunWithTimeout` (test_success_result, test_timeout_with_raise, test_timeout_with_default, test_error_result)
- `TestTimeoutBudget` (test_budget_tracking, test_budget_exhaustion, test_step_timeout, test_multiple_steps, test_summary)
- `TestTimeoutTracker` (test_elapsed_time, test_mark_complete, test_mark_timeout)
- `TestDefaultConfig` (test_default_config_exists)

## `vscode-extension\out\tests\websocketClient.test.js`
Test File

**Functions:**
- `simulateOpen()`
- `simulateClose()`
- `simulateMessage()`
- `simulateError()`

## `backend\adapters\llm\openai_adapter.py`
OpenAI LLM Adapter

**Classes:**
- `OpenAIAdapter` (__init__, provider_name, is_available, _get_client, complete ...)

## `vscode-extension\out\views\agentsTreeProvider.d.ts`
Page Component

**Classes:**
- `AgentsTreeProvider` ()
- `AgentTreeItem` ()

## `vscode-extension\src\views\chatViewProvider.ts`
Page Component

**Classes:**
- `ChatViewProvider` ()

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
- `clearMessages()`
- `updateWelcome()`
- `saveState()`
- `sendMessage()`

## `vscode-extension\out\commands\commandHandler.d.ts`
Request Handler

**Classes:**
- `CommandHandler` ()

## `vscode-extension\src\events\eventBus.ts`
General module

**Classes:**
- `EventBus` ()

**Functions:**
- `dispose()`

## `backend\rag\service.py`
RAG Service using LlamaIndex

**Classes:**
- `RAGConfig` ()
- `ContextVersion` ()
- `RAGResult` ()
- `RAGService` (__init__, is_available, initialize, _init_domain_index, ingest_file ...)

## `vscode-extension\out\backend\websocketClient.d.ts`
General module

**Classes:**
- `WebSocketClient` ()

## `vscode-extension\out\extension.d.ts`
General module

**Functions:**
- `activate()`
- `deactivate()`

## `vscode-extension\src\watchers\fileWatcher.ts`
General module

**Classes:**
- `FileWatcher` ()

## `backend\core\interfaces\vectordb.py`
Vector Database Provider Interface

**Classes:**
- `DistanceMetric` ()
- `Document` (__post_init__)
- `SearchResult` ()
- `CollectionConfig` (__post_init__)
- `SearchConfig` ()
- `VectorDBProvider` (provider_name, is_available, create_collection, delete_collection, collection_exists ...)
- `VectorDBError` (__init__)
- `CollectionNotFoundError` ()
- `CollectionExistsError` ()

## `backend\server\main.py`
Main Server Entry Point

**Functions:**
- `create_app(settings)` → FastAPI
- `run_websocket_server(settings, handler)` → None
- `run_server(config_path, host, port)` → None
- `health_check()`
- `get_config()`
- `signal_handler(signum, frame)`
- `main()`

## `backend\integrations\file_analyzer.py`
File Analyzer

**Classes:**
- `ClassInfo` ()
- `FunctionInfo` ()
- `FileAnalysis` ()
- `FileAnalyzer` (__init__, analyze_file, _detect_language, _analyze_python, _analyze_js_ts ...)

## `backend\agents\coding_agent.py`
Coding Agent Plugin

**Classes:**
- `PatchValidationError` ()
- `PatchType` ()
- `PatchResult` (to_dict)
- `CodingAgentConfig` ()
- `CodingAgent` (__init__, metadata, set_llm, set_rag, set_context_agent ...)

## `backend\tests\agents\test_registry.py`
Unit Tests for Agent Registry

**Classes:**
- `TestAgent` (metadata, initialize, shutdown, process)
- `AnotherTestAgent` (metadata, initialize, shutdown, process)
- `TestAgentRegistryRegister` (test_register_agent_class, test_register_multiple_agents, test_register_duplicate_raises_error, test_register_with_custom_name)
- `TestAgentRegistryGet` (test_get_registered_agent, test_get_unregistered_agent_returns_none, test_get_creates_new_instance)
- `TestAgentRegistryUnregister` (test_unregister_agent, test_unregister_nonexistent_agent)
- `TestAgentRegistryEnableDisable` (test_agent_enabled_by_default, test_disable_agent, test_enable_disabled_agent, test_get_disabled_agent_returns_none, test_list_only_enabled_agents ...)
- `TestAgentRegistryInfo` (test_get_agent_info, test_get_info_nonexistent_returns_none, test_get_all_agent_info)

## `backend\agents\workflow.py`
Workflow Orchestrator

**Classes:**
- `WorkflowResult` (to_dict, get_summary)
- `WorkflowOrchestrator` (__init__, _emit_progress, analyze_workspace, analyze_file, _get_agent ...)

## `backend\tests\test_observability.py`
Tests for Observability Module

**Classes:**
- `TestCorrelationContext` (setup_method, test_generate_id, test_get_set, test_push_pop, test_correlation_scope ...)
- `TestLogContext` (test_default_values, test_to_dict, test_to_dict_excludes_none)
- `TestStructuredLogger` (test_with_context, test_format_message)
- `TestMetricsCollector` (setup_method, test_record_timing, test_increment_counter, test_set_gauge, test_timing_stats ...)
- `TestTimedOperation` (setup_method, test_timed_operation_success, test_timed_operation_failure, test_timed_operation_sync)
- `TestTracedDecorator` (setup_method, test_traced_async, test_traced_sync)
- `TestAgentSpan` (test_create_span, test_complete_span, test_duration, test_to_dict)
- `TestRequestTrace` (setup_method, test_create_trace, test_span_records_timing, test_span_error_handling, test_nested_spans ...)

## `vscode-extension\out\watchers\fileWatcher.d.ts`
General module

**Classes:**
- `FileWatcher` ()

## `benchmark\run_benchmark.py`
Benchmark Runner: Copilot con vs senza OMNI

**Classes:**
- `TokenEstimate` (from_text)
- `TaskResult` (to_dict)
- `BenchmarkReport` ()
- `BenchmarkRunner` (__init__, run, _simulate_task_completion, _generate_simulated_content, _run_task_without_omni ...)

## `vscode-extension\out\views\agentsTreeProvider.js`
Page Component

**Classes:**
- `AgentsTreeProvider` ()
- `AgentTreeItem` ()

## `backend\adapters\llm\local_adapter.py`
Local LLM Adapter

**Classes:**
- `LocalLLMAdapter` (__init__, provider_name, is_available, _get_client, complete ...)

## `backend\autogen\runtime.py`
AutoGen Multi-Agent Runtime

**Classes:**
- `AutoGenConfig` ()
- `GroupChatResult` (to_dict)
- `OmniAgentWrapper` (__init__, name, description, create_autogen_agent, process_message)
- `AutoGenRuntime` (__init__, is_available, wrap_agent, _get_user_proxy, run_group_chat ...)

## `backend\adapters\vectordb\base.py`
Base Vector Database Adapter

**Classes:**
- `BaseVectorDBAdapter` (__init__, _validate_documents, _merge_search_config, _handle_error)

## `test_omni.py`
Test OMNI - Assistant to the Assistant

**Functions:**
- `test_validation()`

## `backend\config\settings.py`
Settings Model

**Classes:**
- `ServerSettings` ()
- `OpenAISettings` ()
- `AnthropicSettings` ()
- `LocalLLMSettings` ()
- `LLMSettings` ()
- `QdrantSettings` ()
- `ChromaSettings` ()
- `FAISSSettings` ()
- `VectorDBSettings` ()
- `RAGSettings` ()

## `backend\agents\orchestrator.py`
Agent Orchestrator

**Classes:**
- `AgentOrchestrator` (__init__, add_agent, _wire_agent_integrations, remove_agent, add_hook ...)

## `vscode-extension\out\extension.js`
General module

**Functions:**
- `activate()`
- `deactivate()`

## `backend\agents\rag_agent.py`
RAG Agent

**Classes:**
- `RAGAgentConfig` ()
- `FileSummary` (to_dict, to_compact_string)
- `RAGQueryResult` (to_dict)
- `RAGAgent` (__init__, metadata, set_llm, set_rag_service, is_available ...)
- `RAGService` ()
- `RAGResult` ()
- `RAGConfig` ()

## `backend\tests\conftest.py`
Pytest Configuration and Shared Fixtures

**Classes:**
- `FakeLLMProvider` (__init__, provider_name, is_available, set_response, set_stream_chunks ...)
- `FakeVectorStore` (__init__, provider_name, is_available, collection_exists, count ...)

## `backend\config\loader.py`
Configuration Loader

**Classes:**
- `ConfigLoader` (__init__, load_yaml, load_multiple, _resolve_path, _substitute_env_vars ...)

## `backend\tests\core\test_dependencies.py`
Tests for Agent Dependency Management

**Classes:**
- `MockAgent` (__init__, metadata, process)
- `TestDependencyGraph` (test_add_agent, test_get_dependencies, test_get_dependents, test_get_provides)
- `TestDependencyValidation` (test_valid_dependencies, test_missing_dependency, test_validate_strict_raises, test_find_missing_dependencies)
- `TestCircularDependencies` (test_no_cycles, test_simple_cycle, test_longer_cycle, test_self_dependency)
- `TestTopologicalSort` (test_simple_order, test_complex_order, test_topological_sort_raises_on_cycle, test_get_initialization_order_alias)
- `TestTransitiveDependencies` (test_get_all_transitive_dependencies, test_transitive_with_diamond)
- `TestDependencyVisualization` (test_to_mermaid, test_to_dot)
- `TestDependencyInfo` (test_get_dependency_info)
- `TestConvenienceFunctions` (test_validate_dependencies_function, test_validate_dependencies_raises, test_get_initialization_order_function)
- `TestRealAgents` (test_omni_agent_dependencies)

## `vscode-extension\out\views\chatViewProvider.d.ts`
Page Component

**Classes:**
- `ChatViewProvider` ()

## `vscode-extension\out\backend\websocketClient.js`
General module

**Classes:**
- `WebSocketClient` ()

## `backend\adapters\llm\anthropic_adapter.py`
Anthropic LLM Adapter

**Classes:**
- `AnthropicAdapter` (__init__, provider_name, is_available, default_embedding_model, _get_client ...)

## `vscode-extension\out\events\eventBus.d.ts`
General module

**Classes:**
- `EventBus` ()

## `backend\integrations\copilot_integration.py`
Copilot Integration

**Classes:**
- `FileSummary` (to_markdown)
- `ProjectContext` ()
- `CopilotIntegration` (__init__, _ensure_directories, _analyze_data_flow, generate_all, generate_copilot_instructions ...)

## `backend\utils\gitignore.py`
Helpers for applying .gitignore-style filtering during scans.

**Functions:**
- `_clean_patterns(patterns)` → list[str]
- `load_gitignore(root)` → PathSpec
- `should_ignore(path, root, spec)` → bool

## `backend\adapters\llm\base.py`
Base LLM Adapter

**Classes:**
- `BaseLLMAdapter` (__init__, default_model, default_embedding_model, _merge_config, _convert_messages ...)

## `backend\core\exceptions.py`
OMNI Exception Hierarchy

**Classes:**
- `ErrorContext` (to_dict)
- `OMNIError` (__init__, __str__, to_dict)
- `AgentError` ()
- `AgentTimeoutError` (__init__)
- `AgentValidationError` (__init__)
- `AgentConfigurationError` (__init__)
- `AgentNotFoundError` (__init__)
- `AgentFatalError` (__init__)
- `AgentDependencyError` (__init__)
- `LLMError` ()

## `backend\adapters\vectordb\qdrant_adapter.py`
Qdrant Vector Database Adapter

**Classes:**
- `QdrantAdapter` (__init__, provider_name, is_available, _get_client, _get_distance ...)

## `vscode-extension\out\watchers\fileWatcher.js`
General module

**Classes:**
- `FileWatcher` ()

## `demo\sample_project\auth.py`
Sample Authentication Module

**Classes:**
- `UserSession` (__init__, log_activity)

## `vscode-extension\out\views\chatViewProvider.js`
Page Component

**Classes:**
- `ChatViewProvider` ()

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
- `clearMessages()`
- `updateWelcome()`
- `saveState()`
- `sendMessage()`

## `backend\tests\core\test_exceptions.py`
Tests for OMNI Exception Hierarchy

**Classes:**
- `TestErrorContext` (test_default_values, test_with_values, test_to_dict)
- `TestOMNIError` (test_basic_error, test_with_context, test_recoverable_flag, test_with_cause, test_to_dict)
- `TestAgentErrors` (test_agent_error_hierarchy, test_timeout_error_is_recoverable, test_validation_error_is_not_recoverable, test_configuration_error, test_not_found_error ...)
- `TestLLMErrors` (test_llm_error_hierarchy, test_timeout_is_recoverable, test_rate_limit_is_recoverable, test_auth_error_not_recoverable)
- `TestVectorDBErrors` (test_vectordb_error_hierarchy, test_connection_error_is_recoverable, test_query_error_stores_query)
- `TestWorkflowErrors` (test_workflow_error_hierarchy, test_timeout_stores_completed_stages, test_stage_error_stores_stage)
- `TestHelperFunctions` (test_is_recoverable_with_omni_error, test_is_recoverable_with_standard_errors, test_wrap_exception, test_wrap_exception_with_context)
- `TestExceptionCatching` (test_catch_specific_agent_error, test_catch_agent_error_base, test_catch_omni_error_base)

## `backend\tests\core\test_llm_adapter.py`
Unit Tests for LLM Adapter Interface

**Classes:**
- `TestFakeLLMProviderHealth` (test_health_check_returns_false_before_init, test_health_check_returns_true_after_init, test_health_check_can_be_set_unhealthy, test_health_check_returns_false_after_shutdown)
- `TestFakeLLMProviderComplete` (test_complete_returns_response, test_complete_returns_configured_response, test_complete_includes_model_in_response, test_complete_includes_usage_stats, test_complete_increments_call_count ...)
- `TestFakeLLMProviderStream` (test_stream_yields_chunks, test_stream_yields_configured_chunks)
- `TestFakeLLMProviderEmbed` (test_embed_returns_embeddings, test_embed_returns_consistent_dimension, test_embed_returns_configured_embedding)

## `backend\agents\compliance_agent.py`
Compliance Agent Plugin

**Classes:**
- `ComplianceSeverity` ()
- `ComplianceStatus` ()
- `ComplianceRule` ()
- `ComplianceFinding` (to_dict)
- `ComplianceAgentConfig` ()
- `ComplianceAgent` (__init__, metadata, set_llm, set_rag, set_context_agent ...)

## `test_omni_simple.py`
Test OMNI - Assistant to the Assistant

**Classes:**
- `Severity` ()
- `SecurityFinding` ()
- `ComplianceFinding` ()
- `SimpleSecurityChecker` (check)
- `SimpleComplianceChecker` (check)

## `vscode-extension\src\commands\commandHandler.ts`
Request Handler

**Classes:**
- `CommandHandler` ()

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
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`

## `vscode-extension\src\tests\setup.ts`
General module

**Functions:**
- `dispose()`

## `backend\tests\core\test_connection_pool.py`
Tests for Connection Pool

**Classes:**
- `MockConnection` (__init__, close)
- `MockConnectionFactory` (__init__, create, close, is_healthy)
- `TestPooledConnection` (test_initial_state, test_mark_in_use, test_mark_idle, test_is_expired, test_in_use_not_expired)
- `TestPoolConfig` (test_defaults)
- `TestPoolStats` (test_to_dict)
- `TestConnectionPool` (test_start_creates_min_connections, test_acquire_returns_connection, test_connection_reused, test_creates_new_when_all_in_use, test_exhausted_pool_timeout ...)
- `TestSimpleConnectionFactory` (test_create_sync_function, test_create_async_function, test_health_check)
- `TestCreatePool` (test_create_pool)
- `TestPoolHealthChecks` (test_unhealthy_connection_removed, test_healthy_connection_kept)

## `backend\tests\core\test_vectordb_adapter.py`
Unit Tests for VectorDB Adapter Interface

**Classes:**
- `TestFakeVectorStoreHealth` (test_health_check_returns_false_before_init, test_health_check_returns_true_after_init, test_health_check_can_be_set_unhealthy)
- `TestFakeVectorStoreCollections` (test_create_collection, test_delete_collection, test_list_collections_empty)
- `TestFakeVectorStoreDocuments` (test_upsert_documents, test_get_documents_by_id, test_delete_documents)
- `TestFakeVectorStoreSearch` (test_search_returns_results, test_search_with_filter, test_search_empty_collection)

## `backend\agents\security_agent.py`
Security Agent Plugin

**Classes:**
- `Severity` ()
- `FindingCategory` ()
- `SecurityFinding` (to_dict)
- `SecurityAgentConfig` ()
- `SecurityAgent` (__init__, metadata, set_llm, set_context_agent, set_rag_agent ...)

## `vscode-extension\out\commands\commandHandler.js`
Request Handler

**Classes:**
- `CommandHandler` ()

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
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`
- `handler()`

## `vscode-extension\src\backend\websocketClient.ts`
General module

**Classes:**
- `WebSocketClient` ()

**Functions:**
- `resolve()`
- `reject()`

## `backend\server\websocket_handler.py`
WebSocket Handler

**Classes:**
- `WebSocketHandler` (__init__, _initialize_agents, handle_connection, _route_message, _handle_chat_message ...)

## `backend\adapters\vectordb\faiss_adapter.py`
FAISS Vector Database Adapter

**Classes:**
- `FAISSCollection` ()
- `FAISSAdapter` (__init__, provider_name, is_available, _get_faiss, _get_index_type ...)

## `backend\adapters\vectordb\factory.py`
Vector Database Factory

**Classes:**
- `VectorDBFactory` (register, create, from_config, list_providers, create_with_health_check)

## `vscode-extension\out\backend\backendManager.js`
General module

**Classes:**
- `BackendManager` ()

**Functions:**
- `onOpen()`
- `onClose()`
- `onError()`
- `onMessage()`

## `vscode-extension\src\views\historyTreeProvider.ts`
Page Component

**Classes:**
- `HistoryTreeProvider` ()
- `HistoryTreeItem` ()
- `SessionTreeItem` ()
- `EmptyHistoryItem` ()

## `vscode-extension\src\views\agentsTreeProvider.ts`
Page Component

**Classes:**
- `AgentsTreeProvider` ()
- `AgentTreeItem` ()

## `demo\demo_mode.py`
OMNI Demo Mode

**Classes:**
- `DemoConfig` ()

## `backend\server\message_types.py`
Message Types

**Classes:**
- `MessageType` ()
- `Message` (to_dict, from_dict, chat_response, stream_start, stream_chunk ...)

## `vscode-extension\out\views\historyTreeProvider.d.ts`
Page Component

**Classes:**
- `HistoryTreeProvider` ()
- `HistoryTreeItem` ()

## `vscode-extension\src\backend\backendManager.ts`
General module

**Classes:**
- `BackendManager` ()

**Functions:**
- `onOpen()`
- `onClose()`
- `onError()`
- `onMessage()`

## `vscode-extension\out\views\historyTreeProvider.js`
Page Component

**Classes:**
- `HistoryTreeProvider` ()
- `HistoryTreeItem` ()
- `SessionTreeItem` ()
- `EmptyHistoryItem` ()
