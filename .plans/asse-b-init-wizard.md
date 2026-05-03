# Asse B — Init Wizard & Config

**Tema**: Setup iniziale guidato con proposal gitignore, config YAML, e best-practices.

## Status Implementazione

- ✅ **v1** — Placeholder per wizard (non implementato in v1)

- ✅ **v2** — Config + Gitignore Wizard
  - `rgen/config.py` — `AgentPilotConfig` dataclass con loader/saver YAML
  - `rgen/gitignore_wizard.py` — wizard interattivo per `.gitignore` entries
  - Schema: `fs_strict`, `allow_github_write`, `track_artifacts`, `cleanup_on_exit`
  - Fallback serialization senza PyYAML
  - `_entry_in_content()` idempotency fix

- ✅ **v3** — Completo
  - `pyyaml>=6.0` aggiunto alle dev deps
  - Fallback parser implementato (legge `key: true/false` senza yaml module)

## Go/No-Go Criteria

**Go** (v2-v3):
- ✅ `.agentpilot/config.yaml` creato in first run
- ✅ Wizard propone `.gitignore` entries all'utente
- ✅ Round-trip save+load preserva tutti i 4 flag
- ✅ Fallback YAML parsing funziona senza PyYAML
- ✅ 28 test passati (test_config.py + test_gitignore_wizard.py)

**No-Go** (se una di queste fallisce):
- ❌ Config file non creato in `.agentpilot/`
- ❌ Gitignore wizard non propone `.agentpilot/` entry
- ❌ Round-trip fallisce (save scrive, load non legge)
- ❌ Fallback parser non gestisce YAML-less caso

## Note Tecniche

- Wizard non è obbligatorio (default non-interactive) → setup può saltare
- YAML dependency è opzionale ma consigliata
- Config è single-file (non per-session)

## Next Milestone

- **v4**: CLI integration per `--init-wizard`, interactive prompts
