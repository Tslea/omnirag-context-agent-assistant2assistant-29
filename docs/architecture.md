# OMNI Architecture

This document describes the architecture of the OMNI system.

## Overview

OMNI is a modular AI development system with two main components:

1. **VS Code Extension** (TypeScript) - User interface
2. **Python Backend** - AI agents and processing

```
┌─────────────────────────────────────────────────────────────┐
│                    VS Code Extension                         │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │  Chat View   │ │ Agents Tree  │ │   History Tree       │ │
│  │  (Webview)   │ │ (TreeView)   │ │   (TreeView)         │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
│                          │                                   │
│                  ┌───────┴────────┐                         │
│                  │   Event Bus    │                         │
│                  └───────┬────────┘                         │
│                          │                                   │
│               ┌──────────┴──────────┐                       │
│               │  Backend Manager    │                       │
│               │  (WebSocket Client) │                       │
│               └──────────┬──────────┘                       │
└──────────────────────────┼──────────────────────────────────┘
                           │ WebSocket
┌──────────────────────────┼──────────────────────────────────┐
│                          │                                   │
│               ┌──────────┴──────────┐                       │
│               │   WebSocket Server  │                       │
│               └──────────┬──────────┘                       │
│                          │                                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Agent Registry                        ││
│  │                                                          ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   ││
│  │  │Assistant │ │ Security │ │Compliance│ │ Coding   │   ││
│  │  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │   ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   ││
│  └─────────────────────────────────────────────────────────┘│
│                          │                                   │
│  ┌───────────────────────┴───────────────────────────────┐  │
│  │                    Adapters                            │  │
│  │                                                        │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐    │  │
│  │  │    LLM Adapters     │  │  VectorDB Adapters  │    │  │
│  │  │ ┌───────┬─────────┐ │  │ ┌───────┬─────────┐ │    │  │
│  │  │ │OpenAI │Anthropic│ │  │ │Qdrant │ Chroma  │ │    │  │
│  │  │ ├───────┼─────────┤ │  │ ├───────┼─────────┤ │    │  │
│  │  │ │ Local │  Fake   │ │  │ │ FAISS │  Fake   │ │    │  │
│  │  │ └───────┴─────────┘ │  │ └───────┴─────────┘ │    │  │
│  │  └─────────────────────┘  └─────────────────────┘    │  │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Optional Components                        │ │
│  │                                                         │ │
│  │  ┌──────────────┐        ┌──────────────┐             │ │
│  │  │  RAG Service │        │   AutoGen    │             │ │
│  │  │ (LlamaIndex) │        │   Runtime    │             │ │
│  │  └──────────────┘        └──────────────┘             │ │
│  └────────────────────────────────────────────────────────┘ │
│                          Python Backend                      │
└──────────────────────────────────────────────────────────────┘
```

## Component Details

### VS Code Extension

Located in: `vscode-extension/src/`

| File | Purpose |
|------|---------|
| `extension.ts` | Entry point, activation |
| `views/chatViewProvider.ts` | Chat webview UI |
| `views/agentsTreeProvider.ts` | Agents tree view |
| `views/historyTreeProvider.ts` | Chat history tree |
| `backend/backendManager.ts` | Backend lifecycle |
| `backend/websocketClient.ts` | WebSocket communication |
| `events/eventBus.ts` | Internal event system |
| `commands/commandHandler.ts` | Command registration |

### Python Backend

Located in: `backend/`

#### Core Interfaces (`core/interfaces/`)

| File | Purpose | Key Classes |
|------|---------|-------------|
| `agent.py` | Agent contract | `AgentBase`, `AgentMessage`, `AgentContext` |
| `llm.py` | LLM contract | `LLMProvider`, `LLMConfig`, `LLMResponse` |
| `vectordb.py` | VectorDB contract | `VectorDBProvider`, `Document`, `SearchResult` |
| `workflow.py` | Workflow contract | `WorkflowBase`, `WorkflowStep` |

#### Adapters (`adapters/`)

**LLM Adapters** (`adapters/llm/`):
- `openai_adapter.py` - OpenAI/Azure OpenAI
- `anthropic_adapter.py` - Anthropic Claude
- `local_adapter.py` - LM Studio, Ollama, etc.
- `base.py` - Base adapter class

**VectorDB Adapters** (`adapters/vectordb/`):
- `qdrant_adapter.py` - Qdrant
- `chroma_adapter.py` - ChromaDB
- `faiss_adapter.py` - FAISS
- `base.py` - Base adapter class

#### Agents (`agents/`)

| File | Agent | Purpose |
|------|-------|---------|
| `base_agents.py` | AssistantAgent | General conversation |
| `security_agent.py` | SecurityAgent | Vulnerability scanning |
| `compliance_agent.py` | ComplianceAgent | Regulatory compliance |
| `coding_agent.py` | CodingAgent | Code changes (patches) |
| `context_agent.py` | ContextAgent | Session memory and coordination |
| `rag_agent.py` | RAGAgent | Intelligent RAG with domain selection |
| `loader.py` | AgentRegistry | Dynamic agent loading |

#### Optional Components

**RAG Service** (`rag/`):
- `service.py` - LlamaIndex integration
- Uses configured VectorDB (Chroma by default)
- Enabled by default for token-efficient context
- Domain-based indices

**RAG Agent** (`agents/rag_agent.py`):
- Intelligent wrapper around RAG Service
- Automatic domain selection
- Query optimization
- Enabled by default in `default.yaml`

