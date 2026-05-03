# Asse E — Test Suite (Hygiene)

**Tema**: Coverage affidabile per workspace hygiene su Windows/Linux/macOS.

## Status Implementazione

- ✅ **v1** — Test statici + snapshot
  - `tests/test_no_direct_writes.py` — AST scan per direct `open()`, `write_text()` fuori fs_policy.py
  - `tests/test_github_write_hardening.py` — 12 test per github write policy
  - Cross-platform: Windows path case, Linux separator, symlink checks

- ✅ **v2** — Session + Lifecycle tests
  - `tests/test_session_context.py` — 22 test per UUID uniqueness, isolation, atexit register
  - `tests/test_lifecycle.py` — 20 test per rotate_logs, cap_cache, clean_tmp
  - Platform-agnostic path resolution

- ✅ **v3** — Strict mode + Read Policy + Audit/Dry-Run
  - `tests/test_strict_mode.py` — 6 test subprocess exit code verification
  - `tests/test_read_policy.py` — 37 test for sensitive patterns, allow/deny, strict/non-strict
  - `tests/test_fs_audit_dryrun.py` — 14 test for audit_mode=True, dry_run=True combined

- ✅ **Total**: 538 passed, 1 skipped (Python 3.10/3.11/3.12 CI green)

## Go/No-Go Criteria

**Go** (v1-v3):
- ✅ 0 direct `open()` calls trovati fuori `fs_policy.py`
- ✅ All platform separators handled correctly (Path.resolve())
- ✅ Symlink resolution doesn't escape whitelist
- ✅ Subprocess exit codes non-zero in strict violations
- ✅ 538+ test coverage
- ✅ CI matrix Python 3.10/3.11/3.12 all green

**No-Go** (se una di queste fallisce):
- ❌ Direct write calls trovati nei moduli
- ❌ Test fallisce su Linux per path handling
- ❌ Symlink escape possibile
- ❌ Exit code 0 su strict violation
- ❌ Test < 500 total

## Note Tecniche

- Tests non isolano monkey-patching (v1 choice)
- Platform detection via `platform.system()` nel core code
- Windows case normalization fatto in `_normalize()` helper

## Next Milestone

- **v4**: Hard enforcement via conftest pytest fixture (isolated patching)
- **v4**: Performance benchmarks per path resolution overhead
