# AgentPilot Orchestrator -- AI Dispatcher

<!-- start AgentPilot Rules -->
⚠️ **WARNING**: Content between these markers is auto-generated and may be overwritten by the sync process. Do not add local customizations here.

## DISPATCHER

### Session bootstrap (obbligatorio)
All'inizio di ogni sessione operativa:
1. Esegui `python .github/router.py --stats`
2. Pubblica l'header di stato con i dati del router

Opzione rapida consigliata (singola esecuzione):
```
python .github/session_header.py --query "<query>"
```
Questo comando esegue internamente stats + direct + update_report + mcp_status e stampa header pronto.

### Regola root e target (.github)
- Il repository in root e' la sorgente principale per sviluppo, fix e documentazione.
- Il target operativo e' la cartella `.github` (servizio router/MCP distribuito tramite update).
- Flusso obbligatorio quando si migliora il progetto:
   1. Modifica e valida prima il repository in root.
   2. Allinea/merge il repository sorgente.
   3. Esegui update del target `.github` con il metodo di update previsto.
- Evita fix diretti solo sul target `.github` senza riportarli prima nella sorgente root.

### Per-request protocol (obbligatorio)
Prima di ogni risposta operativa:
1. Esegui il comando unico (default obbligatorio):
   ```
   python .github/session_header.py --query "<query>"
   ```
   Questo comando esegue internamente `router --stats`, `router --direct`, `update_report`, `mcp_status` e stampa header finale pronto.

2. Determina il **budget token** dal campo `priority` del routing risultante:

   | Priority | Budget stimato | Uso tipico |
   |----------|---------------|------------|
   | `high`   | ~20 000 tok   | Fix chirurgici, codice critico |
   | `medium` | ~35 000 tok   | Feature nuove, refactor |
   | `low`    | ~15 000 tok   | Docs, style, configurazione |
   | nessun match | ~10 000 tok | Chiarimento, domanda veloce |

3. Usa il protocollo multi-comando **solo come fallback di debug** (non default):
   ```
   python .github/router.py --stats
   python .github/router.py --direct "<query>"
   python .github/update_report.py --output .github/UPDATE_STATUS.md
   python .github/mcp_status.py
   ```
   Usa il campo JSON `update_value` stampato dallo script per popolare l'header (`ok` oppure link markdown a `.github/UPDATE_STATUS.md`).
   Opzionale (solo quando richiesto):
   ```
   python .github/update_report.py --output .github/UPDATE_STATUS.md --auto
   ```

4. Pubblica header **obbligatorio** in questa forma:
   ```
   🤖 Suggest:<suggested_model> | Agente: <agent> | Scenario: <scenario> | Budget: ~<N>k tok | Routing: <stats> | Update: <ok-or-NeedUpdateLink> | MCP: <Active-or-Standby-or-Inactive>
   ```
   Dove `suggested_model` è il modello **preferito** da routing-map (`preferred_model`) in base all'uso (`usage_profile`) e alla priorità; non è un vincolo hard e non rappresenta il modello reale in uso nel picker Copilot.
   Linee aggiuntive consigliate subito sotto header:
   ```
   Riepilogo: confidence=<0..1|n/a> | clarify=<yes|no>
   KPI details: [.github/kpi/KPI_METHODS.md](.github/kpi/KPI_METHODS.md)
   ```
   Se `Update` e' `Need Update`, aggiungi subito sotto una riga separata (anche se il link in header non renderizza):
   ```
   Update details: [.github/UPDATE_STATUS.md](.github/UPDATE_STATUS.md)
   ```
   Regola MCP:
   - se attivo: `MCP: Active`
   - se configurato ma non ancora avviato da VS Code: `MCP: Standby`
   - se non attivo: `MCP: Inactive (see .github/MCP_ACTIVATION.md)`
   Esempio reale:
   ```
   🤖 Suggest:gpt-4o-mini | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: ok | MCP: Active
   ```
   Oppure, se non aggiornato:
   ```
   🤖 Suggest:claude-sonnet-4-5 | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: [Need Update](.github/UPDATE_STATUS.md) | MCP: Active
   ```
   Oppure, se MCP non attivo:
   ```
   🤖 Suggest:claude-sonnet-4-6 | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: ok | MCP: Inactive (see .github/MCP_ACTIVATION.md)
   ```
   Oppure, se MCP e' configurato ma lazy-start:
   ```
   🤖 Suggest:claude-sonnet-4-6 | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: ok | MCP: Standby
   ```