**Context Agent** (`agents/context_agent.py`):
- Session memory management
**AutoGen Runtime** (`autogen/`):
- `runtime.py` - Multi-agent chat

### Chat Message Flow

```
User Input (VS Code)
        │
        ▼
┌───────────────────┐
│   ChatViewProvider │
│   (postMessage)    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│    Event Bus      │
│ CHAT_MESSAGE_SENT │
┌───────────────────┐
│  Backend Manager  │
┌───────────────────┐
│ WebSocket Server  │
┌───────────────────┐
│   Agent Registry  │
          ▼

## Context Pack (output)

Il backend genera un "Context Pack" consumabile da Copilot/LLM in:

- `.github/copilot-instructions.md` – istruzioni minime + link al pack
- `.omni/context/`
  - `project-overview.md` – stack e architettura sintetica
  - `component-map.md` – mappa moduli/cartelle con responsabilità
  - `interfaces-and-apis.md` – superfici pubbliche (API, funzioni, classi)
  - `data-model.md` – classi/modelli/esportazioni note
  - `hotspots.md` – file prioritari (es. più LOC) per concentrare l'attenzione
  - `file-summaries.md` – riassunti dettagliati file x file
- `.omni/insights/` – `security.md`, `compliance.md`

### Aggiornamento incrementale (on-demand synthesis)

1. Watcher (estensione) rileva file cambiati → invia `analyze_code` o `scan_workspace`.
2. Il workflow rigenera solo i chunk/file impattati (RAG) e aggiorna le sezioni pertinenti del Context Pack.
3. `.github/copilot-instructions.md` resta breve e punta ai markdown in `.omni/context/`.
┌───────────────────┐
│  Selected Agent   │
│  (process msg)    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   LLM Adapter     │
│  (if needed)      │
└─────────┬─────────┘
          │
          ▼
     Response
```

### Agent Processing Flow

```python
# Agent receives message
async def process(message: AgentMessage, context: AgentContext) -> AgentMessage:
    # 1. Parse intent
    intent = parse_intent(message.content)
    
    # 2. Get relevant context (optional RAG)
    if self._rag:
        context = await self._rag.query(intent)
    
    # 3. Build LLM prompt
    prompt = build_prompt(message, context)
    
    # 4. Get LLM response
    response = await self._llm.complete(prompt)
    
    # 5. Return result
    return AgentMessage(
        content=response.content,
        type=MessageType.TEXT,
        sender=self.metadata.id,
    )
```

## Configuration

### Hierarchy

Configuration is loaded in order (later overrides earlier):

1. Default values (in code)
2. `config/default.yaml`
3. Environment variables (`OMNI_` prefix)

### Key Settings (default.yaml)

```yaml
server:
  host: "localhost"
  port: 8765
  cors_origins:
    - "vscode-webview://*"
    - "http://localhost:*"
  debug: false
  log_level: "INFO"

llm:
  provider: "local"  # local | openai | anthropic
  openai:
    api_key: ${OPENAI_API_KEY}
    model: "gpt-4-turbo-preview"
    embedding_model: "text-embedding-3-small"
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: "claude-3-sonnet-20240229"
  local:
    provider_type: "ollama"
    base_url: "http://localhost:11434/v1"
    model: "phi"

vectordb:
  provider: "chroma"  # chroma | qdrant | faiss
  default_collection: "omni_documents"
  default_dimension: 1536
  chroma:
    persist_path: "./data/chroma"
  qdrant:
    url: ${QDRANT_URL}
    api_key: ${QDRANT_API_KEY}
    prefer_grpc: false
  faiss:
    persist_path: "./data/faiss"

rag:
  enabled: true
  chunk_size: 512
  chunk_overlap: 50
  top_k: 5

features:
  enable_streaming: true
  enable_rag: true
  enable_tool_use: true
```

## Safety Guarantees

### Agent Restrictions

| Agent | Can Read Files | Can Write Files | Requires LLM |
|-------|----------------|-----------------|--------------|
| Assistant | Yes | No | Yes |
| Security | Yes | No | Optional |
| Compliance | Yes | No | Optional |
| Coding | Yes | No (patches only) | Yes |

### Data Flow Restrictions

1. **No direct file writes** - Coding agent outputs patches only
2. **No secrets in output** - Patches are validated
3. **Config file protection** - Config edits rejected by default

### Optional Component Isolation

- RAG and AutoGen are disabled by default
- Missing dependencies don't crash the system
- All features are opt-in

## Extension Points

### Adding New LLM Provider

1. Create `adapters/llm/my_adapter.py`
2. Implement `LLMProvider` interface
3. Register in `adapters/llm/factory.py`
4. Add config section in `default.yaml`

### Adding New VectorDB

1. Create `adapters/vectordb/my_adapter.py`
2. Implement `VectorDBProvider` interface
3. Register in `adapters/vectordb/factory.py`
4. Add config section in `default.yaml`

### Adding New Agent

See [adding_agent.md](adding_agent.md) for detailed guide.

## Performance Considerations

### Streaming

- All LLM adapters support streaming
- WebSocket passes chunks in real-time
- UI updates incrementally

### Lazy Loading

- VS Code views are lazy-loaded
- Extension works offline
- Backend connection is optional

### Caching

- VectorDB embeddings cached
- RAG indices persisted to disk
- LLM responses not cached (configurable)
