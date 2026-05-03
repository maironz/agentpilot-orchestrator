# Asse C — Structure & Lifecycle

**Tema**: Organizzazione delle cartelle `.agentpilot/` con separazione runtime/artifacts, e cleanup automatico.

## Status Implementazione

- ✅ **v1** — Struttura base
  - Cartelle: `.agentpilot/logs/`, `state/`, `cache/`, `tmp/`, `reports/`, `backups/`, `artifacts/`
  - Separazione chiara: `runtime/` vs `artifacts/`

- ✅ **v2** — Session isolation + Lifecycle
  - `rgen/session_context.py` — session-per-run con UUID 8-char, session.json creation/end
  - Dynamic whitelist: `f".agentpilot/runtime/state/{session_id}/**"`
  - `rgen/lifecycle.py` — `LifecycleManager` per cleanup
  - `rotate_logs(keep=N)` — mantiene N log più recenti
  - `cap_cache(max_bytes=M)` — evicta oldest files se size > limit
  - `clean_tmp()` — purga tutto `.agentpilot/tmp/`
  - `register_atexit_if_configured()` — auto-cleanup on exit se flagged

- ✅ **v3** — Completo
  - 22 test per session_context, 20 test per lifecycle
  - PyYAML fallback fix garantisce config read anche senza YAML

## Go/No-Go Criteria

**Go** (v1-v3):
- ✅ Cartelle create nel primo access (mkdir non raise)
- ✅ Session dir isolato con UUID
- ✅ Cleanup su exit non interferisce con user files
- ✅ Log rotation mantiene mtime order
- ✅ Cache cap rispetta byte limit
- ✅ 481+ test passati (v3)

**No-Go** (se una di queste fallisce):
- ❌ Cartelle non create all'inizio
- ❌ Session ID non unico o non isolato
- ❌ Cleanup cancella file user
- ❌ Log rotation non riordina per mtime
- ❌ Cache cap evicta file non-oldest

## Note Tecniche

- Cleanup è opzionale (flag `cleanup_on_exit` in config)
- Session ID è opzionale (default no isolation) in v2
- Atexit hook registra automaticamente se config.cleanup_on_exit = true

## Next Milestone

- **v4**: Aggiungere shardable session dirs per concurrent runs
