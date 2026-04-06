# Versioning Strategy — routing-generator

**Status**: Active | **Last updated**: 2026-04-06

---

## Overview

Usiamo un sistema **Hybrid versioning** a due layer:

| Layer | Format | Purpose | Example |
|-------|--------|---------|---------|
| **Semantic** | `vX.Y.Z` | Git tags, package releases, external visibility | `v0.2.0`, `v0.3.0` |
| **Phase** | `pX.Y` | Internal dev tracking, branch names, narrative | `p1.1`, `p1.2`, `p1.3` |

---

## Mapping Table

Questo è il nostro **source of truth** per correlazione:

| Phase | Semantic | Feature | Status | Branch |
|-------|----------|---------|--------|--------|
| p1.1 | v0.1.0 | Live Router Metrics Dashboard | ✅ DONE | (merged) |
| p1.2 | v0.2.0 | ML Feedback Loop + Router Integration | ✅ DONE | release/p1.2-complete |
| p1.3 | v0.3.0 | Cross-Agent Context Bridge (Graph Routing) | 🟡 NEXT | feature/p1.3-graph-routing |
| p2.1 | v0.4.0 | Multi-Language Agent Templates | ❌ TODO | - |
| p2.2 | v0.5.0 | Scenario Evolution Generator | ❌ TODO | - |
| p2.3 | v0.6.0 | Historical Audit Trail + Rollback | ❌ TODO | - |
| p3.1 | v0.7.0 | Pattern Marketplace / GitHub Discovery | ❌ TODO | - |
| p3.2 | v0.8.0 | Cost Estimator | ❌ TODO | - |
| p4.1 | v0.9.0 | IDE Extensions (VS Code) | ❌ TODO | - |
| p4.2 | v1.0.0 | Stochastic Testing Mode | ❌ TODO | v1.0.0 = GA |

---

## Rules

### ✅ Semantic Versioning (`vX.Y.Z`)

**When to increment**:
- **MAJOR (X)**: Breaking changes, significant refactor (+ 109 → 200 tests)
- **MINOR (Y)**: New feature complete + merged to master = phase increment
- **PATCH (Z)**: Bug fixes, docs, non-feature PRs

**Usage**:
```bash
# After phase merge to master:
git tag -a v0.2.0 -m "p1.2: ML Feedback Loop Complete"
git push origin v0.2.0

# pyproject.toml, __init__.py:
version = "0.2.0"
```

**Visibility**:
- Public on GitHub releases page
- Package managers (PyPI if applicable)
- External APIs

---

### 🟠 Phase Naming (`pX.Y`)

**When to use**:
- Branch names: `release/p1.2-complete`, `feature/p1.3-graph-routing`
- Commit messages: `feat(p1.2): ML weight calibrator integration`
- Internal docs: ROADMAP.md, MEMORY.md
- CLI/internal tracking

**Format**:
- `p1` = Phase 1 core features (Live Metrics + ML + Graph)
- `p1.1` = Phase 1.1 sub-feature (Live Metrics)
- `p1.2` = Phase 1.2 sub-feature (ML Feedback Loop)
- `p2` = Phase 2 (Multi-Language, Scenario Evolution, etc.)

**Visibility**:
- Internal only (dev team, ROADMAP)
- Branch names and commit history
- Not in version strings or releases

---

## Workflow

```
Brainstorm
    ↓
Decision: next phase name (e.g., "p1.3")
    ↓
Create branch: feature/p1.3-graph-routing
    ↓
Development (commit messages use p1.3 tag)
    ↓
PR + code review
    ↓
Merge to master
    ↓
Tag: git tag -a v0.3.0 -m "p1.3: Complete"
    ↓
Update MEMORY.md + ROADMAP.md with status ✅ DONE
    ↓
Close/update GitHub Issues
    ↓
Next phase: repeat
```

---

## Examples

### Commit Messages
```bash
# Good:
git commit -m "feat(p1.2): Integrate RouterWeightCalibrator into router.py"
git commit -m "fix(p1.2): Handle missing interventions.db gracefully"

# Bad:
git commit -m "Add weights"  # Too vague, no phase
git commit -m "feat(v0.2.0): ..."  # Semantic tag in commit is unusual
```

### Branch Names
```bash
# Good:
git checkout -b feature/p1.3-graph-routing
git checkout -b release/p1.2-complete
git checkout -b docs/p1.2-updates

# Bad:
git checkout -b feature/v0.3.0-graph  # Semantic in branch is odd
git checkout -b feature/graph-routing  # Missing phase context
```

### PR Titles
```bash
# Good:
"feat(p1.2): ML weight calibrator + router integration"
"docs(p1.2): Update README with calibration examples"

# Bad:
"v0.2.0: ML Feedback Loop"  # Semantic in PR title
"Fix stuff"  # No phase context
```

---

## File References

**Files that declare version**:
- `pyproject.toml` → `version = "0.2.0"` (semantic only)
- `README.md` → Badge shows `tests-156%2F156` (no version number exposed)
- `__init__.py` → `__version__ = "0.2.0"` (if exists)
- `.github/ROADMAP.md` → Uses phase names (p1.1, p1.2, etc.)
- `.github/MEMORY.md` → Uses phase names + semantic mapping

**Do NOT mix in these files**:
- Avoid `p1.2` in version strings
- Avoid `v0.2.0` in branch names (use `release/p1.2-complete` instead)

---

## Future Considerations

When we reach `v1.0.0` (GA):
- Phase naming continues internally (p5, p6, ...)
- Semantic versioning may switch to `1.Y.Z` (minor/patch only)
- Document in separate `v1-roadmap.md` if major redesign needed

---

## Approval

**Owner**: Massimo | **Status**: Active | **Last review**: 2026-04-06
