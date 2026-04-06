# ROADMAP — routing-generator

**Brainstorm session 2026-04-06** | Next review: 2026-04-20

---

## Feature Matrix

| # | Feature | Priority | Impact | Effort | Owner | Status |
|----|---------|----------|--------|--------|-------|--------|
| 1 | Live Router Metrics Dashboard | 🔴 P1 | 🟢 High | ⭐⭐⭐⭐ | orchestratore | ❌ Backlog |
| 2 | ML Feedback Loop (auto-calibrate weights) | 🔴 P1 | 🟢 High | ⭐⭐⭐⭐⭐ | developer | ❌ Backlog |
| 3 | Multi-Language Agent Templates | 🟠 P2 | 🟠 Mid | ⭐⭐⭐ | developer | ❌ Backlog |
| 4 | Scenario Evolution Generator | 🟠 P2 | 🟢 High | ⭐⭐⭐ | orchestratore | ❌ Backlog |
| 5 | Cross-Agent Context Bridge (graph routing) | 🔴 P1 | 🟢 High | ⭐⭐⭐⭐⭐ | orchestratore | ❌ Backlog |
| 6 | Pattern Marketplace / GitHub Discovery | 🟡 P3 | 🟠 Mid | ⭐⭐ | developer | ❌ Backlog |
| 7 | Historical Audit Trail + Rollback | 🟡 P2 | 🟠 Mid | ⭐⭐⭐ | developer | ❌ Backlog |
| 8 | Cost Estimator (token budget per scenario) | 🟡 P3 | 🟠 Mid | ⭐⭐ | developer | ❌ Backlog |
| 9 | IDE Integrations (VS Code extension) | 🔵 P4 | 🔴 Low | ⭐⭐⭐⭐ | external | ❌ Backlog |
| 10 | Stochastic Testing Mode | 🔵 P4 | 🔴 Low | ⭐⭐⭐ | tester | ❌ Backlog |

### Quick Wins (Low effort, no priority slot)
- [ ] Colored CLI output (`--color`, default: auto)
- [ ] Tab completion bash/zsh (`rgen --enable-completion`)
- [ ] JSON Schema for routing-map autocomplete
- [ ] Dry-run with file preview

---

## Decision Authority

Vedi `.github/decision-priority.md`:
- **Developer**: Feature, CLI flags, adapter/writer logic
- **Tester**: Test coverage, validation, stochastic mode
- **Orchestratore**: Architecture (graph routing, ML loop), priorità ambigue
- **Documentazione**: README update, pattern docs

---

## Feature Dependency Graph

```
[ 1 Live Metrics ]
        ↓
[ 2 ML Feedback Loop ] ←─── richiede interventi storici
        ↓
[ 4 Scenario Evolution Generator ]
        ↓
[ 3 Multi-Language Templates ] (indipendente)

[ 5 Cross-Agent Bridge ] ←─── richiede [ 1 ] per debugging
        ↓
[ 7 Historical Audit Trail ]

[ 6 Pattern Marketplace ] ←─── richiede revisione pattern structure
[ 8 Cost Estimator ] (potrebbe integrarsi con [ 1 ])
[ 9 IDE Extensions ] (P4, posticipiamo)
[ 10 Stochastic Testing ] (P4, dopo [ 2 ] stabile)
```

**Minimal viable sequence**:
1. **Phase 1 (Sprint 1-2)**: [ 1 Live Metrics ]
2. **Phase 2 (Sprint 3-4)**: [ 2 ML Feedback Loop ]
3. **Phase 3 (Sprint 5)**: [ 4 Scenario Evolution + 3 Multi-Language ]
4. **Phase 4 (Sprint 6+)**: [ 5 Graph Routing ], [ 7 Audit Trail ]

---

## Per-Feature Details

### 🔴 P1.1 — Live Router Metrics Dashboard
**Owner**: orchestratore | **Effort**: ⭐⭐⭐⭐ | **Impact**: High
**Plan**: [`.github/plans/live-metrics-dashboard.plan`](./plans/live-metrics-dashboard.plan)

**Goal**: Real-time TUI (Text UI) monitoring di routing health
- Confidence trend (media ultimi N query)
- Scenario usage heatmap
- Overlap indicators (agenti che "competono")
- Dead zones (query senza scenario match)
- Exit: `python .github/router.py --dashboard` interactive mode

**Acceptance**:
- [ ] TUI framework integrato (rich library)
- [ ] Metrics raccolti da router.py --stats
- [ ] Refresh < 500ms
- [ ] Graceful fallback su terminal non-TTY
- [ ] Test coverage > 85%

---

### 🔴 P1.2 — ML Feedback Loop
**Owner**: developer | **Effort**: ⭐⭐⭐⭐⭐ | **Impact**: High

**Goal**: Auto-calibrate keyword weights da success history
- Registrare quale agente ha risolto il task
- Boostrare weight per scenario vincente
- Deprecare scenario che genera false positive
- Exit: `router.py` usa weights dinamici da `interventions.json`

**Acceptance**:
- [ ] Log strutturato di success/fail per agente
- [ ] Algoritmo di decay (recent > old)
- [ ] Dry-run mode per vedere delta weights
- [ ] Backup automatico di weights old

---

### 🟠 P2.1 — Multi-Language Agent Templates
**Owner**: developer | **Effort**: ⭐⭐⭐ | **Impact**: Mid

**Goal**: Agent risposte customizzate per lingua del progetto
- Detect documentazione lingua da metadata
- Template agente in IT/EN/ES/FR
- Vincoli styleguide culturali
- Exit: agents generati con `{{LANGUAGE}}` context

**Acceptance**:
- [ ] Support 4 lingue minimo
- [ ] Fallback a EN se manca lingua
- [ ] i18n structure nel knowledge_base

