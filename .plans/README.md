# .plans/ — Governance Structure for AgentPilot Workspace Hygiene

Questa cartella contiene il piano di governance per il **Workspace Hygiene Project** (v1→v3 completato, v4+ in backlog).

Ogni file rappresenta un **asse** del progetto con:
- **Status**: v1/v2/v3 completezza implementativa
- **Go/No-Go Criteria**: checklist di validazione
- **Next Milestone**: prossima release pianificata

## Assi Implementati

| Asse | Tema | Status | Next |
|------|------|--------|------|
| [A — Path Policy](asse-a-path-policy.md) | Whitelist FS + FSPolicy | ✅ v1-v3 | v4: CLI flags |
| [B — Init Wizard](asse-b-init-wizard.md) | Config YAML + .gitignore setup | ✅ v2-v3 | v4: Interactive prompts |
| [C — Structure](asse-c-structure.md) | `.agentpilot/` folders + lifecycle cleanup | ✅ v1-v3 | v4: Concurrent sharding |
| [D — Strict Mode](asse-d-strict-mode.md) | Enterprise policy enforcement | ✅ v1-v3 | v4: CLI override flag |
| [E — Tests](asse-e-tests.md) | Cross-platform test coverage | ✅ v1-v3 | v4: Hard enforcement via pytest |
| [F — Read Policy](asse-f-read-policy.md) | Sensitive file detection | ✅ v3 | v4: CLI + FSPolicy integration |
| [X — Audit/Dry-Run](asse-x-audit.md) | Logging + simulation mode | ✅ v3 | v4: CLI flags + report |

## Release Timeline

- ✅ **v1** (Commit 300cbf2) — FSPolicy core + path safety + static tests
- ✅ **v2** (Commits 54d776b, ab67e08, 79d034b, 34fa4e8) — Config, session isolation, lifecycle, github logging
- ✅ **v3** (Commit 06a5779) — Strict mode subprocess tests, read policy, audit_mode+dry_run
- ✅ **CI Fix** (Commit 32315d7) — PyYAML fallback parser + dev deps
- 🔄 **v4** (Planned) — CLI integration, hard enforcement, performance

## Validation Status

- **Test Coverage**: 538 passed, 1 skipped (Python 3.10/3.11/3.12)
- **CI Status**: ✅ All matrix green (Run #51)
- **Repository**: https://github.com/maironz/agentpilot-orchestrator

## Historical Reference

Sessione originale di brainstorming: [.discussioni/2026-05-01-privacy-tracciabilita-repo.md](../.discussioni/2026-05-01-privacy-tracciabilita-repo.md)