5. Limita la risposta al budget dichiarato. Se prevedi di superarlo, avvisa l'utente e chiedi conferma.

6. Applica disciplina token e ragionamento minimo:
   - Ragiona in profondita solo se necessario per sbloccare decisioni tecniche non banali.
   - Per task semplici o ripetitivi, usa risposta/azione diretta con massimo contesto locale.
   - Durante iterazioni multi-step, evita riesplorazioni ampie: leggi solo il delta necessario tra un edit e il check successivo.
   - Dopo il primo edit sostanziale, valida subito con il test/check piu economico del perimetro toccato prima di fare altro.
   - Se il check conferma l'ipotesi, prosegui con il minimo edit adiacente; se la falsifica, fai un solo hop locale verso il punto di controllo corretto.
   - Evita spiegazioni verbose non richieste: privilegia output compatti, operativi e verificabili.

### Model guidance policy (non vincolante)
- Source of truth: `.github/routing-map.json` (`usage_profile`, `preferred_model`).
- Modalità: `preferred-not-forced`.
- Override consentito quando confidence è bassa o la complessità reale richiede qualità superiore.
- Ogni override deve essere esplicitato in output come scelta operativa, non come verità sul modello runtime di Copilot.

### Agents
| Agent | Domain |
|-------|--------|
| `backend` | AgentPilot Orchestrator -- backend domain |
| `devops` | AgentPilot Orchestrator -- devops domain |
| `documentazione` | AgentPilot Orchestrator -- documentazione domain |
| `orchestratore` | AgentPilot Orchestrator -- orchestratore domain |

### Key scenarios
- `python_code`
- `api_endpoints`
- `database`
- `auth`
- `caching`
- `testing`
- `docker_infra`
- `performance`

### Router commands
```
python .github/router.py --direct "<query>"
python .github/router.py --follow-up "<query>"
python .github/router.py --stats
python .github/router.py --audit
python .github/mcp_status.py
python .github/update_report.py --output .github/UPDATE_STATUS.md
python .github/update_report.py --output .github/UPDATE_STATUS.md --auto
```

### Policy esplorazione repo
1. Parti sempre dai file instradati dal router
2. Mantieni scope ridotto se confidence > soglia
3. Allarga all'intero repo solo se `repo_exploration.allowed: true`
<!-- end AgentPilot Rules -->

## PROJECT

**AgentPilot Orchestrator** | Stack: python, fastapi, flask, postgresql, postgres, redis, docker, pytest, sqlalchemy, alembic, pydantic, nginx

## Tracciatura discussioni

Ogni sessione operativa deve lasciare traccia in `.discussioni/` (cartella locale, esclusa da git).

### Regole obbligatorie
1. Crea un file per ogni sessione con nome formato `YYYY-MM-DD-<tema>.md`
2. Ogni file deve contenere:
   - **Data** e **tema** della sessione
   - **Decisioni** prese
   - **File modificati** con motivazione
   - **Task aperti** o follow-up
3. Se una risposta non è verificabile direttamente nel codice, marcala come *ipotesi*
4. Aggiorna il file durante la sessione, non solo alla fine

### Formato minimo
```markdown
# Sessione YYYY-MM-DD — <tema>

## Decisioni
- ...

## File modificati
- `path/file.py` — motivo

## Task aperti
- [ ] ...
```

## Postflight
- Verifica che l'agente scelto sia coerente con la richiesta
- Esegui i test rilevanti prima di chiudere il task
- Se aggiungi/rimuovi test, aggiorna il conteggio test nel badge del `README.md`
- Mantieni documentazione e artefatti di routing allineati
- Aggiorna (o crea) il file di sessione in `.discussioni/`