# OMNI Token Efficiency System

## Il Problema Risolto

I coding assistant tradizionali sprecano token rileggendo l'intero codebase ad ogni richiesta:

```
Utente: "crea app cani"
Sistema: Legge workspace... 0 files (OK)
→ Genera backend + frontend

Utente: "metti il login"
Sistema: Legge workspace... 50k tokens (SPRECO!)
→ Non sa che è fullstack, genera solo backend
```

## La Soluzione OMNI

OMNI usa **memoria persistente** e **riassunti** invece di codice raw:

```
Utente: "crea app cani"
Sistema: Genera backend + frontend
→ Context Agent: Registra "fullstack, FastAPI + React"
→ RAG Agent: Indicizza riassunti (200 chars/file)

Utente: "metti il login"
Sistema: Context Agent dice "fullstack, FastAPI + React" (~200 chars)
→ Sa automaticamente che serve backend + frontend
→ Genera entrambi con ~2k token di contesto invece di 50k
```

## Architettura

### Context Agent (Memoria)
```python
# Prima: Solo fatti dalla conversazione
facts = ["user mentioned auth.py"]

# Dopo: Struttura progetto PERSISTENTE
project = ProjectStructure(
    project_type="fullstack",
    backend_framework="FastAPI",
    frontend_framework="React",
    backend_files={
        "main.py": "Classes: App | Functions: get_users, create_user",
        "auth.py": "Classes: AuthService | Functions: login, verify_token"
    },
    frontend_files={
        "App.tsx": "Components: App | Exports: default",
        "Login.tsx": "Components: LoginForm | Functions: handleSubmit"
    },
    completed_features=[
        {"name": "user_crud", "files": ["main.py", "UserList.tsx"]}
    ]
)

# Output per prompt: ~200 chars invece di 50k
summary = "Project: fullstack | Backend: FastAPI | Frontend: React | Files: 15"
```

### RAG Agent (Librarian con Riassunti)
```python
# Prima: Ritorna codice raw
results = rag.query("authentication")
# → 50k chars di codice Python/TypeScript

# Dopo: Ritorna RIASSUNTI
results = rag_agent.get_relevant_summaries("authentication")
# → "auth.py: Classes: AuthService | Functions: login, verify_token"
# → ~2k chars totali
```

### Coding Agent (Generatore Consapevole)
```python
# Prima: Genera senza contesto
patch = coding_agent.generate_patch("add login")
# → Genera solo backend, non sa del frontend

# Dopo: Usa project context
project_summary = context_agent.get_project_summary_for_prompt()
is_fullstack = context_agent.requires_backend_and_frontend()
# → Sa che deve generare backend + frontend

# Dopo generazione: Registra per memoria
coding_agent._register_generated_file(patch)
# → Context Agent memorizza il nuovo file
# → RAG Agent indicizza il riassunto
```

## Flow Completo

```
1. User: "crea app cani"

2. Orchestrator:
   - Chiede a Context Agent: "project summary?"
   - Context: "Project: Not analyzed yet"
   - Procede con generazione

3. Coding Agent genera:
   - backend/main.py (FastAPI)
   - frontend/App.tsx (React)
   
4. Per ogni file generato:
   - Coding Agent → Context Agent: register_generated_file()
   - Coding Agent → RAG Agent: index_file_with_summary()
   
5. Context Agent memorizza:
   - project_type = "fullstack"
   - backend_framework = "FastAPI"
   - frontend_framework = "React"
   - backend_files["main.py"] = "Classes: App | Functions: ..."
   
6. RAG Agent indicizza:
   - _file_summaries["main.py"] = FileSummary(...)

---

7. User: "metti il login"

8. Orchestrator:
   - Chiede a Context Agent: "project summary?"
   - Context: "Project: fullstack | Backend: FastAPI | Frontend: React | Files: 4"
   - Chiede: "requires_backend_and_frontend?"
   - Context: True
   
9. Orchestrator sa automaticamente:
   - Deve generare backend endpoint
   - Deve generare frontend component

10. Coding Agent:
    - Riceve project_summary nel prompt (~200 chars)
    - Riceve relevant_summaries da RAG (~2k chars)
    - Genera backend/auth.py
    - Genera frontend/Login.tsx
    
11. Registrazione automatica (come step 4)

---

RISPARMIO TOKEN:
- Prima: 50k+ token per richiesta
- Dopo: ~2k token per richiesta
- Risparmio: 96%!
```

## API Chiave

### Context Agent
```python
# Registra file generato (chiamato da Coding Agent)
context_agent.register_generated_file(file_path, content)

# Ottieni summary per prompt (~200 chars)
summary = context_agent.get_project_summary_for_prompt()

# Check se fullstack
if context_agent.requires_backend_and_frontend():
    # Genera sia backend che frontend
```

### RAG Agent
```python
# Indicizza con summary (non raw code)
rag_agent.index_file_with_summary(file_path, content)

# Query token-efficient
summaries = await rag_agent.get_relevant_summaries("authentication")
# Ritorna ~2k chars invece di 50k
```

### Coding Agent
```python
# Auto-registrazione dopo generazione
result = await coding_agent.generate_patch(file_path, intent)
# → Automaticamente chiama context_agent.register_generated_file()
# → Automaticamente chiama rag_agent.index_file_with_summary()
```

### Orchestrator
```python
# Wiring automatico
orchestrator.add_agent("context_agent")
orchestrator.add_agent("rag_agent")
orchestrator.add_agent("coding")
# → Automaticamente wired: coding → context_agent, rag_agent

# Query high-level
summary = orchestrator.get_project_summary()
is_fullstack = orchestrator.is_fullstack_project()
context = await orchestrator.get_relevant_context("add login")
```

## Configurazione

```python
# Context Agent
ContextAgentConfig(
    track_project_structure=True,  # Memoria persistente
    auto_detect_stack=True,        # Rileva fastapi/react/etc
    persist_memory=True,           # Mantieni tra sessioni
)

# RAG Agent
RAGAgentConfig(
    return_summaries_only=True,    # Riassunti, non codice
    max_summary_chars=500,         # Limite per file
    auto_index_generated=True,     # Indicizza auto dopo generazione
)

# Coding Agent
CodingAgentConfig(
    auto_register_files=True,      # Registra con Context Agent
    auto_index_summaries=True,     # Indicizza con RAG Agent
    use_project_context=True,      # Usa project summary nel prompt
)
```

Nota: nel file `backend/config/default.yaml` RAG e Context Agent sono già abilitati
con provider LLM locale (`ollama`) e VectorDB `chroma`, così puoi usare subito il
flusso a risparmio token.
