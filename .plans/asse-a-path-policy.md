# Asse A — Path Policy & Whitelist

**Tema**: Implementazione del policy layer centralizzato per il filesystem con whitelist dichiarata e enforcement su `.agentpilot/`.

## Status Implementazione

- ✅ **v1** — `rgen/fs_policy.py`, `tests/test_no_direct_writes.py`
  - `write_file()`, `write_bytes_file()`, `write_atomic()`, `write_best_effort()`
  - `mkdir()`, `delete()` con check whitelist
  - `DIR_MAP` centralizzato
  - Path traversal + symlink resolution safe
  - Case sensitivity Windows normalizzata
  - Strict mode flag
  - GitHub write logging

- ✅ **v2** — Hardening `.github/` + session dynamic whitelist
  - `add_allowed_path()`, `remove_allowed_path()` per isolamento sessione
  - `_audit_github_write()` con log persistente
  - `from_config()` classmethod

- ✅ **v3** — audit_mode + dry_run
  - `audit_mode=True` → logger.INFO su ogni operazione
  - `dry_run=True` → simulate writes senza esecuzione reale
  - Strict mode raise anche in dry_run

## Go/No-Go Criteria

**Go** (v1-v3):
- ✅ Tutte le scritture FS passano per `FSPolicy`
- ✅ `git status` post-run pulito (nessun file fuori `.agentpilot/`)
- ✅ Path traversal e symlink impossibili
- ✅ Exit code non-zero in strict mode su violazione
- ✅ 538+ test passati (v3)

**No-Go** (se una di queste fallisce):
- ❌ Direct `open()`, `write_text()` trovati fuori `fs_policy.py` in `rgen/` o `core/` → test fallisce
- ❌ File scritti in root target senza intentional `.agentpilot/` path
- ❌ Windows case sensitivity non normalizzata
- ❌ Strict mode non blocca in exit code

## Note Tecniche

- Hard enforcement (monkey-patch `pathlib.Path`) rinviato a v4 (richiede isolamento test CI)
- Fallback YAML senza PyYAML: implementato in `rgen/config.py`

## Next Milestone

- **v4**: CLI flags `--fs-audit`, `--fs-dry-run`; hard enforcement evaluation
