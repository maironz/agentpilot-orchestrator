# routing-generator -- AI Dispatcher

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

3. Pubblica header **obbligatorio** in questa forma:
   ```
   🤖 <model> | Agente: <agent> | Scenario: <scenario> | Budget: ~<N>k tok | Routing: <stats>
   ```
   Esempio reale:
   ```
   🤖 Claude claude-opus-4-5 | Agente: backend | Scenario: python_code | Budget: ~20k tok | Routing: 13scn/169kw|overlap:1.8%|[OK]
   ```

4. Limita la risposta al budget dichiarato. Se prevedi di superarlo, avvisa l'utente e chiedi conferma.

### Agents
| Agent | Domain |
|-------|--------|
| `backend` | routing-generator -- backend domain |
| `devops` | routing-generator -- devops domain |
| `documentazione` | routing-generator -- documentazione domain |
| `orchestratore` | routing-generator -- orchestratore domain |

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
```

### Policy esplorazione repo
1. Parti sempre dai file instradati dal router
2. Mantieni scope ridotto se confidence > soglia
3. Allarga all'intero repo solo se `repo_exploration.allowed: true`

## PROJECT

**routing-generator** | Stack: python, fastapi, flask, postgresql, postgres, redis, docker, pytest, sqlalchemy, alembic, pydantic, nginx

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
