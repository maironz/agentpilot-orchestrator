# AgentPilot Orchestrator -- AI Dispatcher

## DISPATCHER

### Session bootstrap (obbligatorio)
All'inizio di ogni sessione operativa:
1. Esegui `python .github/router.py --stats`
2. Pubblica l'header di stato con i dati del router

### Per-request protocol (obbligatorio)
Prima di ogni risposta operativa:
1. Esegui routing della richiesta:
   ```
   python .github/router.py --direct "<query>"
   ```
2. Determina il **budget token** dal campo `priority` del routing risultante:

   | Priority | Budget stimato | Uso tipico |
   |----------|---------------|------------|
   | `high`   | ~20 000 tok   | Fix chirurgici, codice critico |
   | `medium` | ~35 000 tok   | Feature nuove, refactor |
   | `low`    | ~15 000 tok   | Docs, style, configurazione |
   | nessun match | ~10 000 tok | Chiarimento, domanda veloce |

3. Verifica stato aggiornamento (manual-only policy):
   ```
   python -c "import json, sys; from pathlib import Path; sys.path.insert(0, str(Path('.github').resolve())); import update_manager; s=update_manager.get_update_status(refresh=True); update_available=bool(s.get('update_available')); action=(s.get('manual_update_command') or 'manual_update(confirm=true)') if update_available else 'ok'; print(json.dumps({'update': action}, ensure_ascii=False))"
   ```

4. Verifica stato MCP locale (server attivo/non attivo):
   ```
   python .github/mcp_status.py
   ```

5. Pubblica header **obbligatorio** in questa forma:
   ```
   🤖 <model> | Agente: <agent> | Scenario: <scenario> | Budget: ~<N>k tok | Routing: <stats> | Update: <ok-or-procedura> | MCP: <Active-or-Inactive>
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
   🤖 GPT-5.3-Codex | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: git pull --ff-only | MCP: Inactive
   ```
   Oppure, se MCP non attivo:
   ```
   🤖 GPT-5.3-Codex | Agente: orchestratore | Scenario: _fallback | Budget: ~15k tok | Routing: 13scn/176kw|overlap:2.3%|[WARN] | Update: ok | MCP: Inactive (see .github/MCP_ACTIVATION.md)
   ```

6. Limita la risposta al budget dichiarato. Se prevedi di superarlo, avvisa l'utente e chiedi conferma.

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
python -c "import json, sys; from pathlib import Path; sys.path.insert(0, str(Path('.github').resolve())); import update_manager; print(json.dumps(update_manager.get_update_status(refresh=True), indent=2, ensure_ascii=False))"
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
- Mantieni documentazione e artefatti di routing allineati
- Aggiorna (o crea) il file di sessione in `.discussioni/`
