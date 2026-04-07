<div>
<div align="Left">

```
 ____   ___  _   _ _____ ___ _   _  ____
|  _ \ / _ \| | | |_   _|_ _| \ | |/ ___|
| |_) | | | | | | | | |  | ||  \| | |  _
|  _ <| |_| | |_| | | |  | || |\  | |_| |
|_| \_\\___/ \___/  |_| |___|_| \_|\____|
        ____ _____  _   _ _____ ____      _  _____ ___  ____
       / ___| ____|| \ | | ____|  _ \    / \|_   _/ _ \|  _ \
      | |  _|  _|  |  \| |  _| | |_) |  / _ \ | || | | | |_) |
      | |_| | |___ | |\  | |___|  _ <  / ___ \| || |_| |  _ <
       \____|_____||_| \_|_____|_| \_\/_/   \_\_| \___/|_| \_\
```
</div>
<div align="Center">
**Genera automaticamente un sistema di routing AI semantico per qualsiasi progetto.**

[![Python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-187%2F187-brightgreen?logo=pytest&logoColor=white)](tests/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies](https://img.shields.io/badge/core-stdlib%20only%20%2B%20rich-orange)](pyproject.toml)
[![Works with](https://img.shields.io/badge/works%20with-Copilot%20%7C%20Claude%20%7C%20Cursor-blueviolet)](README.md)

</div>
</div>

---

## Cos'e'

`rgen` e' uno **strumento CLI** che genera in secondi l'infrastruttura completa di routing AI per il tuo progetto: scenari, agenti specializzati, system prompt e motore di routing — tutto calibrato sulla tua architettura.

```
Il tuo progetto              Routing system generato
───────────────              ───────────────────────

  "Ho un'app FastAPI        .github/
   con PostgreSQL           ├── router.py                <- motore semantico
   e Redis cache..."        ├── routing-map.json         <- 20+ scenari custom
                            ├── copilot-instructions.md  <- system prompt
        rgen                ├── AGENT_REGISTRY.md
        ────►               ├── subagent-brief.md
                            ├── standard/
                            │   ├── general-style.md
                            │   ├── python-style-guide.md
                            │   └── template.py
                            └── esperti/
                                ├── esperto_backend.md
                                ├── esperto_database.md
                                └── esperto_devops.md
```

### Cosa ottieni

- **Riduzione token** — ogni richiesta viene instradata solo all'agente competente
- **Zero allucinazioni di contesto** — ogni agente conosce solo il suo dominio
- **Auto self-check** — 8 controlli di integrità post-generazione
- **Backup automatico** — ogni sovrascrittura viene salvata con timestamp
- **Pattern riutilizzabili** — costruisci una knowledge base di pattern per team
- **Standard pack linguistico** — style guide e template base generati in `.github/standard/`

---

## Flusso di lavoro

```
                    ┌─────────────────────────────────────────┐
                    │              rgen --direct              │
                    │    --pattern psm_stack --name my-app    │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │           PatternLoader                 │
                    │   knowledge_base/<pattern>/             │
                    │   metadata.json + routing-map.json      │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │              Adapter                    │
                    │   Sostituisce {{VAR}} nei template      │
                    │   Rinomina agenti al tuo stack          │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │     Writer  +  BackupEngine             │
                    │   Backup automatico se .github/ esiste  │
                    │   Copia core files + genera output      │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │            SelfChecker                  │
                    │   8 controlli: files, routing-map,      │
                    │   agenti, template_vars, stats...       │
                    └─────────────────────────────────────────┘
```

---

## Installazione

```bash
git clone https://github.com/<your-username>/routing-generator
cd routing-generator

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -e .
pip install -r requirements-dev.txt   # solo per i test
```

---

## Quick Start

### 1. Vedi i pattern disponibili

```bash
rgen --list-patterns
```

```
Pattern disponibili (3):
  psm_stack   — PHP 8.3 + Docker + MariaDB + Traefik + Proxmox
  python_api  — FastAPI/Flask + PostgreSQL + Redis + Docker
  node_ts     — Node.js TypeScript + Express + React/Vue + Docker
```

### 2. Genera il routing per il tuo progetto

```bash
# Non-interattivo (CI/CD friendly)
rgen --direct --pattern psm_stack --name my-app --target ./my-app

# Anteprima senza scrivere nulla su disco
rgen --dry-run --pattern psm_stack --name my-app --target ./my-app

# Interattivo guidato (consigliato per la prima volta)
rgen
```

### 3. Output della generazione

```
[rgen] Backup: 0 file (destinazione vuota)
[rgen] Scritti: 18 file in ./my-app/.github/

Self-Check Report
=================
[PASS] required_files    - router.py, routing-map.json, ... (8/8)
[PASS] routing_map       - 21 scenari, 162 keywords, JSON valido
[PASS] expert_files      - 3 agenti dichiarati, 3 file trovati
[PASS] agent_registry    - AGENT_REGISTRY.md coerente con routing-map
[PASS] copilot_instr     - sezioni DISPATCHER e Router presenti
[PASS] template_vars     - nessun {{VAR}} rimasto non sostituito
[PASS] core_files        - router.py, interventions.py copiati
[PASS] router_stats      - exit 0, overall: ok

Overall: OK (8/8 checks passed)
```

### 4. Attiva il routing nel tuo AI tool

| Tool | Come attivare |
|---|---|
| **GitHub Copilot** | `.github/copilot-instructions.md` caricato automaticamente da VS Code |
| **Claude Code** | Incolla `copilot-instructions.md` come system prompt o CLAUDE.md |
| **Cursor** | Rinomina in `.cursorrules` o usa il system prompt |
| **Aider** | `aider --system-prompt .github/copilot-instructions.md` |
| **Qualsiasi LLM** | Copia manualmente il contenuto di `copilot-instructions.md` |

---

### 5. Scenario Evolution (P2.x in progress)

Puoi ottenere candidati scenario dai log storici in `.github/interventions.db`:

```bash
# Analisi standard: usa prima i fallback / unmatched
rgen --suggest-scenarios --target ./my-app

# Salva anche il payload JSON su file
rgen --suggest-scenarios --target ./my-app --suggest-output ./artifacts/scenario-suggestions.json

# Filtra cluster deboli o troppo piccoli
rgen --suggest-scenarios --target ./my-app --min-cluster-size 4 --min-confidence 0.65

# Limita l'analisi agli ultimi 50 interventi
rgen --suggest-scenarios --target ./my-app --history-limit 50

# Analizza tutta la history, non solo gli unmatched
rgen --suggest-scenarios --target ./my-app --include-matched
```

Output: JSON con cluster di query simili, keywords estratte, scenario suggerito e confidence.

Opzioni principali:

- `--min-cluster-size` per ignorare gruppi troppo piccoli
- `--similarity-threshold` per rendere il clustering piu' o meno aggressivo
- `--min-confidence` per escludere suggerimenti poco affidabili
- `--history-limit` per controllare quanti interventi recenti vengono analizzati
- `--suggest-output` per esportare il JSON su file oltre a stamparlo su stdout
- `--include-matched` per includere anche interventi gia' categorizzati

Esempio (estratto):

```json
[
  {
    "cluster_id": 0,
    "suggested_scenario": "database_query_performance",
    "confidence": 0.81,
    "size": 7,
    "keywords": ["database", "query", "performance"]
  }
]
```

---

## Standard di programmazione generati

Ogni progetto generato include una cartella `.github/standard/` con:

- `general-style.md` per le regole trasversali
- style guide per i linguaggi rilevati dallo stack
- template base come `template.py`, `template.ts`, `template.php`, `template.sql`, `template.sh`, `template.ps1`

La selezione è guidata dal tech stack dichiarato:

- `python`, `fastapi`, `django` -> standard Python
- `javascript`, `node`, `react` -> standard JavaScript
- `typescript`, `nestjs`, `angular` -> standard TypeScript
- `php`, `laravel`, `symfony` -> standard PHP
- `postgres`, `mysql`, `mariadb`, `sqlite` -> standard SQL
- `docker`, `linux`, `bash` -> standard Bash
- `powershell`, `windows` -> standard PowerShell

Questo evita che lo stile resti implicito nei singoli agenti e fornisce una base concreta per nuovi file e refactor.

---

## Come funziona il router

Il **router semantico** assegna ogni richiesta all'agente piu' competente tramite keyword scoring:

```bash
# Nella directory del tuo progetto
python .github/router.py --stats
python .github/router.py --direct "ottimizza query postgres per report mensile"
```

```json
{
  "agent": "esperto_database",
  "scenario": "query_optimization",
  "confidence": 0.87,
  "files": [".github/esperti/esperto_database.md"],
  "context": "Query optimization - EXPLAIN, indexes, transactions"
}
```

L'AI riceve **solo** il file `esperto_database.md` — non tutto il contesto del progetto.

### Bootstrap sessione AI (obbligatorio)

Per evitare risposte non allineate allo stato del router, all'inizio di ogni sessione operativa esegui:

```bash
python .github/router.py --stats
```

Poi pubblica sempre un header iniziale con:

```text
🤖 GPT-5.3-Codex | Agente: <agent> | Priorita': <priority> | Routing: <stats + stato>
```

Esempio reale di stato router:

```text
Routing: 15scn/184kw | overlap:2.7% | router:574L | map:7.4KB | [OK] OK
```

Per ogni nuova richiesta, instrada prima il task:

```bash
python .github/router.py --direct "<query>"
# oppure
python .github/router.py --follow-up "<query>"
```

### Policy di esplorazione repo

Il routing via MCP e router CLI non e' una sandbox blindata: e' un filtro operativo iniziale.

Regola consigliata:

1. Parti sempre dai file instradati dal router
2. Mantieni scope ridotto se la confidence e' sopra soglia
3. Allarga all'intero repo solo come fallback controllato

Il router espone ora una policy `repo_exploration` con confidence gate esplicito:

- `allowed: false` quando il match e' sufficientemente affidabile
- `allowed: true` quando non c'e' match, il routing e' ambiguo, oppure la confidence e' sotto soglia

Trigger ammessi per passare alla ricerca repo-wide:

- nessuno scenario matchato
- routing ambiguo
- confidence sotto soglia
- file instradati insufficienti o incoerenti con il repo reale

---

## Advanced Router Features

### 🎯 Live Metrics Dashboard (P1.1 — DONE)

Monitor routing health in real-time:

```bash
python .github/router.py --dashboard
```

**Output**: Interactive TUI with:
- Confidence trend (average recent queries)
- Scenario usage heatmap
- Agent overlap detection
- Dead zones (unmatched queries)
- Controls: `[r]efresh | [e]xport | [q]uit`

---

### 🧠 ML-Calibrated Weights (P1.2 — DONE)

Auto-calibrate routing weights from intervention history:

```bash
# Show calibrated weights with success rates
python .github/router.py --calibrate-weights

# Preview weights without persisting
python .github/router.py --calibrate-weights --dry-run

# Use calibration in routing query
python .github/router.py --direct "query" --use-calibration
```

**Report output**:
```
SUCCESS RATES PER SCENARIO:
  query_optimization        → 87.5%
  config_validation         → 92.1%
  error_handling            → 61.3%

KEYWORD BOOSTS (top 15):
  1. optimize               → +50% (boost: 1.5x)
  2. performance            → +25% (boost: 1.25x)
  3. index                  → +40% (boost: 1.4x)
```

**Features**:
- Decay algorithm: recent interventions weighted higher
- Dry-run mode to preview changes
- Exports to `calibrated_weights.json`
- Configurable minimum sample threshold

---

### 🔗 Graph Routing — Multi-Agent Cascade (P1.3 — DONE)

Route queries through agent dependency graphs for multi-domain tasks:

```bash
python .github/router.py --graph-mode "fix auth bug AND deploy to production"
```

**Features**:
- Primary + secondary agents per scenario
- Automatic cascade execution with context forwarding
- Cycle detection (prevents circular routing)
- Graceful fallback on failures

**Example routing-map.json with dependencies:**
```json
{
  "deployment": {
    "agent": "backend",
    "keywords": ["deploy", "release", "production"],
    "dependencies": ["devops"],
    "files": [".github/esperti/esperto_backend.md"],
    "context": "Full deployment workflow"
  }
}
```

**Output**: Multi-agent result with execution chain:
```json
{
  "mode": "graph",
  "primary": {
    "agent": "backend",
    "scenario": "deployment",
    "confidence": 0.87,
    "files": [".github/esperti/esperto_backend.md"],
    "context": "Full deployment workflow"
  },
  "secondary": [
    {
      "agent": "devops",
      "scenario": "infrastructure",
      "confidence": 0.75,
      "files": [".github/esperti/esperto_devops.md"],
      "context": "Infrastructure management"
    }
  ],
  "execution_plan": ["backend", "devops"],
  "context_forwarding": {
    "prior_agent": "backend",
    "prior_confidence": 0.87,
    "prior_context": "Full deployment workflow"
  },
  "cascade_success": true
}
```

**Workflow**:
1. User query → routes to primary agent (backend)
2. Backend identifies secondary need (devops)
3. System checks dependency graph
4. Devops agent invoked with forwarded context
5. Unified response chain

---

## Backup e ripristino

Prima di ogni scrittura, `rgen` crea automaticamente un backup in `.github/.rgen-backups/<timestamp>/`.

```bash
# Lista backup disponibili
rgen --restore --target ./my-app

# Ripristina un backup specifico
rgen --restore --target ./my-app --timestamp 20260314_143022
```

---

## Validazione post-generazione

```bash
# Verifica un .github/ esistente senza rigenerare nulla
rgen --check --target ./my-app
```

Utile dopo modifiche manuali o aggiornamenti di pattern.

---

## Aggiungere un pattern alla knowledge base

```
knowledge_base/
└── my_pattern/
    ├── metadata.json          <- id, versione, tags, stack
    ├── routing-map.json       <- scenari e keywords
    ├── agents.json            <- definizione agenti
    └── esperti/
        └── esperto_<role>.template.md   <- usa {{VAR}} per variabili
```

Variabili disponibili nei template:

| Variabile | Contenuto |
|---|---|
| `{{PROJECT_NAME}}` | Nome del progetto |
| `{{PROJECT_DESCRIPTION}}` | Descrizione breve |
| `{{TECH_STACK_TABLE}}` | Tabella Markdown dello stack |
| `{{DOMAIN_KEYWORDS}}` | Keywords di dominio |
| `{{CONSTRAINTS_LIST}}` | Vincoli critici |
| `{{AGENT_RESPONSE_PREFIX}}` | Prefisso risposta agente |
| `{{GITHUB_SUBDIR}}` | Cartella di output (default: `.github`) |

Puoi anche rinominare gli agenti via `RENAME_<AGENT>` nei `template_vars`.

---

## Sviluppo e test

```bash
pytest                                         # tutti i test (109/109)
pytest --cov=rgen --cov-report=term-missing   # con coverage
pytest tests/test_cli.py -v                   # integration test
```

### Struttura del progetto

```
routing-generator/
├── rgen/
│   ├── cli.py              <- entry point (6 modalita')
│   ├── questionnaire.py    <- intervista interattiva
│   ├── adapter.py          <- PatternLoader + template substitution
│   ├── writer.py           <- scrittura + backup su disco
│   ├── backup.py           <- BackupEngine con timestamp
│   ├── self_checker.py     <- 8 controlli post-generazione
│   └── models.py           <- ProjectProfile, GenerationResult, CheckReport
├── knowledge_base/
│   ├── psm_stack/          <- PHP + Docker + MariaDB + Traefik
│   ├── python_api/         <- FastAPI/Flask + PostgreSQL + Redis + Docker
│   └── node_ts/            <- Node.js TypeScript + Express + React/Vue
├── core/                   <- file invarianti copiati in ogni progetto
│   ├── router.py           <- motore semantico (574 righe)
│   ├── router_audit.py     <- audit copertura
│   ├── router_planner.py   <- integrazione planner
│   ├── interventions.py    <- memoria SQLite+FTS5
│   └── mcp_server.py       <- MCP server 5 tools
└── tests/                  <- 91 test, tutti con tmp_path
```

---

## MCP Server (opzionale)

Il sistema generato include un **MCP server** che espone il router come tool nativo per AI assistant compatibili:

```bash
# Nel progetto target (non qui)
pip install mcp[cli]>=1.0.0
python .github/mcp_server.py
```

5 tools disponibili: `route_query`, `search_history`, `log_intervention`, `get_stats`, `audit_coverage`.

`route_query` restituisce anche la policy `repo_exploration`, utile per decidere se restare nei file instradati o aprire la ricerca all'intero repository.

---

## Licenza

MIT — libero per uso personale, commerciale e open source.
