# Context Pack (design)

Obiettivo: fornire all'assistente un set minimo di file Markdown sintetici, facili da aggiornare in modo incrementale e referenziabili (citazioni verso file/linee originali quando possibile).

## File generati

- `.github/copilot-instructions.md` — breve, punta al pack in `.omni/context/`
- `.omni/context/`
  - `project-overview.md` — stack, runtime, entrypoint, comandi utili
  - `component-map.md` — mappa moduli/cartelle → responsabilità → dipendenze
  - `interfaces-and-apis.md` — superfici pubbliche (API, classi, funzioni esposte)
  - `data-model.md` — classi/modelli/exports noti
  - `hotspots.md` — file prioritari (es. top LOC) per concentrare la review
  - `file-summaries.md` — riassunti dettagliati file x file (per approfondimento)
- `.omni/insights/` — `security.md`, `compliance.md`

## Regole di aggiornamento (on-demand synthesis)

- **Workspace scan**: genera/aggiorna tutti i file del pack.
- **File change**:
  - aggiorna solo i chunk nel vector store
  - rigenera le sezioni pertinenti:
    - `file-summaries.md` (solo il file toccato)
    - `component-map.md` (cartella del file)
    - `interfaces-and-apis.md` (se il file contiene classi/funzioni)
    - `data-model.md` (se il file contiene classi/costanti)
    - `hotspots.md` (se la LOC del file cambia in modo significativo)
  - `copilot-instructions.md` resta breve, ma si rigenera per tenere i link aggiornati

## Criteri di contenuto

- **Breve per Copilot**: `copilot-instructions.md` deve essere corto e puntare ai markdown in `.omni/context/`.
- **Citazioni**: quando disponibile, includere percorso (e linea se nota) per ogni insight.
- **Rumore minimo**: preferire elenchi brevi e ordinati; troncare descrizioni lunghe; limitare a top-N elementi per sezione.

## Evoluzioni possibili

- Ordine dei hotspot basato su churn/storia git (non solo LOC).
- Task Brief on-demand: dato un task, generare un riassunto contestuale con top-K chunk e citazioni.
- Segmentazione intelligente: chunking per funzione/classe anziché blocchi fissi.
