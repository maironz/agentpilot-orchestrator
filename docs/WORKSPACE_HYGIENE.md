# Workspace Hygiene

AgentPilot non deve lasciare tracce non attese nel repository target che lo ospita.
Tutte le scritture avvengono sotto una cartella root dedicata (`.agentpilot/`) e nulla
viene scritto fuori da percorsi dichiarati senza avviso esplicito.

---

## Struttura `.agentpilot/`

```
.agentpilot/
├── runtime/
│   └── state/          # stato sessione, interventions.db
├── logs/               # log operativi
├── cache/              # cache versioni remote e simili
├── tmp/                # file temporanei, svuotati a fine run
├── reports/            # output report (update status, ecc.)
├── backups/            # backup snapshot generazioni rgen
└── artifacts/          # artefatti tracciabili (opzionale)
```

---

## Policy di scrittura (default)

| Percorso | Consentito | Note |
|---|---|---|
| `.agentpilot/**` | ✅ sempre | root whitelisted |
| `.github/**` | ⚠️ con log | solo se `allow_github_write: true` in config; sempre loggato |
| Qualsiasi altro path | ❌ warning | in strict mode: errore bloccante |

---

## Annotazione `# fs-policy: ok`

Le scritture su path specificato **dall'utente** via argomento CLI (es. `--output`,
`--history-output`) non passano per `FSPolicy` perché il path è scelto esplicitamente
dall'utente. Queste righe sono annotate con `# fs-policy: ok` per sopprimere il test
statico `test_no_direct_writes`.

---

## `FSPolicy` API

Modulo: `rgen/fs_policy.py`

```python
from rgen.fs_policy import FSPolicy

policy = FSPolicy(project_root=Path("."), strict=False)

# Scrittura standard con check whitelist
policy.write_file(policy.DIR_MAP["state"] / "session.json", content)

# Scrittura atomica (write-then-rename) — per state/ e cache/
policy.write_atomic(policy.DIR_MAP["cache"] / "version.json", data)

# Scrittura best-effort — per logs/ e tmp/ (non solleva eccezioni)
policy.write_best_effort(policy.DIR_MAP["logs"] / "run.log", line)

# Crea directory con check whitelist
policy.mkdir(policy.DIR_MAP["tmp"] / "extraction")

# Elimina file con check whitelist
policy.delete(policy.DIR_MAP["tmp"] / "archive.zip")
```

### `DIR_MAP` — path logiche → fisiche

```python
policy.DIR_MAP["state"]    # .agentpilot/runtime/state/
policy.DIR_MAP["logs"]     # .agentpilot/logs/
policy.DIR_MAP["cache"]    # .agentpilot/cache/
policy.DIR_MAP["tmp"]      # .agentpilot/tmp/
policy.DIR_MAP["reports"]  # .agentpilot/reports/
policy.DIR_MAP["backups"]  # .agentpilot/backups/
policy.DIR_MAP["artifacts"]# .agentpilot/artifacts/
```

Usare sempre `DIR_MAP` invece di hardcodare il path fisico.

---

## Strict mode (`--fs-strict`)

In strict mode ogni scrittura fuori whitelist causa `PolicyViolation` con exit code
non-zero. Utile in ambienti CI o pipeline enterprise.

```python
policy = FSPolicy(project_root=Path("."), strict=True)
```

---

## Test statico anti-bypass

`tests/test_no_direct_writes.py` scansiona tutti i file in `rgen/` e `core/` e
fallisce se trova pattern di scrittura diretta (`open(` write mode, `write_text(`,
`write_bytes(`) non annotati con `# fs-policy: ok`.

Esecuzione:

```bash
pytest tests/test_no_direct_writes.py
```

---

## `.gitignore` raccomandato nel target

Aggiungere nel `.gitignore` del repository target:

```gitignore
# AgentPilot workspace — non versionare
.agentpilot/
```

Se si vuole tracciare gli artefatti di reporting:

```gitignore
.agentpilot/
!.agentpilot/reports/
!.agentpilot/artifacts/
```

---

## Garanzia accettazione

Dopo un'esecuzione standard nel target, `git status` non deve mostrare file
nuovi o modificati fuori da `.agentpilot/` e `.github/` (se `allow_github_write`
è abilitato).

In strict mode ogni violazione produce exit code non-zero verificabile in CI.
