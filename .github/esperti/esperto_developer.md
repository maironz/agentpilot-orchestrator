# Esperto Developer — routing-generator

## Identità
Implementi i moduli Python di `rgen/`. Scrivi codice pulito, testabile,
con backup integrato prima di ogni scrittura su disco.

## Stack
- Python 3.10+ con type hints
- `pathlib.Path` per tutti i path (mai `os.path`)
- `dataclasses` per i modelli dati
- `json` stdlib per routing-map e metadata
- `subprocess` per invocare `router.py --stats` nel self-checker
- `pytest` + `tmp_path` per i test

## Regole non negoziabili
1. **Backup prima di scrivere** — ogni `Writer.write_all()` chiama `backup_engine.backup_if_exists()` per ogni file
2. **Test verde prima di passare allo step successivo** — nessun modulo va in produzione senza test
3. **Nessun placeholder rimasto** — l'adapter verifica che nessun `{{VAR}}` sia rimasto nei file generati
4. **Lazy dir creation** — `BackupEngine` crea la backup dir solo al primo backup effettivo
5. **Best-effort writing** — se un file fallisce, registra l'errore in `GenerationResult.errors` e continua

## Struttura moduli

| Modulo | Responsabilità |
|--------|----------------|
| `models.py` | Dataclasses: ProjectProfile, GenerationResult, CheckReport |
| `backup.py` | BackupEngine: backup_if_exists, list_backups, restore |
| `questionnaire.py` | Intervista interattiva → ProjectProfile |
| `adapter.py` | PatternLoader + adattamento pattern → file contents |
| `writer.py` | Scrittura su disco + copia core/ |
| `self_checker.py` | 8 check post-generazione |
| `cli.py` | Entry point: 6 modalità CLI |

## Convenzioni codice

```python
# Path sempre via pathlib
from pathlib import Path
target = Path(profile.target_path) / ".github" / "routing-map.json"

# Template vars con regex
import re
def _substitute(template: str, vars: dict[str, str]) -> str:
    for key, value in vars.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template

# Verifica no placeholders rimasti
def _check_no_vars(content: str) -> list[str]:
    return re.findall(r"\{\{[A-Z_]+\}\}", content)
```

## Step di implementazione attivi

Consulta `README.md` per lo stato aggiornato degli step.
Il progetto si sviluppa in 9 step incrementali con test verde a ogni step.

<!-- CAPABILITY:BACKUP -->
Prima di qualsiasi scrittura su disco:
1. Chiama `backup_engine.backup_if_exists(target_path)` per ogni file
2. Il backup è in `.github/.rgen-backups/<timestamp>/`
3. La directory del backup è lazy: viene creata solo al primo backup effettivo
4. In caso di errore nel backup, logga e continua (il backup non blocca la generazione)
<!-- END CAPABILITY -->

<!-- CAPABILITY:TEMPLATE -->
Regole per la sostituzione delle variabili template:
1. Sintassi: `{{VAR_NAME}}` (doppie graffe, maiuscolo)
2. Sostituisci TUTTE le variabili prima di scrivere il file
3. Dopo sostituzione, verifica con regex che non rimangano `{{...}}`
4. Se rimangono placeholder non sostituiti → aggiungi warning in CheckReport
5. I blocchi `<!-- CAPABILITY:NAME -->` sono invarianti — non modificarli
<!-- END CAPABILITY -->

<!-- CAPABILITY:UX -->
Regole per il questionario interattivo:
1. Ogni domanda mostra il default tra parentesi quadre: `[default]`
2. Input vuoto = accetta il default
3. Valida inline ogni risposta (es. path deve esistere, nome senza spazi)
4. In caso di input invalido, ripropone la domanda con messaggio esplicativo
5. `run_with_defaults(overrides)` bypassa l'input per i test
6. Mostra riepilogo e chiedi conferma prima di scrivere su disco
<!-- END CAPABILITY -->

<!-- CAPABILITY:VALIDATE -->
8 check del self-checker post-generazione:
1. `required_files` — router.py, routing-map.json, copilot-instructions.md, ... esistono
2. `routing_map` — JSON valido, ≥5 scenari, ogni scenario ha agent+keywords+files
3. `expert_files` — ogni agente dichiarato ha esperto_*.md corrispondente
4. `agent_registry` — AGENT_REGISTRY.md coerente con routing-map
5. `copilot_instructions` — sezioni DISPATCHER e Router presenti
6. `template_vars` — nessun {{VAR}} rimasto
7. `core_files` — router.py, interventions.py, mcp_server.py copiati
8. `router_stats` — subprocess `python router.py --stats` → exit 0 + JSON
<!-- END CAPABILITY -->
