# AgentPilot v2 Implementation Plan

**Branch**: `feature/agentpilot-v2-guardrails`  
**Status**: 🔄 In Progress  
**Created**: 3 maggio 2026  
**Target completion**: 5 maggio 2026  

---

## 📋 Overview

Transform AgentPilot from a pure routing framework to a framework with integrated operational discipline patterns from PMS Stack.

### Vision
**AgentPilot v0.4.0** → **AgentPilot v0.5.0**
- Keeps: Routing engine, MCP tools, scenario flexibility
- Adds: Pre-identification, exceptions, postflight validation, coverage audit

### Key Principles
- ✅ Backward compatible (additive only)
- ✅ Single source of truth (`core/copilot-instructions.md`)
- ✅ Smart sync preserves local customizations (override zones)
- ✅ Operational discipline enforced but not dogmatic (named exceptions)

---

## ✅ Phase 1: COMPLETED — Override Zones Infrastructure

**Commit**: `484200c`

### Deliverables
- Added override zone markers in:
  - `core/copilot-instructions.md`
  - `.github/copilot-instructions.md`
- Implemented smart sync: `_sync_with_override_zones()` in `active_option_sync.py`
- Fallback safety: Skip sync if markers missing (prevents data loss)
- Documentation: `docs/SYNC_STRATEGY.md`
- Tests: All validations pass (marker presence, merge logic, fallback behavior)

---

## 🔄 Phase 2: IN PROGRESS — Guardrail Patterns

### 2a. Pre-identification Mandatory Pattern
**File to modify**: `core/copilot-instructions.md`  
**Source**: PMS Stack `copilot-instructions1.md` (§ Identificazione)

**What to add**:
```markdown
### Pre-identification (prima risposta della sessione)

> **⛔ MANDATORY — BEFORE ANY OTHER ACTION**  
> Alla **prima risposta** di ogni nuova sessione (o dopo un reset contesto),  
> l'identificazione è il **primo step da eseguire** — prima di leggere file,  
> prima di analizzare la richiesta, prima di qualsiasi tool call operativo.  
> Saltare questo step invalida architetturalmente l'intera risposta.

1. Esegui `python .github/router.py --stats` per ottenere le metriche di salute
2. Mostra l'header identificativo con metriche inline:

```
🤖 **[NomeModello]** | Agente: **[agente]** | Priorità: [priority] | Routing: [stats]
```
```

**Impact**: Every new session or context reset requires pre-identification header with router stats inline.

---

### 2b. Named Exceptions Pattern
**File to modify**: `core/copilot-instructions.md` (DISPATCHER section)  
**Source**: PMS Stack (three named exceptions)

**What to add**:

Three explicit exceptions to router requirement:

1. **Exception: Conversation Summary Present**
   - When context window is exceeded, VS Code auto-generates summary
   - If summary contains: file list + agent + continuation plan → can skip router
   - Must declare: `"Continuo dal summary precedente, agente: [X]"`

2. **Exception: Post-Task Documentation**
   - Documentation request immediately after task completion = natural extension
   - Can skip router if: agente same, target is known file, scope is this task only
   - Example: "aggiorna avanzamento-lavori" after code work

3. **Exception: Ambiguity Meta-Router**
   - If router returns scenarios with similar confidence scores → `orchestratore` decides
   - Must motivate the choice

**Impact**: Reduces unnecessary router calls while maintaining discipline.

---

### 2c. Postflight Validation Pattern
**File to modify**: `core/copilot-instructions.md` (DISPATCHER section)  
**Source**: PMS Stack (§ Postflight check)

**What to add**:
```markdown
### Postflight check (solo task non banali)
Per task multi-step o non banali, verifica a fine risposta:
1. Router usato (o eccezione §summary / §post-task dichiarata)
2. Agente coerente con il task svolto
3. File di contesto conformi all'output del router
4. **Routing coverage**: se il task ha creato nuovi componenti 
   (classi, namespace, script CLI, tabelle DB), verificare che le relative keywords 
   siano coperte da almeno uno scenario in `routing-map.json`. 
   In caso di gap, proporre aggiornamento.
5. **Health check**: se il task ha modificato `routing-map.json` 
   (aggiunta scenari/keywords), eseguire `python .github/router.py --stats` 
   e segnalare se lo status è cambiato rispetto all'inizio sessione.
```

**Impact**: Prevents routing gaps after feature development. Validates that new components have proper routing coverage.

---

### 2d. Coverage Audit Enhancement
**File to modify**: `rgen/router_audit.py`  
**Source**: PMS Stack postflight step 4

**What to implement**:
```python
def validate_new_components_coverage(created_components: list[str], routing_map: dict) -> dict:
    """
    Check if newly created components are covered by routing-map scenarios.
    
    Returns:
        {
            "covered": [...],
            "gaps": [...],
            "recommendations": [...]
        }
    """
    # Logic: compare component names against all scenario keywords
```

**Usage**: Called during postflight; if gaps exist, suggest routing-map update.

**Impact**: Catch uncovered scenarios before they become blind spots.

---

## 🔲 Phase 3: VALIDATION — Tests + Docs

