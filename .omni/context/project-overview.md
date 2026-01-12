# Project Overview: OMNI

> Last updated: 2026-01-10T15:19:07.618696

## Stack

- **Type:** Software Project
- **Languages:** PHP, TypeScript, Python, JavaScript

## Architecture

- **Backend** code is in dedicated `backend/` folder
- Has **GitHub Actions** CI/CD workflows
- Entry points: backend\server\main.py
- **116** source files analyzed

## Data Flow

- **Entry Points:** backend\server\main.py
- **Flow:** UI/Views → API Handlers → Services → Repositories → Database
- **Layers:** UI Layer (9 files) → API Layer (4 files) → Service Layer (1 files)
- **Key Modules:** `backend.core.interfaces.llm` (18 imports), `backend.core.interfaces.agent` (17 imports), `../events/eventBus` (13 imports)

## File Structure

**Total files analyzed:** 116

### `./`
- test_omni.py
- test_omni_simple.py

### `.github\workflows/`
- ci.yml

### `backend/`
- __init__.py
- observability.py

### `backend\adapters\llm/`
- __init__.py
- anthropic_adapter.py
- base.py
- factory.py
- local_adapter.py
- openai_adapter.py

### `backend\adapters\vectordb/`
- __init__.py
- base.py
- chroma_adapter.py
- factory.py
- faiss_adapter.py
- qdrant_adapter.py

### `backend\agents/`
- __init__.py
- base_agents.py
- coding_agent.py
- compliance_agent.py
- context_agent.py
- loader.py
- orchestrator.py
- rag_agent.py
- security_agent.py
- workflow.py

### `backend\autogen/`
- __init__.py
- runtime.py

### `backend\config/`
- __init__.py
- default.yaml
- loader.py
- settings.py

### `backend\core/`
- __init__.py
- connection_pool.py
- dependencies.py
- exceptions.py
- retry.py
- state.py
- timeout.py

### `backend\core\interfaces/`
- __init__.py
- agent.py
- llm.py
- vectordb.py
- workflow.py

### `backend\integrations/`
- __init__.py
- copilot_integration.py
- file_analyzer.py

### `backend\rag/`
- __init__.py
- service.py

### `backend\rulesets/`
- gdpr-sample.yaml

### `backend\server/`
- __init__.py
- main.py
- message_types.py
- websocket_handler.py

### `backend\tests/`
- __init__.py
- conftest.py
- test_observability.py

### `backend\tests\agents/`
- __init__.py
- test_context_persistence.py
- test_registry.py

### `backend\tests\core/`
- __init__.py
- test_connection_pool.py
- test_dependencies.py
- test_exceptions.py
- test_llm_adapter.py
- test_retry.py
- test_state.py
- test_timeout.py
- test_vectordb_adapter.py

### `backend\tests\fakes/`
- __init__.py

### `backend\utils/`
- __init__.py
- gitignore.py

### `benchmark/`
- run_benchmark.py
- tasks.yaml

### `demo/`
- __init__.py
- demo_mode.py

### `demo\sample_project/`
- auth.py
- config.yaml

### `vscode-extension/`
- jest.config.js

### `vscode-extension\out/`
- extension.d.ts
- extension.js

### `vscode-extension\out\backend/`
- backendManager.d.ts
- backendManager.js
- websocketClient.d.ts
- websocketClient.js

### `vscode-extension\out\commands/`
- commandHandler.d.ts
- commandHandler.js

### `vscode-extension\out\events/`
- eventBus.d.ts
- eventBus.js

### `vscode-extension\out\tests/`
- eventBus.test.d.ts
- eventBus.test.js
- setup.d.ts
- setup.js
- websocketClient.test.d.ts
- websocketClient.test.js

### `vscode-extension\out\views/`
- agentsTreeProvider.d.ts
- agentsTreeProvider.js
- chatViewProvider.d.ts
- chatViewProvider.js
- historyTreeProvider.d.ts
- historyTreeProvider.js

### `vscode-extension\out\watchers/`
- fileWatcher.d.ts
- fileWatcher.js

### `vscode-extension\src/`
- extension.ts

### `vscode-extension\src\backend/`
- backendManager.ts
- websocketClient.ts

### `vscode-extension\src\commands/`
- commandHandler.ts

### `vscode-extension\src\events/`
- eventBus.ts

### `vscode-extension\src\tests/`
- eventBus.test.ts
- setup.ts
- websocketClient.test.ts

### `vscode-extension\src\views/`
- agentsTreeProvider.ts
- chatViewProvider.ts
- historyTreeProvider.ts

### `vscode-extension\src\watchers/`
- fileWatcher.ts
