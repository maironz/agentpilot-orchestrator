# AgentPilot Orchestrator -- AI Dispatcher

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
   🤖 <model> | Agente: <agent> | Scenario: <scenario> | Budget: ~<N>k tok | Routing: <stats> | Update: <ok-or-NeedUpdateLink> | MCP: <Active-or-Inactive>
   ```
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
   - se non attivo: `MCP: Inactive (see .github/MCP_ACTIVATION.md)`
   Esempio reale:
   ```
   🤖 GPT-5.3-Codex | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: ok | MCP: Active
   ```
   Oppure, se non aggiornato:
   ```
   🤖 GPT-5.3-Codex | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: [Need Update](.github/UPDATE_STATUS.md) | MCP: Active
   ```
   Oppure, se MCP non attivo:
   ```
   🤖 GPT-5.3-Codex | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: ok | MCP: Inactive (see .github/MCP_ACTIVATION.md)
   ```

5. Limita la risposta al budget dichiarato. Se prevedi di superarlo, avvisa l'utente e chiedi conferma.

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