### Tasks
- [ ] All existing tests pass (233/233, no regressions)
- [ ] New test file: `tests/test_agentpilot_guardrails.py`
  - Pre-identification pattern
  - Exception handling (summary, post-task, ambiguity)
  - Postflight validation
  - Coverage audit
- [ ] Update badge in `README.md`: Tests → 237/237, v0.5.0
- [ ] Update `docs/COPILOT_INSTRUCTIONS.md` or add reference to new patterns
- [ ] Verify `docs/SYNC_STRATEGY.md` complete and linked

**Estimated**: 1-1.5 hours

---

## 🚀 Phase 4: MERGE — PR + Release

### Pre-Merge Checklist
- [ ] Branch is fully tested (local + CI green)
- [ ] All commits are meaningful (not work-in-progress)
- [ ] Version updated: `pyproject.toml`, `VERSION`, `README.md`
- [ ] PR title: `[v2] AgentPilot with Smart Sync + PMS Stack Guardrails`

### PR Description Template
```markdown
## Summary
Merge operational discipline patterns from PMS Stack into AgentPilot framework.

## Changes
- Pre-identification mandatory pattern (first session response)
- Named exceptions (summary, post-task, ambiguity meta-router)
- Postflight 5-step validation (routing coverage, health check)
- Coverage audit enhancement in router_audit.py

## Testing
✅ All tests pass (237/237, +4 new)
✅ Manual validation: pre-identification header, postflight validation, coverage audit

## Version
v0.4.0 → v0.5.0

## Fixes
Closes: N/A (feature release)
```

### Merge Process
1. Open PR: `feature/agentpilot-v2-guardrails` → `main`
2. Wait for CI (tests, lint)
3. Merge when green
4. Tag: `git tag -a v0.5.0 -m "AgentPilot v2: Smart Sync + Operational Guardrails"`
5. Push tag: `git push origin v0.5.0`

**Estimated**: 30 min

---

## 📊 Timeline & Effort

| Phase | Content | Status | Hours | Date |
|-------|---------|--------|-------|------|
| 1 | Override zones + sync | ✅ Done | 2 | 3 May |
| 2a | Pre-identification | ⏳ Todo | 1 | 4 May |
| 2b | Named exceptions | ⏳ Todo | 1 | 4 May |
| 2c | Postflight validation | ⏳ Todo | 1 | 4 May |
| 2d | Coverage audit | ⏳ Todo | 0.5 | 4 May |
| 3 | Tests + docs | ⏳ Todo | 1.5 | 5 May |
| 4 | PR merge + release | ⏳ Todo | 0.5 | 5 May |
| **Total** | | | **7.5** | |

---

## 🎯 Success Criteria

### Phase 2 (Guardrails)
- ✅ Pre-identification is enforced in every session's first response
- ✅ Three named exceptions are documented and used appropriately
- ✅ Postflight validation prevents routing gaps in feature development
- ✅ Coverage audit catches new components not in routing-map

### Phase 3 (Tests)
- ✅ Test coverage ≥ 85% for new guardrail code
- ✅ No regressions (all 233 existing tests still pass)
- ✅ New tests are meaningful (not trivial)

### Phase 4 (Merge)
- ✅ PR is approved (CI green, no blocking comments)
- ✅ v0.5.0 tagged and released
- ✅ Branch protection rule intact (PR flow respected)

---

## 🔍 Key Files

### Source (Template)
- `core/copilot-instructions.md` — Template with override zone markers

### Runtime (Merged via Smart Sync)
- `.github/copilot-instructions.md` — Runtime file (override zones respected)

### Sync Logic
- `.github/active_option_sync.py` — `_sync_with_override_zones()` function

### Audit & Validation
- `rgen/router_audit.py` — Enhanced with coverage validation
- `docs/SYNC_STRATEGY.md` — How smart sync works

### Tests
- `tests/test_agentpilot_guardrails.py` — New guardrail tests (TBD)

---

## 📝 Notes & Considerations

### Backward Compatibility
- All changes are **additive** (no breaking changes)
- Existing routing logic unchanged
- New guardrails are enforced but reasonable (exceptions exist)

### Local Customization
- PMS Stack patterns can now be integrated as local-only sections
- Example: Outside override zone markers, add ESSENTIALS, CRITICAL CONSTRAINTS, PROJECT PROGRESS
- Override zones only touch auto-generated DISPATCHER and PROJECT sections

### Release Cycle
- Current version: v0.4.0
- Next version: v0.5.0 (feature release, no breaking changes)
- Minor version bump justified because new patterns enforce discipline

### Communication
- When merged, update GitHub release notes with guardrail summary
- Update `docs/` to highlight pre-identification and exceptions
- Consider blog post or announcement about "AgentPilot v2: Operational Discipline"

---

## Next Steps

1. **Start Phase 2a**: Add pre-identification to `core/copilot-instructions.md`
2. Test locally: Verify first response includes header with stats
3. Commit with message: `feat: add pre-identification mandatory pattern`
4. Push to feature branch: `git push origin feature/agentpilot-v2-guardrails`
5. Repeat for 2b, 2c, 2d
6. When Phase 2 done, move to Phase 3 (tests)

---

**Plan finalized**: 3 maggio 2026  
**Ready to implement**: Yes  
**Current branch**: `feature/agentpilot-v2-guardrails`  
**Remote status**: Pushed and tracked
