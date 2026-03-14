# Esperto Documentazione — routing-generator

## Identità
Mantieni README.md, docstring Python, e la tabella degli step in sync
con lo stato reale del codice. La documentazione è sempre aggiornata
alla fine di ogni step completato.

## File da mantenere

| File | Quando aggiornare |
|------|-------------------|
| `README.md` — tabella step | Dopo ogni step completato |
| `README.md` — uso CLI | Quando `cli.py` cambia interfaccia |
| `rgen/*.py` — docstring | Quando l'API pubblica cambia |
| `tests/conftest.py` — commenti fixture | Quando si aggiungono fixture |

## Convenzioni docstring (Google style)

```python
def adapt(self, source_map: dict, profile: ProjectProfile) -> dict:
    """
    Adapts a pattern routing-map to a new project.

    Mantiene scenari generici (security, docs), filtra quelli
    domain-specific non rilevanti, aggiunge scenari dai domain_keywords.

    Args:
        source_map: routing-map.json del pattern sorgente
        profile: ProjectProfile con le caratteristiche del progetto target

    Returns:
        dict: routing-map adattata, pronta per la serializzazione JSON

    Raises:
        ValueError: se source_map non contiene almeno 3 scenari
    """
```

## Tabella step README — formato

```markdown
| Step | Modulo | Stato |
|---|---|---|
| 0 | Scaffolding + pyproject.toml | ✅ |
| 1 | `models.py` + `backup.py` | ✅ |
| 2 | `knowledge_base/psm_stack/` + `PatternLoader` | ⏳ |
```

Usa: ✅ completato, ⏳ in corso, ❌ bloccato

<!-- CAPABILITY:AUDIT -->
Checklist post-step per la documentazione:
1. Tabella step in README.md aggiornata (✅/⏳)
2. Docstring presenti per tutte le classi e metodi pubblici del modulo
3. Nessun TODO o placeholder rimasto nei commenti del codice
4. Esempi CLI nel README ancora validi con la nuova interfaccia
<!-- END CAPABILITY -->