---

### 🟠 P2.2 — Scenario Evolution Generator
**Owner**: orchestratore | **Effort**: ⭐⭐⭐ | **Impact**: High

**Goal**: Auto-detect pattern simili → suggerisci nuovo scenario
- Analizza `interventions.db` (history)
- Cluster query simili non categorizzate
- Output: "Scenario candidato: `optimization_performance`, 7 query simili"
- Exit: CLI tool `rgen --suggest-scenarios`

**Acceptance**:
- [ ] Clustering algorithm (cosine similarity)
- [ ] Threshold di confidence configurabile
- [ ] JSON output candidati
- [ ] Test su dataset storico reale

---

### 🔴 P1.3 — Cross-Agent Context Bridge
**Owner**: orchestratore | **Effort**: ⭐⭐⭐⭐⭐ | **Impact**: High

**Goal**: Routing a grafo, non 1:1 map
- Agent A → "serve esperto B"  → chiama B in cascade
- Primary + secondary agents per scenario
- Context forwarding tra agenti
- Exit: `routing-map.json` con `"dependencies": ["esperto_x"]`

**Acceptance**:
- [ ] Routing graph validazione (cicli?)
- [ ] Primary fallback su failure
- [ ] Context size limits
- [ ] Test cascade scenario

---

### 🟡 P2.3 — Historical Audit Trail + Rollback
**Owner**: developer | **Effort**: ⭐⭐⭐ | **Impact**: Mid

**Goal**: Timeline di tutte generazioni, rollback selettivo
- Extend `.rgen-backups/` con metadata
- Query diff tra versioni routing-map
- Rollback a generazione X preservando modifiche manuali Y
- Exit: `rgen --history --show-diffs` e `rgen --rollback --to <gen_id>`

**Acceptance**:
- [ ] Timestamp in backup metadata
- [ ] Diff annotation in JSON
- [ ] Smart merge (manuale > auto)
- [ ] Test su sequence di 5+ generazioni

---

### 🟡 P3.1 — Pattern Marketplace
**Owner**: developer | **Effort**: ⭐⭐ | **Impact**: Mid

**Goal**: Condividere custom pattern tra team
- Hub simple GitHub: `patterns/` registry o org
- CLI: `rgen --download 'owner/pattern:version'`
- Validation on download (checksum, schema)
- Exit: CI/CD che valida pattern prima di merge

**Acceptance**:
- [ ] Pattern search command
- [ ] Signed releases (opcional)
- [ ] Rating + comment per pattern
- [ ] Test download + install flow

---

### 🟡 P3.2 — Cost Estimator
**Owner**: developer | **Effort**: ⭐⭐ | **Impact**: Mid

**Goal**: Stimare token/scenario + alert su inefficienza
- Model token estimator (GPT-4o pricing, Claude pricing, ...)
- Cost per scenario = avg_context_size × scenario_popularity
- Alert: "Questi 3 scenari costano X, considera consolidamento"
- Exit: `rgen --cost-report` JSON output

**Acceptance**:
- [ ] Model pricing DB (aggiornabile)
- [ ] Estimation accuracy +/- 10%
- [ ] Consolidation suggestion algorithm

---

### 🔵 P4.1 — IDE Extensions (VS Code)
**Owner**: external | **Effort**: ⭐⭐⭐⭐ | **Impact**: Low

**Goal**: Extension che mostra agent competente durante editing
- Hover su task → preview agent + confidence
- Syntax highlight routing-map.json
- Performance: no overhead

**Acceptance**:
- [ ] Extension published to marketplace
- [ ] < 100ms query time
- [ ] Test on 50+ project size

---

### 🔵 P4.2 — Stochastic Testing Mode
**Owner**: tester | **Effort**: ⭐⭐⭐ | **Impact**: Low

**Goal**: Fuzz router su parameter variations
- Variano keyword weights, thresholds, query lengths
- Test robustness routing su edge case
- Exit: `pytest tests/test_stochastic_routing.py`

**Acceptance**:
- [ ] 1000+ fuzz iterations
- [ ] Seed reproducible
- [ ] Coverage report

---

## Quick Wins (No priority, do anytime)

### CLI Color Output
```bash
rgen --direct ... --color auto|always|never  # default: auto
# Exit: colored output ✅❌⚠️ emojis
```

### Tab Completion
```bash
rgen --enable-completion bash  # generar .completions/rgen.bash
source <(rgen --enable-completion bash)
```

### JSON Schema
```
.github/schema/routing-map.schema.json  # per IDE autocomplete
.vscode/settings.json: associate
```

### Dry-run Preview
```bash
rgen --dry-run ... --show-files  # mostra file che verrebbero scritti
# Ex: "+ .github/router.py", "~ .github/routing-map.json"
```

---

## Timeline Suggerita

```
Week 1-2:   [ 1 Live Metrics ]
Week 3-4:   [ 2 ML Feedback Loop ]
Week 5-6:   [ 4 Scenario Evolution + 3 Multi-Language ]
Week 7-8:   [ 5 Cross-Agent Bridge ] → richiede revisione core
Week 9-10:  [ 7 Audit Trail + 8 Cost Estimator ]
Week 11+:   [ 6 Pattern Marketplace + Quick Wins ]
P4:         [ 9 IDE, 10 Stochastic ] sotto altri sprint
```

**Check-in points**: ogni 2 settimane con tester + documentazione

---

## Link Correlati

- `.github/decision-priority.md` — authority per feature decision
- `.github/token-budget-allocation.md` — budget per sprint
- `.github/AGENT_REGISTRY.md` — ruoli correnti
- `tests/` — ensure coverage > 90% per ogni feature
