# Component Map

> Last updated: 2026-01-10T15:19:07.623344

Breakdown by top-level folder with key responsibilities and dependencies.

## .github

- `.github\workflows\ci.yml` — General module

## backend

- `backend\__init__.py` — OMNI Backend Package (depends on: backend.core, backend.adapters.llm.factory, backend.adapters.vectordb.factory, backend.agents, backend.config)
- `backend\adapters\llm\__init__.py` — LLM Adapters Package (depends on: backend.adapters.llm.base, backend.adapters.llm.openai_adapter, backend.adapters.llm.anthropic_adapter, backend.adapters.llm.local_adapter, backend.adapters.llm.factory)
- `backend\adapters\llm\anthropic_adapter.py` — Anthropic LLM Adapter (depends on: backend.adapters.llm.base, backend.core.interfaces.llm)
- `backend\adapters\llm\base.py` — Base LLM Adapter (depends on: backend.core.interfaces.llm)
- `backend\adapters\llm\factory.py` — LLM Factory (depends on: backend.core.interfaces.llm, backend.adapters.llm.openai_adapter, backend.adapters.llm.anthropic_adapter, backend.adapters.llm.local_adapter)
- `backend\adapters\llm\local_adapter.py` — Local LLM Adapter (depends on: backend.adapters.llm.base, backend.core.interfaces.llm)
- `backend\adapters\llm\openai_adapter.py` — OpenAI LLM Adapter (depends on: backend.adapters.llm.base, backend.core.interfaces.llm)
- `backend\adapters\vectordb\__init__.py` — Vector Database Adapters Package (depends on: backend.adapters.vectordb.base, backend.adapters.vectordb.qdrant_adapter, backend.adapters.vectordb.chroma_adapter, backend.adapters.vectordb.faiss_adapter, backend.adapters.vectordb.factory)
- `backend\adapters\vectordb\base.py` — Base Vector Database Adapter (depends on: backend.core.interfaces.vectordb)
- `backend\adapters\vectordb\chroma_adapter.py` — ChromaDB Vector Database Adapter (depends on: backend.adapters.vectordb.base, backend.core.interfaces.vectordb)
- `backend\adapters\vectordb\factory.py` — Vector Database Factory (depends on: backend.core.interfaces.vectordb, backend.adapters.vectordb.qdrant_adapter, backend.adapters.vectordb.chroma_adapter, backend.adapters.vectordb.faiss_adapter)
- `backend\adapters\vectordb\faiss_adapter.py` — FAISS Vector Database Adapter (depends on: backend.adapters.vectordb.base, backend.core.interfaces.vectordb)
- `backend\adapters\vectordb\qdrant_adapter.py` — Qdrant Vector Database Adapter (depends on: backend.adapters.vectordb.base, backend.core.interfaces.vectordb)
- `backend\agents\__init__.py` — Agent Plugin System (depends on: backend.agents.loader, backend.agents.orchestrator, backend.agents.base_agents, backend.agents.context_agent, backend.agents.rag_agent)
- `backend\agents\base_agents.py` — Base Agent Implementations (depends on: backend.core.interfaces.agent, backend.core.interfaces.llm)
- `backend\agents\coding_agent.py` — Coding Agent Plugin (depends on: backend.core.interfaces.agent, backend.core.interfaces.llm)
- `backend\agents\compliance_agent.py` — Compliance Agent Plugin (depends on: backend.core.interfaces.agent, backend.core.interfaces.llm)
- `backend\agents\context_agent.py` — Context Agent (depends on: backend.core.interfaces.agent, backend.core.interfaces.llm, backend.core.state, backend.utils.gitignore, backend.integrations.file_analyzer)
- `backend\agents\loader.py` — Agent Loader and Registry (depends on: backend.core.interfaces.agent, backend.agents.base_agents, backend.agents.security_agent, backend.agents.compliance_agent, backend.agents.context_agent)
- `backend\agents\orchestrator.py` — Agent Orchestrator (depends on: backend.core.interfaces.agent, backend.core.interfaces.llm, backend.core.exceptions, backend.core.retry, backend.agents.loader)
- `backend\agents\rag_agent.py` — RAG Agent (depends on: backend.core.interfaces.agent, backend.core.interfaces.llm, backend.rag.service)
- `backend\agents\security_agent.py` — Security Agent Plugin (depends on: backend.core.interfaces.agent, backend.core.interfaces.llm, backend.core.interfaces.llm)
- `backend\agents\workflow.py` — Workflow Orchestrator (depends on: backend.core.interfaces.agent, backend.agents.orchestrator, backend.integrations.copilot_integration, backend.integrations.file_analyzer, backend.integrations.copilot_integration)
- `backend\autogen\__init__.py` — AutoGen Multi-Agent Runtime Module (depends on: backend.autogen.runtime)
- `backend\autogen\runtime.py` — AutoGen Multi-Agent Runtime (depends on: backend.core.interfaces.agent)
- `backend\config\__init__.py` — Configuration Management (depends on: backend.config.settings, backend.config.loader)
- `backend\config\default.yaml` — General module
- `backend\config\loader.py` — Configuration Loader
- `backend\config\settings.py` — Settings Model (depends on: backend.config.loader)
- `backend\core\__init__.py` — OMNI Backend Core Package (depends on: backend.core.interfaces.llm, backend.core.interfaces.vectordb, backend.core.interfaces.agent, backend.core.interfaces.workflow, backend.core.exceptions)
- `backend\core\connection_pool.py` — Connection Pool
- `backend\core\dependencies.py` — Agent Dependency Management
- `backend\core\exceptions.py` — OMNI Exception Hierarchy
- `backend\core\interfaces\__init__.py` — Core interfaces package. (depends on: backend.core.interfaces.llm, backend.core.interfaces.vectordb, backend.core.interfaces.agent, backend.core.interfaces.workflow)
- `backend\core\interfaces\agent.py` — Agent Interface
- `backend\core\interfaces\llm.py` — LLM Provider Interface
- `backend\core\interfaces\vectordb.py` — Vector Database Provider Interface
- `backend\core\interfaces\workflow.py` — Workflow Interface
- `backend\core\retry.py` — Retry Logic with Exponential Backoff (depends on: backend.core.exceptions)
- `backend\core\state.py` — Thread-Safe State Management
- `backend\core\timeout.py` — Timeout Management (depends on: backend.core.exceptions)
- `backend\integrations\__init__.py` — OMNI Integrations Package (depends on: backend.integrations.copilot_integration, backend.integrations.file_analyzer)
- `backend\integrations\copilot_integration.py` — Copilot Integration
- `backend\integrations\file_analyzer.py` — File Analyzer (depends on: backend.integrations.copilot_integration)
- `backend\observability.py` — Observability Module
- `backend\rag\__init__.py` — RAG (Retrieval-Augmented Generation) Module (depends on: backend.rag.service)
- `backend\rag\service.py` — RAG Service using LlamaIndex (depends on: backend.utils.gitignore)
- `backend\rulesets\gdpr-sample.yaml` — General module
- `backend\server\__init__.py` — Backend Server Package (depends on: backend.server.main, backend.server.websocket_handler, backend.server.message_types)
- `backend\server\main.py` — Main Server Entry Point (depends on: backend.config.settings, backend.server.websocket_handler)

