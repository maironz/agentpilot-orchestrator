# routing-generator — Subagent Brief

Tool Python che genera sistemi di routing AI da pattern esistenti.

## Stack
- Python 3.12 | pathlib | dataclasses | json | subprocess | pytest

## Path
| Path | Contenuto |
|------|-----------|
| `rgen/` | Package: cli, questionnaire, adapter, writer, backup, self_checker, models |
| `knowledge_base/psm_stack/` | Pattern PSM Stack (routing-map, agents, templates) |
| `core/` | File invarianti copiati nei progetti target |
| `tests/` | pytest unit + integration |

## Vincoli
1. Test verde prima di avanzare allo step successivo
2. BackupEngine attivo prima di ogni scrittura su disco
3. tmp_path nei test — mai filesystem reale
4. Nessun {{VAR}} rimasto dopo template substitution
