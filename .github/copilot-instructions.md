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

### Pre-identification (prima risposta della sessione) — MANDATORY

> **⛔ MANDATORY — BEFORE ANY OTHER ACTION**  
> Alla **prima risposta** di ogni nuova sessione (o dopo un reset contesto),  
> l'identificazione è il **primo step da eseguire** — prima di leggere file,  
> prima di analizzare la richiesta, prima di qualsiasi tool call operativo.  
> Saltare questo step invalida architetturalmente l'intera risposta.

**Step**:
1. Esegui `python .github/router.py --stats` per ottenere le metriche di salute
2. Mostra l'header identificativo con metriche inline:
```
🤖 **[NomeModello]** | Agente: **[agente]** | Priorità: [priority] | Routing: [stats-one-liner]
```
**Esempio**: `🤖 **Claude Haiku** | Agente: **orchestratore** | Priorità: medium | Routing: 13scn/176kw | overlap:2.3% | [OK]`

**Exception**: Se continui dal summary precedente (context overflow), dichiara esplicitamente:  
`Continuo dal summary precedente, agente: [X]` — in questo caso il router viene saltato ma la dichirazione è obbligatoria.

### Named Exceptions — Quando saltare il router

Tre casi documentati dove è **lecito saltare il router** (ma deve essere dichiarato):

**Exception 1: Conversation Summary Present**
- Quando VS Code comprime il contesto, il summary è source di truth
- Condizione: Summary contiene file list + agent + continuation plan
- Dichiarazione: `"Continuo dal summary precedente, agente: [X]"`
- Implication: Il router può essere skippato se tutti i dettagli di continuità sono già nel summary

**Exception 2: Post-Task Documentation**
- Documentazione come estensione naturale di un task appena completato (stesso agente)
- Condizione: target è un file noto, scope è limitato al task completato
- Esempio: "aggiorna file avanzamento-lavori dopo code work"
- Implication: Se il task è lo stesso agente + target noto, router è opzionale

**Exception 3: Ambiguity Meta-Router**
- Quando il router restituisce scenari con confidence simile (differenza < 5%)
- Ruolo: L'agente `orchestratore` decide quale scenario è più appropriato
- Dichiarazione: "Orchestrazione: scelgo [scenario] perché [motivo]"
- Implication: Mantiene disciplina pur rispettando ambiguità reali

### Postflight Validation — Solo task non banali

Per task multi-step o non banali, verifica a fine risposta:

1. **Router usato**: ✅ Router eseguito, OPPURE ✅ Exception dichiarata ($summary/$post-task/$meta-router)
2. **Agente coerente**: Agent matching è coerente con il task svolto (no subject drift)
3. **File conformi**: File di contesto nominati nel routing sono quelli effettivamente modificati
4. **Routing coverage**: Se il task ha creato nuovi componenti (classi, namespace, script CLI, tabelle DB, moduli), verificare che le relative keywords siano coperte da almeno uno scenario in `routing-map.json`. In caso di gap, proporre aggiornamento.
5. **Health check**: Se il task ha modificato `routing-map.json`, eseguire `python .github/router.py --stats` e segnalare se lo status è cambiato rispetto all'inizio sessione (es. nuovi scenari, keywords overlap, ecc).

**Nota**: Postflight è **obbligatorio** solo per task non banali (multi-step, create new components, modify routing-map). Per richieste semplici (query, pequeño fix), è opzionale.

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