# 🛡️ OMNI - Assistant to the Assistant

> **OMNI non è un coding assistant.** GitHub Copilot fa già quello in modo eccellente.
> 
> OMNI è un **guardiano di sicurezza e compliance** che valida il codice e fornisce **contesto intelligente a Copilot**.

---

## 📖 Indice

1. [Cos'è OMNI](#-cosè-omni)
2. [Come Funziona](#-come-funziona)
3. [Quick Start](#-quick-start)
4. [Architettura](#-architettura)
5. [Gli Agenti](#-gli-agenti)
6. [Integrazione con Copilot](#-integrazione-con-copilot)
7. [Configurazione](#-configurazione)
8. [Sviluppo](#-sviluppo)

---

## 🎯 Cos'è OMNI

OMNI è un sistema multi-agente che lavora **insieme** a GitHub Copilot per:

| Funzione | Descrizione |
|----------|-------------|
| 🔒 **Sicurezza** | Scansiona il codice per vulnerabilità (SQL injection, XSS, secrets hardcoded) |
| 📋 **Compliance** | Verifica conformità a regolamenti (GDPR, HIPAA, PCI-DSS) |
| 🧠 **Contesto** | Fornisce a Copilot la conoscenza completa del tuo progetto |
| 📚 **Context Pack (RAG + sintesi)** | Indicizza i file e compila un Context Pack compatto per l'assistente |

### Il Problema che Risolve

Copilot è fantastico nel generare codice, ma:
- ❌ Non conosce le tue policy di sicurezza
- ❌ Non sa quali regolamenti devi rispettare
- ❌ Non ha memoria del tuo progetto
- ❌ Non può validare il codice prima che venga applicato

**OMNI risolve tutto questo.**

---

## 🔄 Come Funziona (Context Pack + On-demand)

### Diagramma del Flusso

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           TU (Developer)                                  │
│                                                                          │
│   1. Apri un progetto in VS Code                                         │
│   2. Chiedi a Copilot di scrivere codice                                 │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         OMNI (Automatico)                                 │
│                                                                          │
│   Quando apri il progetto, OMNI automaticamente:                         │
│                                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│   │   STEP 1    │───▶│   STEP 2    │───▶│   STEP 3    │                 │
│   │   Context   │    │    RAG      │    │  Security   │                 │
│   │   Agent     │    │   Agent     │    │   Agent     │                 │
│   │             │    │             │    │             │                 │
│   │ Analizza    │    │ Indicizza   │    │ Scansiona   │                 │
│   │ struttura   │    │ tutti i     │    │ vulnera-    │                 │
│   │ progetto    │    │ file        │    │ bilità      │                 │
│   └─────────────┘    └─────────────┘    └─────────────┘                 │
│          │                  │                  │                         │
│          │                  │                  │                         │
│          │                  ▼                  │                         │
│          │           ┌─────────────┐           │                         │
│          │           │   STEP 4    │           │                         │
│          └──────────▶│ Compliance  │◀──────────┘                         │
│                      │   Agent     │                                     │
│                      │             │                                     │
│                      │ Verifica    │                                     │
│                      │ regolamenti │                                     │
│                      └─────────────┘                                     │
│                             │                                            │
│                             ▼                                            │
│                      ┌─────────────┐                                     │
│                      │   STEP 5    │                                     │
│                      │  Copilot    │                                     │
│                      │Integration  │                                     │
│                      │             │                                     │
│                      │ Genera file │                                     │
│                      │ di contesto │                                     │
│                      └─────────────┘                                     │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    File Generati per Copilot (Context Pack)              │
│                                                                          │
│   📁 .github/                                                            │
│      └── copilot-instructions.md    ← Copilot legge questo AUTO!         │
│                                                                          │
│   📁 .omni/                                                              │
│      ├── context/                                                        │
│      │   ├── project-overview.md       ← Stack + architettura sintetica  │
│      │   ├── component-map.md          ← Mappa moduli/cartelle           │
│      │   ├── interfaces-and-apis.md    ← Superfici pubbliche (API, funzioni)
│      │   ├── data-model.md             ← Classi/modelli/exports          │
│      │   ├── hotspots.md               ← File prioritari (es. più LOC)   │
│      │   └── file-summaries.md         ← Riassunti dettagliati file x file
│      └── insights/                                                         │
│          ├── security.md               ← Problemi di sicurezza trovati    │
│          └── compliance.md             ← Problemi di compliance trovati   │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        GitHub Copilot                                     │
│                                                                          │
│   Ora Copilot SA:                                                        │
│   ✅ Che tipo di progetto è (backend, frontend, fullstack)               │
│   ✅ Quali framework usi (FastAPI, React, etc.)                          │
│   ✅ Cosa fa ogni file del progetto                                      │
│   ✅ Quali pattern di sicurezza seguire                                  │
│   ✅ Quali regolamenti rispettare                                        │
│   ✅ Quali problemi esistono già nel codice                              │
└──────────────────────────────────────────────────────────────────────────┘
```

### Flusso Semplificato

1. **Apri progetto** → OMNI analizza tutto automaticamente
2. **OMNI genera Context Pack** → `.github/copilot-instructions.md` + `.omni/context/*`
3. **Copilot legge** → Ha contesto completo del tuo progetto
4. **Scrivi codice** → Copilot genera codice migliore perché SA cosa stai facendo
5. **Salvi file** → OMNI ri-analizza i chunk toccati e aggiorna solo le sezioni pertinenti del Context Pack (on-demand synthesis)

---

## 🚀 Quick Start

### Prerequisiti

- Python 3.10+
- Node.js 18+
- VS Code
- (Opzionale) Ollama per LLM locale

### Installazione

```bash
# 1. Clona il repository
git clone https://github.com/your-repo/OMNI.git
cd OMNI

# 2. Crea un virtualenv (consigliato)
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3. Installa le dipendenze backend
pip install --upgrade pip
pip install -r backend/requirements.txt
# Se la build di llama-cpp-python fallisce, lascialo fuori: OMNI funziona con
# OpenAI/Anthropic/Ollama senza quel pacchetto.

# 4. Configura l'LLM (scegli uno)

# Opzione A: Ollama (gratuito, locale)
# Installa Ollama da https://ollama.ai
ollama pull phi
# oppure: ollama pull llama2, ollama pull mistral, etc.

# Opzione B: OpenAI
export OPENAI_API_KEY="sk-your-key"

# Opzione C: Anthropic
export ANTHROPIC_API_KEY="sk-ant-your-key"
```

### Avvio

```bash
# Terminal 1: Avvia il backend
cd OMNI
python -m backend.server.main

# Output:
# INFO - Starting OMNI backend server
# INFO - WebSocket: ws://localhost:8765
# INFO - HTTP: http://localhost:8766
```

```bash
# Terminal 2: Avvia l'estensione VS Code
cd OMNI/vscode-extension
npm install
npm run compile
# Premi F5 in VS Code per lanciare l'estensione
```

### Configurazione Ollama (Consigliato per Iniziare)

Ollama è **gratuito** e funziona **offline**. Perfetto per iniziare!

1. Scarica Ollama: https://ollama.ai
2. Installa un modello:
   ```bash
   ollama pull phi      # Piccolo e veloce (3GB)
   ollama pull llama2   # Più potente (7GB)
   ollama pull mistral  # Ottimo bilanciamento (4GB)
   ```
3. Modifica `backend/config/default.yaml`:
   ```yaml
   llm:
     provider: "local"
     local:
       base_url: "http://localhost:11434"
       model: "phi"  # o llama2, mistral, etc.
   ```

---

## 🏗️ Architettura

### Struttura delle Cartelle

```
OMNI/
├── backend/                    # Server Python
│   ├── agents/                 # Implementazione agenti
│   │   ├── context_agent.py    # Analizza struttura progetto
│   │   ├── rag_agent.py        # Indicizzazione e ricerca
│   │   ├── security_agent.py   # Scansione vulnerabilità
│   │   ├── compliance_agent.py # Verifica compliance
│   │   ├── orchestrator.py     # Coordina gli agenti
│   │   └── workflow.py         # Pipeline completa
│   │
│   ├── integrations/           # Integrazioni esterne
│   │   ├── copilot_integration.py  # Genera file per Copilot
│   │   └── file_analyzer.py        # Analisi dettagliata file
│   │
│   ├── adapters/               # Adapter per servizi esterni
│   │   ├── llm/                # OpenAI, Anthropic, Ollama
│   │   └── vectordb/           # Chroma, FAISS, Qdrant
│   │
│   ├── server/                 # WebSocket + HTTP server
│   │   ├── main.py             # Entry point
│   │   └── websocket_handler.py # Gestione messaggi
│   │
│   └── config/                 # Configurazione
│       └── default.yaml        # Settings
│
├── vscode-extension/           # Estensione VS Code
│   └── src/
│       ├── extension.ts        # Entry point
│       ├── views/              # UI (chat, tree view)
│       └── backend/            # Comunicazione WebSocket
│
├── .github/
│   └── copilot-instructions.md # [AUTO-GENERATO] Istruzioni per Copilot
│
└── .omni/                      # [AUTO-GENERATO] File di contesto
    ├── context/
    │   ├── project-overview.md
    │   └── file-summaries.md
    └── insights/
        ├── security.md
        └── compliance.md
```

### Comunicazione

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│   VS Code       │◄──────────────────▶│   Backend       │
│   Extension     │    ws://8765       │   Python        │
│                 │                    │                 │
│   - UI Chat     │                    │   - Agenti      │
│   - File Watch  │                    │   - LLM         │
│   - Commands    │                    │   - VectorDB    │
└─────────────────┘                    └─────────────────┘
```

---

## 🤖 Gli Agenti

OMNI usa 4 agenti specializzati che lavorano insieme:

### 1. 🧠 Context Agent

**Cosa fa:** Analizza la struttura del progetto e crea una "memoria"

**Input:** File del progetto
**Output:** Struttura progetto, framework usati, pattern riconosciuti

```
Esempio output:
- Project Type: fullstack
- Backend: FastAPI
- Frontend: React  
- Database: PostgreSQL
- Files: 45 backend, 32 frontend
```

**Caratteristiche:**
- ✅ Read-only (non modifica file)
- ✅ Funziona senza LLM (pattern matching)
- ✅ Genera riassunti dettagliati per senior developers

### 2. 📚 RAG Agent

**Cosa fa:** Indicizza tutti i file per permettere ricerche semantiche

**Input:** File del progetto + query
**Output:** File/snippet rilevanti per la query

```
Esempio:
Query: "Come gestisco l'autenticazione?"
Output: 
- backend/auth/jwt_handler.py (rilevanza: 95%)
- backend/routes/login.py (rilevanza: 87%)
```

**Caratteristiche:**
- ✅ Usa vector database (Chroma/FAISS/Qdrant)
- ✅ Ricerca semantica, non solo keyword
- ✅ Indicizza automaticamente quando apri progetto

### 3. 🔒 Security Agent

**Cosa fa:** Scansiona il codice per vulnerabilità di sicurezza

**Cosa cerca:**
| Vulnerabilità | Esempio |
|---------------|---------|
| SQL Injection | `query = "SELECT * FROM users WHERE id=" + user_input` |
| XSS | `innerHTML = userInput` |
| Secrets hardcoded | `password = "admin123"` |
| Command Injection | `os.system(user_input)` |
| Insecure Deserialization | `pickle.loads(data)` |

**Output:**
```
🔴 CRITICAL: Hardcoded password in config.py:15
🟠 HIGH: SQL injection in users.py:42
🟡 MEDIUM: Missing input validation in api.py:28
```

**Caratteristiche:**
- ✅ Pattern matching (funziona senza LLM)
- ✅ Può usare LLM per analisi più profonda
- ✅ Integrazione Semgrep (opzionale)

### 4. 📋 Compliance Agent

**Cosa fa:** Verifica che il codice rispetti regolamenti

**Regolamenti supportati:**
| Regolamento | Descrizione |
|-------------|-------------|
| GDPR | Protezione dati EU |
| HIPAA | Dati sanitari USA |
| PCI-DSS | Pagamenti carte |
| SOC2 | Sicurezza cloud |

**Cosa controlla:**
- Gestione dati personali (PII)
- Logging di dati sensibili
- Crittografia password
- Retention dei dati
- Consenso utente

**Output:**
```
📋 GDPR Violation: Logging email in auth.py:23
📋 PCI-DSS Warning: Credit card not encrypted in payment.py:45
```

---

## 🤝 Integrazione con Copilot

### Come Funziona

OMNI genera automaticamente file che **Copilot legge**:

#### `.github/copilot-instructions.md`

Questo file viene **letto automaticamente** da GitHub Copilot quando lavori nel progetto.

```markdown
# Copilot Instructions for this Project

## Project Overview
**Project Type:** Python Backend
**Backend:** FastAPI
**Database:** PostgreSQL

## Security Requirements
When generating code, ALWAYS:
- Use parameterized queries (never string concatenation for SQL)
- Validate and sanitize all user inputs
- Never hardcode secrets, passwords, or API keys

## ⚠️ Known Security Issues (Fix These!)
- **[CRITICAL]** Hardcoded secret in config.py
- **[HIGH]** SQL injection in users.py
```

#### `.omni/context/file-summaries.md`

Riassunti dettagliati di ogni file:

```markdown
### `backend/auth/jwt_handler.py`
**Language:** Python | **Lines:** 145

**Purpose:** JWT token management

**Classes:**
- `JWTHandler`: Manages JWT creation and validation
  - Methods: create_token, validate_token, refresh_token

**Functions:**
- `create_access_token(user_id, expires_delta)` → `str`
- `decode_token(token)` → `dict`

**Key Imports:** jose, datetime, config

**⚠️ Security Notes:**
- Handles sensitive authentication data
```

### Risultato

Quando chiedi a Copilot:
> "Aggiungi un endpoint per il login"

Copilot **SA**:
- Che usi FastAPI (non Flask)
- Che hai già un `JWTHandler` 
- Che devi usare query parametrizzate
- Che non devi hardcodare secrets
- Quali pattern di sicurezza seguire

**Risultato:** Codice migliore, più sicuro, più consistente!

---

## ⚙️ Configurazione

### File: `backend/config/default.yaml`

```yaml
# ===== Server =====
server:
  host: "localhost"
  port: 8765
  cors_origins:
    - "vscode-webview://*"
    - "http://localhost:*"
  debug: false
  log_level: "INFO"

# ===== LLM Provider =====
llm:
  provider: "local"  # local | openai | anthropic
  
  openai:
    api_key: ${OPENAI_API_KEY}
    model: "gpt-4-turbo-preview"
    embedding_model: "text-embedding-3-small"
    max_tokens: 4096
    temperature: 0.7
  
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: "claude-3-sonnet-20240229"
    max_tokens: 4096
    temperature: 0.7
  
  local:
    provider_type: "ollama"  # lmstudio, ollama, llamacpp
    base_url: "http://localhost:11434/v1"
    model: "phi"
    temperature: 0.7

# ===== Vector Database =====
vectordb:
  provider: "chroma"  # chroma | faiss | qdrant
  
  qdrant:
    url: ${QDRANT_URL}
    api_key: ${QDRANT_API_KEY}
    prefer_grpc: false
  
  chroma:
    persist_path: "./data/chroma"
  
  faiss:
    persist_path: "./data/faiss"
  
  default_collection: "omni_documents"
  default_dimension: 1536

# ===== RAG =====
rag:
  enabled: true
  chunk_size: 512
  chunk_overlap: 50
  top_k: 5
  score_threshold: 0.7

# ===== Agenti =====
agents:
  plugin_dirs:
    - "./plugins/agents"
    - "~/.omni/agents"
  default_agents:
    - "context_agent"
    - "rag_agent"
    - "security"
    - "compliance"
    - "assistant"
    - "code_agent"
    - "planner"

# ===== Feature Flags =====
features:
  enable_streaming: true
  enable_tool_use: true
  enable_multi_agent: true
  enable_rag: true
  enable_code_execution: false
```

### Variabili d'Ambiente

Tutte le configurazioni possono essere sovrascritte con variabili d'ambiente con prefisso `OMNI_`:

```bash
# LLM
export OMNI_LLM__PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Vector DB
export OMNI_VECTORDB__PROVIDER=qdrant
export QDRANT_URL=https://your-qdrant-host:6333

# Server
export OMNI_SERVER__HOST=0.0.0.0
export OMNI_SERVER__PORT=9000
```

---

## 👨‍💻 Sviluppo

### Aggiungere un Nuovo Agente

1. Crea file in `backend/agents/`:

```python
# backend/agents/my_agent.py
from backend.core.interfaces.agent import AgentBase, AgentMetadata

class MyAgent(AgentBase):
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            id="my_agent",
            name="My Custom Agent",
            description="Does something cool",
        )
    
    async def process(self, message, context):
        # La tua logica qui
        pass
```

2. Registra in `backend/agents/__init__.py`

### Test

```bash
# Esegui test
python -m pytest

# Test specifico
python -m pytest backend/tests/agents/test_security_agent.py
```

Stato attuale: 46 test verdi su Python 3.12 (gen 2026).

### Debug

```bash
# Avvia con debug logging
OMNI_LOG_LEVEL=DEBUG python -m backend.server.main
```

---

## 📝 Messaggi WebSocket

### Dal Client al Server

| Tipo | Descrizione | Payload |
|------|-------------|---------|
| `chat` | Messaggio chat | `{content: "...", context: {...}}` |
| `scan_workspace` | Scansiona progetto | `{folder_path: "...", files: [...]}` |
| `analyze_code` | Analizza codice | `{code: "...", file_path: "..."}` |

### Dal Server al Client

| Tipo | Descrizione | Payload |
|------|-------------|---------|
| `chat_response` | Risposta chat | `{content: "...", sender: "..."}` |
| `agent_status` | Stato agente | `{agent_id: "...", status: "..."}` |
| `security_findings` | Vulnerabilità | `{findings: [...]}` |
| `error` | Errore | `{message: "..."}` |

---

## 🆘 Troubleshooting

### Il server non parte

```bash
# Controlla se la porta è occupata
netstat -an | grep 8765

# Killa processi Python
pkill -f "python -m backend"

# Windows
Get-Process -Name python | Stop-Process -Force
```

### Ollama non risponde

```bash
# Verifica che Ollama sia attivo
curl http://localhost:11434/api/tags

# Riavvia Ollama
ollama serve
```

### L'estensione non si connette

1. Verifica che il backend sia attivo
2. Controlla la console di VS Code (Help > Toggle Developer Tools)
3. Verifica che il WebSocket sia su `ws://localhost:8765`

---

## 📜 Licenza

MIT License - Vedi [LICENSE](LICENSE) per dettagli.

---

## 🙏 Credits

- [GitHub Copilot](https://github.com/features/copilot) - Il miglior coding assistant
- [Ollama](https://ollama.ai) - LLM locali facili
- [LlamaIndex](https://llamaindex.ai) - RAG framework
- [Semgrep](https://semgrep.dev) - Security scanning

---

**Made with ❤️ by the OMNI Team**