## benchmark

- `benchmark\run_benchmark.py` — Benchmark Runner: Copilot con vs senza OMNI
- `benchmark\tasks.yaml` — General module

## demo

- `demo\__init__.py` — Demo module for OMNI.
- `demo\demo_mode.py` — OMNI Demo Mode (depends on: backend.tests.conftest, backend.core.interfaces.llm, backend.core.interfaces.vectordb, backend.core.interfaces.agent, backend.agents.base_agents)
- `demo\sample_project\auth.py` — Sample Authentication Module
- `demo\sample_project\config.yaml` — Configuration File

## test_omni.py

- `test_omni.py` — Test OMNI - Assistant to the Assistant (depends on: backend.agents.context_agent, backend.agents.rag_agent, backend.agents.security_agent, backend.agents.compliance_agent)

## test_omni_simple.py

- `test_omni_simple.py` — Test OMNI - Assistant to the Assistant

## vscode-extension

- `vscode-extension\jest.config.js` — Configuration File
- `vscode-extension\out\backend\backendManager.d.ts` — General module (depends on: ../events/eventBus)
- `vscode-extension\out\backend\backendManager.js` — General module
- `vscode-extension\out\backend\websocketClient.d.ts` — General module
- `vscode-extension\out\backend\websocketClient.js` — General module
- `vscode-extension\out\commands\commandHandler.d.ts` — Request Handler (depends on: ../backend/backendManager, ../views/chatViewProvider, ../views/agentsTreeProvider, ../views/historyTreeProvider, ../events/eventBus)
- `vscode-extension\out\commands\commandHandler.js` — Request Handler
- `vscode-extension\out\events\eventBus.d.ts` — General module
- `vscode-extension\out\events\eventBus.js` — General module
- `vscode-extension\out\extension.d.ts` — General module
- `vscode-extension\out\extension.js` — General module
- `vscode-extension\out\tests\eventBus.test.d.ts` — Test File
- `vscode-extension\out\tests\eventBus.test.js` — Test File
- `vscode-extension\out\tests\setup.d.ts` — General module
- `vscode-extension\out\tests\setup.js` — General module
- `vscode-extension\out\tests\websocketClient.test.d.ts` — Test File
- `vscode-extension\out\tests\websocketClient.test.js` — Test File
- `vscode-extension\out\views\agentsTreeProvider.d.ts` — Page Component (depends on: ../backend/backendManager, ../events/eventBus)
- `vscode-extension\out\views\agentsTreeProvider.js` — Page Component
- `vscode-extension\out\views\chatViewProvider.d.ts` — Page Component (depends on: ../backend/backendManager, ../events/eventBus)
- `vscode-extension\out\views\chatViewProvider.js` — Page Component
- `vscode-extension\out\views\historyTreeProvider.d.ts` — Page Component (depends on: ../events/eventBus)
- `vscode-extension\out\views\historyTreeProvider.js` — Page Component
- `vscode-extension\out\watchers\fileWatcher.d.ts` — General module (depends on: ../events/eventBus, ../backend/backendManager)
- `vscode-extension\out\watchers\fileWatcher.js` — General module
- `vscode-extension\src\backend\backendManager.ts` — General module (depends on: ../events/eventBus, ./websocketClient)
- `vscode-extension\src\backend\websocketClient.ts` — General module
- `vscode-extension\src\commands\commandHandler.ts` — Request Handler (depends on: ../backend/backendManager, ../views/chatViewProvider, ../views/agentsTreeProvider, ../views/historyTreeProvider, ../events/eventBus)
- `vscode-extension\src\events\eventBus.ts` — General module
- `vscode-extension\src\extension.ts` — General module (depends on: ./backend/backendManager, ./views/chatViewProvider, ./views/agentsTreeProvider, ./views/historyTreeProvider, ./commands/commandHandler)
- `vscode-extension\src\tests\eventBus.test.ts` — Test File (depends on: ../events/eventBus)
- `vscode-extension\src\tests\setup.ts` — General module
- `vscode-extension\src\tests\websocketClient.test.ts` — Test File (depends on: ../backend/websocketClient)
- `vscode-extension\src\views\agentsTreeProvider.ts` — Page Component (depends on: ../backend/backendManager, ../events/eventBus)
- `vscode-extension\src\views\chatViewProvider.ts` — Page Component (depends on: ../backend/backendManager, ../events/eventBus)
- `vscode-extension\src\views\historyTreeProvider.ts` — Page Component (depends on: ../events/eventBus)
- `vscode-extension\src\watchers\fileWatcher.ts` — General module (depends on: ../events/eventBus, ../backend/backendManager)
