# Asse F — Read Policy (Sensitive Files)

**Tema**: Warn/block su lettura accidentale di file sensibili (.env, secrets, credenziali).

## Status Implementazione

- ❌ **v1** — Non implementato (pianificato)

- ❌ **v2** — Non implementato (after v1 priority)

- ✅ **v3** — Completo
  - `rgen/read_policy.py` — `ReadPolicy` class per check file sensibili
  - Sensitive patterns: `.env*`, `secrets.*`, `*.pem`, `*.key`, `*.pfx`, `*.p12`, `credentials.*`, `.netrc`, `id_*` (SSH keys)
  - Metodi: `is_sensitive()`, `check_read()`, `read_file()`, `read_bytes()`, `allow()`, `deny()`
  - Strict mode: raise `ReadPolicyViolation`
  - Non-strict mode: warning emesso
  - Allowed paths whitelist: skip check per authorized files (e.g., `.env.example`)
  - `tests/test_read_policy.py` — 37 test, 1 skip (documented)

## Go/No-Go Criteria

**Go** (v3):
- ✅ Read `.env` triggers `is_sensitive()` detection
- ✅ Strict mode raises `ReadPolicyViolation` on sensitive read
- ✅ Non-strict mode warns, continues
- ✅ Allowed paths bypass sensitivity check
- ✅ All sensitive patterns covered by regex tests
- ✅ 37 test passed, 1 skip (intentional)

**No-Go** (se una di queste fallisce):
- ❌ Sensitive patterns non detected
- ❌ Strict mode non raise
- ❌ Non-strict mode raise instead of warn
- ❌ Allowed paths not respected
- ❌ Test < 35 passed

## Note Tecniche

- Pattern matching case-insensitive (regex IGNORECASE flag)
- Allowed paths check resolve paths per symlink safety
- No integration yet in CLI (v4 task)
- ReadPolicyViolation subclass RuntimeError per compat

## Next Milestone

- **v4**: CLI flag `--fs-read-strict` per override runtime
- **v4**: Integration con `FSPolicy` per coordinated checks
