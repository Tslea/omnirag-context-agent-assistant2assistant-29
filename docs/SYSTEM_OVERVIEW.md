# OMNI - Guida Completa al Sistema

**Versione**: 1.0  
**Data**: 10 Gennaio 2026  
**Destinatari**: Manager, Product Owner, Stakeholder non-tecnici

---

## Indice

1. [Cos'è OMNI](#1-cosè-omni)
2. [Architettura ad Alto Livello](#2-architettura-ad-alto-livello)
3. [Gli Agenti: Chi Fa Cosa](#3-gli-agenti-chi-fa-cosa)
4. [Flussi Operativi](#4-flussi-operativi)
5. [Sistema di Sicurezza e Controllo](#5-sistema-di-sicurezza-e-controllo)
6. [Monitoraggio e Osservabilità](#6-monitoraggio-e-osservabilità)
7. [Gestione degli Errori](#7-gestione-degli-errori)
8. [Configurazione e Personalizzazione](#8-configurazione-e-personalizzazione)
9. [Domande Frequenti](#9-domande-frequenti)
10. [Glossario](#10-glossario)

---

## 1. Cos'è OMNI

### 1.1 In Breve

OMNI è un **assistente intelligente per sviluppatori** che si integra in Visual Studio Code (l'editor di codice). Funziona come un "team di esperti virtuali" che lavora insieme per:

- ✅ **Analizzare** il codice esistente
- ✅ **Identificare** problemi di sicurezza
- ✅ **Verificare** la conformità a normative (GDPR, etc.)
- ✅ **Suggerire** modifiche al codice
- ✅ **Mai scrivere direttamente** nei file (solo proposte)

### 1.2 Filosofia Fondamentale

```
🎯 OMNI NON scrive mai codice direttamente nei file.
   Propone sempre, l'umano decide sempre.
```

Questa scelta garantisce che:
- Il programmatore mantiene **controllo totale**
- Ogni modifica è **revisionata** prima di essere applicata
- Non ci sono **sorprese** nel codice

### 1.3 Il Problema che Risolve

| Situazione Tradizionale | Con OMNI |
|------------------------|----------|
| Lo sviluppatore deve ricordare tutte le regole di sicurezza | OMNI le controlla automaticamente |
| Le verifiche di conformità GDPR sono manuali e lunghe | OMNI le fa in tempo reale |
| Trovare codice rilevante in progetti grandi è difficile | OMNI cerca e riassume intelligentemente |
| GitHub Copilot genera codice ma non lo valida | OMNI valida il codice PRIMA che venga applicato |

---

## 2. Architettura ad Alto Livello

### 2.1 Schema del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        VISUAL STUDIO CODE                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Estensione OMNI (Frontend)                   │   │
│  │  • Chat Panel (interfaccia utente)                        │   │
│  │  • Vista Agenti (stato del sistema)                       │   │
│  │  • Storico Conversazioni                                  │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │ WebSocket                            │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                Backend OMNI (Python)                      │   │
│  │                                                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │   │
│  │  │ Context │ │   RAG   │ │Security │ │Compliance│        │   │
│  │  │  Agent  │ │  Agent  │ │  Agent  │ │  Agent  │        │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘        │   │
│  │       │           │           │           │              │   │
│  │       └───────────┴─────┬─────┴───────────┘              │   │
│  │                         │                                 │   │
│  │                   ORCHESTRATOR                            │   │
│  │              (Coordinatore Centrale)                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 I Tre Strati

| Strato | Cosa Fa | Analogia |
|--------|---------|----------|
| **Estensione VS Code** | Interfaccia utente, chat, visualizzazioni | La "faccia" del sistema |
| **Backend Python** | Logica, agenti AI, analisi | Il "cervello" del sistema |
| **Servizi Esterni** | LLM (GPT/Claude), Database vettoriali | La "memoria" e "intelligenza" |

### 2.3 Comunicazione tra Componenti

Il sistema usa **WebSocket** per comunicare in tempo reale:

```
Utente digita messaggio
        │
        ▼
Estensione VS Code ──WebSocket──▶ Backend Python
        │                              │
        │                              ▼
        │                     Orchestrator smista
        │                     agli Agenti giusti
        │                              │
        │                              ▼
        │                     Agenti elaborano
        │                              │
        ◀──────────────────────────────┘
        │
        ▼
Risposta mostrata nel Chat Panel
```

---

## 3. Gli Agenti: Chi Fa Cosa

OMNI è composto da **5 agenti specializzati**. Ogni agente è un esperto in un dominio specifico.

### 3.1 Tabella Riassuntiva

| Agente | Ruolo | Input | Output |
|--------|-------|-------|--------|
| **Context Agent** | Memoria del progetto | Messaggi, file | Riassunti, contesto |
| **RAG Agent** | Ricerca intelligente | Query | Snippet di codice rilevanti |
| **Security Agent** | Trova vulnerabilità | Codice | Lista problemi di sicurezza |
| **Compliance Agent** | Verifica normative | Codice | Violazioni GDPR/altre |
| **Coding Agent** | Propone modifiche | Richieste | Patch (diff) da approvare |

### 3.2 Context Agent - "La Memoria"

**Cosa fa**: Tiene traccia di tutto ciò che succede nella sessione.

**Responsabilità**:
- Ricorda quali file sono stati menzionati
- Traccia il tipo di progetto (React? Django? Node?)
- Mantiene una lista delle funzionalità completate
- Estrae informazioni importanti dalle conversazioni

**Esempio pratico**:
```
Utente: "Sto lavorando su un'app React con backend FastAPI"

Context Agent memorizza:
├── Tipo progetto: fullstack
├── Frontend: React
├── Backend: FastAPI
└── Questo contesto viene condiviso con gli altri agenti
```

**Dati che mantiene**:
- Struttura del progetto (cartelle, file principali)
- Pattern architetturali rilevati
- Convenzioni del codice
- Funzionalità già implementate

### 3.3 RAG Agent - "Il Ricercatore"

**Cosa fa**: Cerca informazioni rilevanti nel codice e nelle knowledge base.

**RAG = Retrieval-Augmented Generation**:
1. **Retrieval**: Cerca snippet rilevanti
2. **Augmented**: Li usa per arricchire il contesto
3. **Generation**: Permette risposte più accurate

**Domini di ricerca**:
| Dominio | Cosa contiene | Quando usato |
|---------|---------------|--------------|
| `code` | Il codice del progetto | Sempre come default |
| `security` | Regole di sicurezza OWASP | Query su sicurezza |
| `compliance` | Normative GDPR, HIPAA | Query su conformità |
| `docs` | Documentazione | Query generiche |

**Come seleziona il dominio**:
```
Query: "Come gestisco i dati personali?"
        │
        ▼
Analisi pattern nella query
        │
        ├── Contiene "dati personali" → dominio: compliance
        ├── Contiene "sicurezza" → dominio: security
        └── Default → dominio: code
```

**Ottimizzazione Token**:
- NON invia codice raw (costoso)
- Invia RIASSUNTI (economico)
- ~200 caratteri invece di ~50.000

### 3.4 Security Agent - "Il Guardiano"

**Cosa fa**: Analizza il codice per trovare vulnerabilità di sicurezza.

**Strumento principale**: Semgrep (analizzatore statico)

**Tipi di problemi che trova**:

| Categoria | Esempi | Gravità |
|-----------|--------|---------|
| **SQL Injection** | Query SQL con input non sanificati | 🔴 Critica |
| **XSS** | HTML non escaped | 🔴 Critica |
| **Hardcoded Secrets** | Password nel codice | 🟠 Alta |
| **Weak Crypto** | MD5, SHA1 per password | 🟠 Alta |
| **Path Traversal** | Accesso file non validato | 🟠 Alta |
| **Insecure Config** | Debug attivo in produzione | 🟡 Media |

**Output esempio**:
```
🔴 CRITICO: SQL Injection
   File: api/users.py, Linea: 45
   Problema: Input utente passato direttamente alla query
   Raccomandazione: Usare query parametrizzate

🟠 ALTO: Hardcoded Secret
   File: config.py, Linea: 12
   Problema: API key visibile nel codice
   Raccomandazione: Usare variabili d'ambiente
```

**Flusso di validazione**:
```
Codice da validare
        │
        ▼
┌───────────────────┐
│  Security Agent   │
│                   │
│  1. Semgrep scan  │
│  2. Pattern check │
│  3. Context check │
└─────────┬─────────┘
          │
          ▼
    ┌─────┴─────┐
    │           │
    ▼           ▼
 SICURO     PROBLEMI
   │           │
   ▼           ▼
 "OK ✓"    Lista findings
```

### 3.5 Compliance Agent - "Il Revisore Legale"

**Cosa fa**: Verifica che il codice rispetti le normative (GDPR, HIPAA, PCI-DSS).

**Come funziona**:
1. Carica **ruleset** esterni (file YAML/JSON)
2. Applica le regole al codice
3. Segnala violazioni

**Regole GDPR esempio** (da `gdpr-sample.yaml`):

| Regola | Cosa verifica |
|--------|---------------|
| `personal_data_logging` | Log non devono contenere dati personali |
| `consent_required` | Raccolta dati richiede consenso esplicito |
| `data_retention` | Dati devono avere scadenza definita |
| `encryption_required` | Dati sensibili devono essere crittografati |

**Output esempio**:
```
⚠️ GDPR Violazione: personal_data_logging
   File: services/logger.py, Linea: 23
   Problema: Email utente presente nei log
   Articolo: GDPR Art. 5(1)(f) - Integrità e riservatezza
   Raccomandazione: Rimuovere o anonimizzare i dati personali nei log
```

### 3.6 Coding Agent - "Lo Sviluppatore"

**Cosa fa**: Genera proposte di modifica al codice.

**IMPORTANTE - Cosa NON fa**:
- ❌ NON scrive direttamente nei file
- ❌ NON applica modifiche automaticamente
- ❌ NON bypassa la review umana

**Cosa FA**:
- ✅ Genera "patch" (differenze)
- ✅ Mostra cosa cambierebbe
- ✅ Aspetta approvazione umana

**Formato output (Unified Diff)**:
```diff
--- a/api/users.py
+++ b/api/users.py
@@ -45,7 +45,7 @@
 def get_user(user_id):
-    query = f"SELECT * FROM users WHERE id = {user_id}"
+    query = "SELECT * FROM users WHERE id = %s"
-    cursor.execute(query)
+    cursor.execute(query, (user_id,))
     return cursor.fetchone()
```

**Questo formato permette**:
- Vedere esattamente cosa cambia (righe con `-` e `+`)
- Decidere se accettare o rifiutare
- Applicare solo parti della modifica

---

## 4. Flussi Operativi

### 4.1 Flusso: Analisi di un File

```
                    UTENTE
                      │
                      │ "Analizza api/users.py"
                      ▼
              ┌───────────────┐
              │  Orchestrator │
              └───────┬───────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ Context │  │Security │  │Compliance│
   │  Agent  │  │  Agent  │  │  Agent  │
   └────┬────┘  └────┬────┘  └────┬────┘
        │             │             │
        │ Aggiorna    │ Scan       │ Check
        │ contesto    │ sicurezza  │ normative
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
              RISPOSTA AGGREGATA
              ├── Contesto file
              ├── 3 problemi sicurezza
              └── 1 violazione GDPR
```

**Tempo tipico**: 2-5 secondi

### 4.2 Flusso: Validazione Codice Copilot

Quando GitHub Copilot genera codice, OMNI può validarlo PRIMA che venga inserito:

```
GitHub Copilot genera codice
              │
              ▼
      ┌───────────────┐
      │ OMNI Intercept│
      └───────┬───────┘
              │
              ▼
      ┌───────────────┐
      │Security Agent │◄── Scansione vulnerabilità
      └───────┬───────┘
              │
        ┌─────┴─────┐
        │           │
        ▼           ▼
     SICURO      PROBLEMI
        │           │
        ▼           ▼
   "Applica"   "Attenzione!
    codice     Trovati problemi:
               - SQL Injection
               - Hardcoded secret
               
               Vuoi applicare comunque?"
```

**Beneficio**: Il codice non sicuro viene segnalato PRIMA di entrare nel progetto.

### 4.3 Flusso: Richiesta di Modifica

```
UTENTE: "Aggiungi autenticazione JWT"
              │
              ▼
      ┌───────────────┐
      │  Orchestrator │
      └───────┬───────┘
              │
              ▼
      ┌───────────────┐
      │ Context Agent │◄── Recupera info progetto
      └───────┬───────┘    (stack: FastAPI, React)
              │
              ▼
      ┌───────────────┐
      │   RAG Agent   │◄── Cerca pattern JWT esistenti
      └───────┬───────┘    nel codice
              │
              ▼
      ┌───────────────┐
      │ Coding Agent  │◄── Genera patch con
      └───────┬───────┘    modifiche proposte
              │
              ▼
      ┌───────────────┐
      │Security Agent │◄── Valida che la proposta
      └───────┬───────┘    sia sicura
              │
              ▼
      PROPOSTA FINALE
      ├── Diff per auth/jwt.py (nuovo file)
      ├── Diff per api/routes.py (modifiche)
      └── Validazione sicurezza: ✓ OK
```

### 4.4 Flusso: Scansione Workspace

```
UTENTE: "Scansiona tutto il progetto per problemi di sicurezza"
              │
              ▼
      ┌───────────────┐
      │  Orchestrator │
      └───────┬───────┘
              │
              ▼
      ┌───────────────┐
      │ Context Agent │◄── Elenca tutti i file
      └───────┬───────┘
              │
              ▼
    Per ogni file rilevante:
              │
              ▼
      ┌───────────────┐
      │Security Agent │◄── Semgrep + Pattern
      └───────┬───────┘
              │
              ▼
      ┌───────────────┐
      │Compliance Agt │◄── Ruleset GDPR/altro
      └───────┬───────┘
              │
              ▼
      REPORT COMPLETO
      ├── 47 file analizzati
      ├── 12 problemi sicurezza
      │   ├── 3 critici
      │   ├── 5 alti
      │   └── 4 medi
      └── 4 violazioni conformità
```

---

## 5. Sistema di Sicurezza e Controllo

### 5.1 Principio del Minimo Privilegio

```
┌─────────────────────────────────────────────┐
│              OMNI PUÒ:                       │
├─────────────────────────────────────────────┤
│ ✅ Leggere file del workspace                │
│ ✅ Analizzare codice                         │
│ ✅ Proporre modifiche (come diff)            │
│ ✅ Cercare in database vettoriali            │
│ ✅ Chiamare API LLM (OpenAI/Anthropic)       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│              OMNI NON PUÒ:                   │
├─────────────────────────────────────────────┤
│ ❌ Scrivere/modificare file                  │
│ ❌ Eseguire comandi nel terminale            │
│ ❌ Accedere a file fuori dal workspace       │
│ ❌ Inviare dati a server non autorizzati     │
│ ❌ Installare pacchetti/dipendenze           │
└─────────────────────────────────────────────┘
```

### 5.2 Validazione delle Modifiche

Ogni modifica proposta passa attraverso 3 livelli:

```
Modifica proposta
        │
        ▼
LIVELLO 1: Validazione Sintattica
├── Il codice è sintatticamente corretto?
├── Le importazioni esistono?
└── I tipi sono compatibili?
        │
        ▼
LIVELLO 2: Validazione Sicurezza
├── Introduce vulnerabilità note?
├── Usa pattern pericolosi?
└── Espone dati sensibili?
        │
        ▼
LIVELLO 3: Approvazione Umana
├── Diff mostrato all'utente
├── Spiegazione delle modifiche
└── Utente decide: accetta/rifiuta
```

### 5.3 Gestione delle Dipendenze tra Agenti

Gli agenti hanno dipendenze esplicite. Il sistema valida che siano soddisfatte:

```
        ┌─────────────┐
        │   Context   │
        │    Agent    │ ◄── Nessuna dipendenza
        └──────┬──────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
   ┌─────────┐  ┌─────────┐
   │   RAG   │  │   ...   │ ◄── Nessuna dipendenza
   │  Agent  │  │         │
   └────┬────┘  └─────────┘
        │
        │
        ▼
   ┌─────────┐
   │Security │
   │  Agent  │ ◄── Dipende da: Context, RAG
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │Compliance│
   │  Agent  │ ◄── Dipende da: Context, RAG
   └─────────┘
```

**Se una dipendenza manca**, il sistema:
1. Segnala l'errore all'avvio
2. Non permette l'esecuzione
3. Indica esattamente cosa manca

---

## 6. Monitoraggio e Osservabilità

### 6.1 Correlation ID

Ogni richiesta ha un **ID univoco** che la traccia attraverso tutto il sistema:

```
Richiesta utente
        │
        │ correlation_id = "req-abc123"
        ▼
┌───────────────────────────────────────────┐
│ Context Agent  [req-abc123] Processing... │
│ RAG Agent      [req-abc123] Searching...  │
│ Security Agent [req-abc123] Scanning...   │
└───────────────────────────────────────────┘
```

**Utilità**: Se qualcosa va storto, il correlation_id permette di tracciare esattamente cosa è successo.

### 6.2 Metriche Raccolte

| Metrica | Cosa misura | Perché importante |
|---------|-------------|-------------------|
| `agent_execution_time` | Tempo per agente | Performance |
| `agent_errors` | Errori per agente | Stabilità |
| `rag_cache_hits` | Cache hit rate | Efficienza |
| `total_requests` | Richieste totali | Carico |
| `security_findings` | Problemi trovati | Sicurezza |

### 6.3 Request Tracing

Ogni richiesta genera un "trace" che mostra:

```
RequestTrace: req-abc123
├── Span: workflow.analyze (150ms)
│   ├── Span: context.extract (20ms) ✓
│   ├── Span: rag.search (45ms) ✓
│   ├── Span: security.scan (60ms) ✓
│   └── Span: compliance.check (25ms) ✓
└── Total: 150ms, Status: SUCCESS
```

---

## 7. Gestione degli Errori

### 7.1 Tipi di Errori

| Tipo | Causa | Recuperabile? | Azione |
|------|-------|---------------|--------|
| **Timeout** | Operazione troppo lenta | ✅ Sì | Retry automatico |
| **Rate Limit** | Troppe richieste API | ✅ Sì | Attesa + retry |
| **Validation** | Input non valido | ❌ No | Messaggio utente |
| **Configuration** | Config errata | ❌ No | Fix config |
| **Fatal** | Errore critico | ❌ No | Log + alert |

### 7.2 Strategia di Retry

Per errori recuperabili, il sistema riprova automaticamente:

```
Tentativo 1 ──FAIL──▶ Attesa 1 secondo
                           │
                           ▼
Tentativo 2 ──FAIL──▶ Attesa 2 secondi
                           │
                           ▼
Tentativo 3 ──FAIL──▶ Attesa 4 secondi
                           │
                           ▼
Tentativo 4 ──FAIL──▶ Errore definitivo
                      all'utente
```

**Backoff esponenziale**: ogni retry attende il doppio del precedente.

### 7.3 Timeout Management

Ogni operazione ha un **budget di tempo**:

```
Richiesta totale: 5 minuti di budget
        │
        ├── Context: max 60 secondi
        ├── RAG: max 120 secondi
        ├── Security: max 120 secondi
        └── Compliance: max 60 secondi

Se un agente supera il suo tempo:
├── Viene interrotto
├── Risultato parziale (se disponibile) viene usato
└── Warning mostrato all'utente
```

---

## 8. Configurazione e Personalizzazione

### 8.1 File di Configurazione Principale

Percorso: `backend/config/default.yaml`

**Sezioni principali**:

```yaml
# Configurazione LLM
llm:
  provider: "openai"           # openai, anthropic, local
  model: "gpt-4"               # Modello da usare
  temperature: 0.7             # Creatività (0-1)
  max_tokens: 4096             # Lunghezza max risposta

# Configurazione Agenti
agents:
  context:
    enabled: true
    max_history: 10            # Messaggi in memoria
  
  security:
    enabled: true
    semgrep_enabled: true      # Usare Semgrep
    llm_enabled: false         # Analisi LLM aggiuntiva
  
  compliance:
    enabled: true
    rulesets:
      - "gdpr-sample.yaml"     # Ruleset da caricare
  
  rag:
    enabled: false             # Disabilitato di default
    top_k: 5                   # Risultati per ricerca

# Timeout
timeouts:
  request: 300                 # 5 minuti max per richiesta
  agent: 60                    # 1 minuto max per agente
```

### 8.2 Ruleset di Compliance

I ruleset sono file YAML/JSON che definiscono regole:

```yaml
# rulesets/gdpr-sample.yaml
name: "GDPR Basic Rules"
version: "1.0"

rules:
  - id: personal_data_logging
    name: "No Personal Data in Logs"
    severity: high
    patterns:
      - "logger.*email"
      - "log.*password"
    message: "Non loggare dati personali"
    reference: "GDPR Art. 5(1)(f)"
```

**Come aggiungere regole custom**:
1. Creare file `.yaml` in `backend/rulesets/`
2. Definire regole con pattern e messaggi
3. Aggiungere al config `compliance.rulesets`

### 8.3 Abilitare/Disabilitare Funzionalità

| Funzionalità | Config Key | Default | Note |
|--------------|-----------|---------|------|
| Security scanning | `agents.security.enabled` | ✅ On | |
| Semgrep | `agents.security.semgrep_enabled` | ✅ On | Richiede Semgrep installato |
| Compliance check | `agents.compliance.enabled` | ✅ On | |
| RAG search | `agents.rag.enabled` | ❌ Off | Richiede vector DB |
| LLM domain selection | `agents.rag.use_llm_for_domain_selection` | ❌ Off | Risparmia token |

---

## 9. Domande Frequenti

### Q: OMNI può scrivere codice malevolo nei miei file?
**R**: No. OMNI non ha la capacità di scrivere nei file. Può solo proporre modifiche che l'utente deve approvare manualmente.

### Q: I miei dati vengono inviati a server esterni?
**R**: Il codice viene inviato solo a:
- Il provider LLM configurato (OpenAI/Anthropic) per l'analisi
- Nessun altro server

Puoi usare un LLM locale (Ollama) per zero trasmissione dati.

### Q: Quanto costa usare OMNI?
**R**: OMNI stesso è gratuito. I costi sono:
- API LLM: secondo il provider (OpenAI, Anthropic)
- Infrastruttura: se self-hosted

OMNI è progettato per **minimizzare i token** usati tramite:
- Cache delle risposte
- Riassunti invece di codice raw
- Pattern matching invece di LLM dove possibile

### Q: Cosa succede se il backend va in crash?
**R**: 
- L'estensione VS Code rimane attiva
- Mostra un errore di connessione
- Si riconnette automaticamente quando il backend torna online
- Nessun dato viene perso (il codice è nei file)

### Q: Posso usare OMNI offline?
**R**: Parzialmente:
- ✅ Security scanning con Semgrep (locale)
- ✅ Compliance checking (locale)
- ❌ Funzionalità che richiedono LLM

Con LLM locale (Ollama): ✅ 100% offline

### Q: OMNI funziona con qualsiasi linguaggio?
**R**: Sì, ma con supporto variabile:
- **Ottimo**: Python, JavaScript, TypeScript
- **Buono**: Java, Go, Rust, C#
- **Base**: Altri (analisi sintattica generica)

---

## 10. Glossario

| Termine | Significato |
|---------|-------------|
| **Agent** | Componente specializzato che svolge un compito specifico |
| **Orchestrator** | Coordinatore che smista il lavoro agli agenti |
| **LLM** | Large Language Model - modello AI come GPT-4 o Claude |
| **RAG** | Retrieval-Augmented Generation - ricerca + generazione |
| **Semgrep** | Tool di analisi statica del codice |
| **WebSocket** | Protocollo per comunicazione real-time |
| **Diff/Patch** | Formato che mostra differenze tra file |
| **Vector DB** | Database per ricerca semantica |
| **Token** | Unità di testo per LLM (~4 caratteri) |
| **Correlation ID** | Identificatore univoco per tracciare richieste |
| **Ruleset** | Set di regole per compliance checking |
| **Timeout** | Limite di tempo per un'operazione |
| **Retry** | Tentativo ripetuto dopo un errore |
| **Backoff** | Attesa crescente tra retry |

---

## Appendice A: Diagramma Completo del Sistema

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                              VISUAL STUDIO CODE                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        ESTENSIONE OMNI                                  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │ │
│  │  │  Chat View   │  │ Agents View  │  │ History View │                  │ │
│  │  │              │  │              │  │              │                  │ │
│  │  │ [User input] │  │ ● Context ✓  │  │ > Session 1  │                  │ │
│  │  │ [AI reply]   │  │ ● RAG ✓      │  │ > Session 2  │                  │ │
│  │  │              │  │ ● Security ✓ │  │              │                  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                  │ │
│  │                                                                         │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │ │
│  │  │ Event Bus       │  │ WebSocket Client│  │ Command Handler │        │ │
│  │  │ (comunicazione) │  │ (connessione)   │  │ (azioni utente) │        │ │
│  │  └─────────────────┘  └────────┬────────┘  └─────────────────┘        │ │
│  └─────────────────────────────────┼──────────────────────────────────────┘ │
│                                    │                                         │
│                                    │ WebSocket (porta 8765)                  │
│                                    │                                         │
│  ┌─────────────────────────────────┼──────────────────────────────────────┐ │
│  │                    BACKEND PYTHON                                       │ │
│  │                                 │                                       │ │
│  │  ┌──────────────────────────────┴──────────────────────────────────┐   │ │
│  │  │                     WebSocket Handler                            │   │ │
│  │  │  • Riceve messaggi      • Gestisce sessioni                     │   │ │
│  │  │  • Routing richieste    • Error handling                        │   │ │
│  │  └──────────────────────────────┬──────────────────────────────────┘   │ │
│  │                                 │                                       │ │
│  │  ┌──────────────────────────────┴──────────────────────────────────┐   │ │
│  │  │                       ORCHESTRATOR                               │   │ │
│  │  │  • Smista lavoro agli agenti                                     │   │ │
│  │  │  • Gestisce dipendenze                                           │   │ │
│  │  │  • Aggrega risposte                                              │   │ │
│  │  │  • Timeout management                                            │   │ │
│  │  └────┬─────────┬─────────┬─────────┬─────────┬────────────────────┘   │ │
│  │       │         │         │         │         │                         │ │
│  │       ▼         ▼         ▼         ▼         ▼                         │ │
│  │  ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐               │ │
│  │  │ Context ││   RAG   ││Security ││Compliance││ Coding  │               │ │
│  │  │  Agent  ││  Agent  ││  Agent  ││  Agent  ││  Agent  │               │ │
│  │  │         ││         ││         ││         ││         │               │ │
│  │  │ Memoria ││ Ricerca ││ Semgrep ││ Ruleset ││  Diff   │               │ │
│  │  │ Contesto││ Vector  ││ Pattern ││ GDPR    ││ Patches │               │ │
│  │  └────┬────┘└────┬────┘└────┬────┘└────┬────┘└────┬────┘               │ │
│  │       │         │         │         │         │                         │ │
│  │       └─────────┴────┬────┴─────────┴─────────┘                         │ │
│  │                      │                                                   │ │
│  │  ┌───────────────────┴───────────────────────────────────────────────┐ │ │
│  │  │                    CORE INFRASTRUCTURE                             │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │ │ │
│  │  │  │Exceptions│ │  Retry   │ │ Timeout  │ │Connection│             │ │ │
│  │  │  │ Handling │ │  Logic   │ │  Budget  │ │   Pool   │             │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                          │ │ │
│  │  │  │  State   │ │Dependency│ │Observabil│                          │ │ │
│  │  │  │Management│ │  Graph   │ │   ity    │                          │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘                          │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/API
                                    ▼
            ┌───────────────────────────────────────────────┐
            │              SERVIZI ESTERNI                   │
            │  ┌─────────────┐  ┌─────────────┐             │
            │  │   OpenAI    │  │  Anthropic  │             │
            │  │   (GPT-4)   │  │  (Claude)   │             │
            │  └─────────────┘  └─────────────┘             │
            │  ┌─────────────┐  ┌─────────────┐             │
            │  │  ChromaDB   │  │   Qdrant    │             │
            │  │ (Vector DB) │  │ (Vector DB) │             │
            │  └─────────────┘  └─────────────┘             │
            └───────────────────────────────────────────────┘
```

---

**Documento generato**: 10 Gennaio 2026  
**Ultima revisione**: 10 Gennaio 2026  
**Autore**: Sistema OMNI - Documentazione Automatica
