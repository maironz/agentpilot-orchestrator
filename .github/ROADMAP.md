# ROADMAP — routing-generator

**Brainstorm session 2026-04-06** | Last update: 2026-04-07 | **Phase 1 + P2.1 COMPLETE** ✅ | **P2.2-P2.7 COMPLETE** ✅

---

## Progress Summary

| Phase | Feature | Status | PR |
|-------|---------|--------|-----|
| **Phase 1 (Week 1-2)** | Live Metrics Dashboard | ✅ Done | [#1](https://github.com/maironz/routing-generator/commits) |
| **P1.2 (Week 3-4)** | ML Feedback Loop + Router Integration | ✅ Done | [#5](https://github.com/maironz/routing-generator/commits) |
| **P1.3 (Week 5)** | Cross-Agent Context Bridge (Graph Routing) | ✅ Done | [#7](https://github.com/maironz/routing-generator/commits) |
| **P2.1 (Week 6)** | Multi-Language Agent Templates | ✅ Done | [#8](https://github.com/maironz/routing-generator/commits) |
| **P2.2-P2.7 (Week 7+)** | Scenario Evolution Generator increments | ✅ Done | [#10](https://github.com/maironz/routing-generator/commits) to [#15](https://github.com/maironz/routing-generator/commits) |
| Phase 2+ (next) | Audit Trail, Marketplace, Cost Estimator | 🟡 In progress | - |

**Metrics**:
- **223/223 tests passing** ✅
- **Scenario suggestion workflow complete**: JSON output, text preview, confidence/history filters, matched/unmatched analysis
- **3-panel TUI dashboard** (`python .github/router.py --dashboard`)
- **ML-calibrated routing** (`python .github/router.py --calibrate-weights`)
- **Graph cascade routing** (`python .github/router.py --graph-mode "query"`)
- **Multi-language support** (`rgen --language it|en|es|fr`)
- Ready for next Phase 2 item: audit trail + rollback

---

## Feature Matrix

| # | Feature | Priority | Impact | Effort | Owner | Status |
|----|---------|----------|--------|--------|-------|--------|
| 1 | Live Router Metrics Dashboard | 🔴 P1 | 🟢 High | ⭐⭐⭐⭐ | orchestratore | ✅ Done |
| 2 | ML Feedback Loop (auto-calibrate weights) | 🔴 P1 | 🟢 High | ⭐⭐⭐⭐⭐ | developer | ✅ Done |
| 5 | Cross-Agent Context Bridge (graph routing) | 🔴 P1 | 🟢 High | ⭐⭐⭐⭐⭐ | orchestratore | ✅ Done |
| 3 | Multi-Language Agent Templates | 🟠 P2 | 🟠 Mid | ⭐⭐⭐ | developer | ✅ Done |
| 4 | Scenario Evolution Generator | 🟠 P2 | 🟢 High | ⭐⭐⭐ | orchestratore | ✅ Done |
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

### 🔴 P1.2 — ML Feedback Loop ✅ DONE
**Owner**: developer | **Effort**: ⭐⭐⭐⭐⭐ | **Impact**: High
**Plan**: [`.github/plans/ml-feedback-loop.plan`](./plans/ml-feedback-loop.plan)

**Completed**:
- ✅ `RouterWeightCalibrator` class with decay algorithm
- ✅ `_score_scenarios()` accepts weighted boosts parameter
- ✅ `route_query(use_calibration=True)` optional intelligent routing
- ✅ CLI flag: `--calibrate-weights` show/export weights
- ✅ CLI flag: `--calibrate-weights --dry-run` preview without persist
- ✅ 17 new tests (calibrator + integration)
- ✅ Exit: `python .github/router.py --calibrate-weights` interactive report

**Metrics collected**:
```
SUCCESS RATES PER SCENARIO:
  scenario_name             → success_rate%

KEYWORD BOOSTS (top 15):
  1. keyword_name           → +X% (boost: 1.5x)
```

---

### 🔴 P1.3 — Cross-Agent Context Bridge (Graph Routing) ✅ COMPLETE
**Owner**: orchestratore | **Effort**: ⭐⭐⭐⭐⭐ | **Impact**: High
**Plan**: [`.github/plans/p1-3-graph-routing.plan`](./plans/p1-3-graph-routing.plan)

**Completed**:
- ✅ `GraphRouter` class with DFS cycle detection
- ✅ Dependency graph building from routing-map.json
- ✅ Context forwarding between agent chain
- ✅ CLI flag: `--graph-mode` for cascade routing
- ✅ 31 new tests (unit + integration)
- ✅ Full validation of DAG + graceful error handling
- ✅ Exit: `python .github/router.py --graph-mode "query"` interactive cascade

**Metrics collected**:
```
EXECUTION PLAN:
  primary: backend (confidence: 0.87)
  secondary: [devops, db_admin] (confidence: 0.75, 0.72)

CONTEXT FORWARDING:
  prior_agent: backend
  prior_confidence: 0.87
  cascade_success: true
```

---

---

### 🟠 P2.1 — Multi-Language Agent Templates ✅ COMPLETE
**Owner**: developer | **Effort**: ⭐⭐⭐ | **Impact**: Mid
**Plan**: [`.github/plans/p2-1-multi-language.plan`](./plans/p2-1-multi-language.plan)

**Completed**:
- ✅ `TemplateLocalizer` class with language metadata substitution
- ✅ `LanguageDetector` with metadata → README → content analysis
- ✅ CLI flag: `--language it|en|es|fr` (default: auto-detect)
- ✅ Adapter integration: language parameter through pipeline
- ✅ 21 new tests (CLI + localizer + detector)
- ✅ Exit: `rgen --direct --language it` → Italian agent templates

**Language Support**:
```
Italian (it)      → Tono: Professionale, formale
English (en)      → Tone: Professional, concise
Spanish (es)      → Tono: Profesional, formal
French (fr)       → Ton: Professionnel, formel
```

**Features**:
- `TemplateLocalizer.substitute_language_context()` → {{LANGUAGE}}, {{TONE}}, etc.
- `LanguageDetector.detect()` → auto-detection strategy
- Fallback to English if target language missing
- Full CLI pipeline support (direct + interactive)

---

### 🟠 P2.2 — Scenario Evolution Generator ✅ COMPLETE
**Owner**: orchestratore | **Effort**: ⭐⭐⭐ | **Impact**: High
**Plan**: [`.github/plans/p2-2-scenario-evolution.plan`](./plans/p2-2-scenario-evolution.plan)

**Completed across PR #10-#15**:
- ✅ `rgen --suggest-scenarios` con clustering semantico leggero su `interventions.db`
- ✅ soglia minima cluster configurabile (`--min-cluster-size`)
- ✅ soglia similarita configurabile (`--similarity-threshold`)
- ✅ filtro confidence (`--min-confidence`)
- ✅ analisi limitata agli ultimi N interventi (`--history-limit`)
- ✅ supporto include matched (`--include-matched`)
- ✅ export JSON su file (`--suggest-output`)
- ✅ preview leggibile a terminale (`--suggest-format text`)
- ✅ test unitari e integrazione dedicati

**Current usage**:
```bash
rgen --suggest-scenarios --target ./my-app
rgen --suggest-scenarios --target ./my-app --min-confidence 0.7 --history-limit 50
rgen --suggest-scenarios --target ./my-app --suggest-format text
rgen --suggest-scenarios --target ./my-app --suggest-output artifacts/scenarios.json
```

**Acceptance**:
- [x] Clustering algorithm implemented
- [x] Threshold di confidence configurabile
- [x] JSON output candidati
- [x] Preview text su stdout
- [x] Test coverage aggiornata e suite green

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
**Plan**: [`.github/plans/p2-3-historical-audit-trail.plan`](./plans/p2-3-historical-audit-trail.plan)

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
**Plan**: [`.github/plans/p3-1-pattern-marketplace.plan`](./plans/p3-1-pattern-marketplace.plan)

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
**Plan**: [`.github/plans/p3-2-cost-estimator.plan`](./plans/p3-2-cost-estimator.plan)

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
**Plan**: [`.github/plans/p4-1-ide-extensions.plan`](./plans/p4-1-ide-extensions.plan)

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
**Plan**: [`.github/plans/p4-2-stochastic-testing.plan`](./plans/p4-2-stochastic-testing.plan)

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
**Plan**: [`.github/plans/quick-win-cli-color-output.plan`](./plans/quick-win-cli-color-output.plan)
```bash
rgen --direct ... --color auto|always|never  # default: auto
# Exit: colored output ✅❌⚠️ emojis
```

### Tab Completion
**Plan**: [`.github/plans/quick-win-tab-completion.plan`](./plans/quick-win-tab-completion.plan)
```bash
rgen --enable-completion bash  # generar .completions/rgen.bash
source <(rgen --enable-completion bash)
```

### JSON Schema
**Plan**: [`.github/plans/quick-win-routing-schema.plan`](./plans/quick-win-routing-schema.plan)
```
.github/schema/routing-map.schema.json  # per IDE autocomplete
.vscode/settings.json: associate
```

### Dry-run Preview
**Plan**: [`.github/plans/quick-win-dry-run-preview.plan`](./plans/quick-win-dry-run-preview.plan)
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
