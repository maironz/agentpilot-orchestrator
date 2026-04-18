# Release Notes — AgentPilot Orchestrator

---

## v0.4.0 (P2.8 — MCP Baseline + Open-Core Assets)

**Release Date**: 2026-04-11
**Phase**: MCP hardening, activation flow, and public-facing packaging
**Tag**: `v0.4.0`

### 🎉 What's New

#### MCP Baseline Hardened

The project now ships with a documented and operational MCP baseline for VS Code workflows.

**Highlights**:
- MCP runtime packaging via `pip install -e ".[mcp]"`
- installable MCP entrypoint: `agentpilot-mcp`
- MCP contract documentation in `.github/MCP_CONTRACT.md`
- explicit update policy with `get_update_status` and `manual_update`
- response header status model with `Update` and `MCP`
- runtime MCP status detection aligned with real VS Code logs

#### Standard User Activation Flow

MCP activation is now documented for non-expert users:

- workspace MCP configuration in `.vscode/mcp.json`
- activation guide in `.github/MCP_ACTIVATION.md`
- enable/disable helper in `.github/mcp_configure.py`
- extension recommendations in `.vscode/extensions.json`

#### Documentation and Open-Core Assets

- README expanded with MCP value proposition and onboarding flow
- README now clarifies that MCP does not replace instructions
- open-core asset boundaries, cutover docs, and governance artifacts added

---

### 📊 Metrics

| Metric | Value | Change |
|--------|-------|--------|
| Test Suite | 343/343 | +110 tests |
| MCP Tools | 7 | baseline stabilized |
| MCP Status | Active/Inactive | added runtime reporting |
| Packaging | `agentpilot-mcp` | new entrypoint |

---

### 🧪 Testing

All 343 tests passing.

Includes coverage for:
- branding migration
- cutover snapshot flow
- MCP startup smoke behavior
- secret scanning guardrails
- CORE_FILES expansion (mcp_status.py, update_manager.py)
- CLI timeout guards and network-scan fixture
- integration quality checks for core file count

Run tests:
```bash
pytest tests/ -v
```

---

### 📚 Documentation Updates

- ✅ README.md — MCP onboarding, value explanation, instructions vs MCP
- ✅ `.github/MCP_ACTIVATION.md` — user activation and disable flow
- ✅ `.github/MCP_CONTRACT.md` — MCP tool contract
- ✅ `.github/RELEASE_NOTES.md` — release history updated

---

### 🔄 Backward Compatibility

✅ Backward compatible for existing routing users.

- CLI generation remains available
- MCP is additive, not a replacement for instructions
- update flow remains manual-only

---

## v0.3.0 (P1.3 — Graph Routing)

**Release Date**: 2026-04-07
**Phase**: Cross-Agent Context Bridge Complete
**Tag**: `v0.3.0`

### 🎉 What's New

#### 🔗 Graph Routing with Agent Cascade
Multi-domain queries now supported through dependency graphs:

```bash
python .github/router.py --graph-mode "fix auth bug AND deploy to production"
```

**Features**:
- Scenarios can declare dependencies: `"dependencies": ["secondary_agent", ...]`
- Automatic cascade execution with context forwarding
- Cycle detection prevents infinite loops
- Graceful fallback on failures

#### Example Use Case
```json
{
  "deployment": {
    "agent": "backend",
    "keywords": ["deploy", "release"],
    "dependencies": ["devops"],  ← automatic cascade
    "files": ["backend.md"]
  }
}
```

When a deployment query routes to `backend`, `devops` is automatically invoked in cascade with forwarded context.

---

### 📊 Metrics

| Metric | Value | Change |
|--------|-------|--------|
| Test Coverage | 187/187 | +31 tests |
| Features Complete (P1) | 3/3 | ✅ 100% |
| CLI Modes | 5 | +1 (--graph-mode) |
| Agent Coordination | Graph-based | 1:1 → N:N |

---

### ✨ Phase 1 Summary (Complete)

**What's included**:

1. **P1.1** — Live Metrics Dashboard
   - Real-time TUI monitoring
   - Confidence trending, scenario heatmap
   - Command: `--dashboard`

2. **P1.2** — ML Weight Calibrator
   - Auto-calibrate routing weights from intervention history
   - Decay algorithm (recent > old)
   - Command: `--calibrate-weights` with `--dry-run`

3. **P1.3** — Graph Routing
   - Multi-agent cascade execution
   - Dependency graph validation
   - Command: `--graph-mode`

---

### 🔄 Backward Compatibility

✅ **Fully backward compatible**

- No breaking changes
- `routing-map.json` `"dependencies"` field is optional
- Existing routes work without modification
- Can opt-in to graph routing per scenario

---

### 📚 Documentation Updates

- ✅ README.md — New "Graph Routing" section + usage examples
- ✅ ROADMAP.md — P1.3 marked complete, Phase 2 planned
- ✅ versioning-strategy.md — Hybrid semantic/phase versioning
- ✅ plans/p1-3-graph-routing.plan — Full design documentation

---

### 🚀 Next Phase (P2)

**Estimated**: Week 6-10

1. **P2.1** — Multi-Language Agent Templates
2. **P2.2** — Scenario Evolution Generator
3. **P2.3** — Historical Audit Trail + Rollback

---

### 🧪 Testing

All 187 tests passing:
- 30 tests (P1.1 Live Metrics)
- 17 tests (P1.2 ML Feedback)
- 31 tests (P1.3 Graph Routing)
- 109 existing tests (core + adapter + generation)

Run tests:
```bash
pytest tests/ -v
```

---

### 📖 Migration Guide

**For existing users**:
- No action required
- Existing routing still works
- To enable graph routing:
  1. Add `"dependencies": [...]` to scenarios in `routing-map.json`
  2. Use `--graph-mode` CLI flag instead of `--direct`

**Example**:
```bash
# Old (still works)
python .github/router.py --direct "deploy app"

# New (with cascading)
python .github/router.py --graph-mode "deploy app"
```

---

### 🙏 Credits

Developed as part of Phase 1 strategic initiative.
- **P1.1**: Live dashboard infrastructure
- **P1.2**: ML weight optimization foundation
- **P1.3**: Multi-agent orchestration via graphs

---

### 📝 Changelog

See `.github/ROADMAP.md` for full feature matrix and `.github/plans/` for detailed design docs.

---

## Previous Releases

### v0.2.0 (P1.2 — ML Feedback Loop)
**Date**: 2026-04-06
- RouterWeightCalibrator class
- Intelligent routing weights from intervention history
- `--calibrate-weights` CLI flag

### v0.1.0 (P1.1 — Live Metrics Dashboard)
**Date**: 2026-04-05
- Real-time TUI monitoring
- Routing health metrics
- `--dashboard` CLI mode
