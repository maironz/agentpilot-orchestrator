# Asse D — Strict Mode & Error Handling

**Tema**: Enforce non-negotiable policy violations in strict enterprise mode.

## Status Implementazione

- ✅ **v1** — Strict flag in `FSPolicy`
  - `--fs-strict` exit code != 0 on violation
  - `PolicyViolation(RuntimeError)` raised in strict mode
  - Default non-strict: warning only

- ✅ **v2** — Non implementato specificamente (v1 sufficiente)

- ✅ **v3** — Test rigorosi
  - `tests/test_strict_mode.py` — 6 test subprocess verificano exit code non-zero
  - Strict mode blocca anche `.github/` write se `allow_github_write: false`
  - Dry-run non bypassa strict mode (ancora raise)

## Go/No-Go Criteria

**Go** (v1-v3):
- ✅ Write fuori whitelist in strict mode → PolicyViolation raised
- ✅ Exit code 1 su policy violation (subprocess test)
- ✅ Non-strict mode emette warning, continua
- ✅ `--fs-strict` flag onorato da `from_config()`
- ✅ 6 test passati (test_strict_mode.py)

**No-Go** (se una di queste fallisce):
- ❌ Strict mode non raise PolicyViolation
- ❌ Non-strict mode raise invece di warn
- ❌ Exit code 0 su violation in strict mode
- ❌ Dry-run bypassa strict mode

## Note Tecniche

- Strict mode è opt-in (default false in config.yaml)
- PolicyViolation è subclass di RuntimeError per compat
- Subprocess test verifica exit code (non catchable da parent)

## Next Milestone

- **v4**: CLI flag `--fs-strict` per override runtime config
