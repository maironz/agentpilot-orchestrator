# Asse X — Audit Mode & Dry-Run FS

**Tema**: Debugging und visibility: logga tutte le operazioni FS e simula le operazioni senza esecuzione.

## Status Implementazione

- ❌ **v1** — Non pianificato

- ❌ **v2** — Non pianificato

- ✅ **v3** — Completo
  - `FSPolicy.__init__()` aggiunto: `audit_mode=False`, `dry_run=False`
  - **audit_mode=True**: `logger.info()` su ogni `write_file`, `write_bytes_file`, `write_atomic`, `mkdir`, `delete`
    - Log format: `"fs_policy audit: <method> path=<path> dry_run=<flag>"`
  - **dry_run=True**: policy check + log (se audit_mode) ma NO file creation/deletion
    - Strict mode ancora raise anche in dry_run
    - Policy checks unchanged (whitelist still enforced)
  - Combined audit_mode + dry_run: log emesso, niente scritto
  - `tests/test_fs_audit_dryrun.py` — 14 test coprendo tutti gli scenari

## Go/No-Go Criteria

**Go** (v3):
- ✅ Audit mode emette INFO log su ogni operazione
- ✅ Dry-run blocca writes, log still emesso
- ✅ Policy checks ancora executed in dry-run (strict raises)
- ✅ Combined audit+dry-run: log + no write
- ✅ Non-audit, non-dry default (backward compat)
- ✅ 14 test passed

**No-Go** (se una di queste fallisce):
- ❌ Audit mode no log on operations
- ❌ Dry-run crea file anyway
- ❌ Policy checks skipped in dry-run
- ❌ Strict mode bypassed in dry-run
- ❌ Default behavior changed

## Note Tecniche

- Audit log level: INFO (non DEBUG) per visibility
- Dry-run non crea temp files (write_atomic skip mkstemp)
- Policy validation happens BEFORE dry_run check (fail-fast)
- No integration yet in CLI (v4 task)

## Next Milestone

- **v4**: CLI flags `--fs-audit`, `--fs-dry-run` per CLI entry
- **v4**: Audit log redirection to file (default: logger)
- **v4**: Dry-run stats report (N files would create, N would delete, etc.)
