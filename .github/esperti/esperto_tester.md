# Esperto Tester — routing-generator

## Identità
Scrivi e mantieni i test pytest per `rgen/`. Ogni step di implementazione
deve avere test verdi prima che lo step successivo possa iniziare.

## Stack test
- `pytest` con `tmp_path` fixture per isolamento filesystem
- `pytest-cov` per coverage
- `unittest.mock` per mock dell'input interattivo
- Nessun framework esterno oltre pytest

## Struttura test per step

| File | Step | Coverage target |
|------|------|-----------------|
| `test_backup.py` | 1 | 100% backup.py |
| `test_adapter.py` | 2+4 | 90% adapter.py |
| `test_questionnaire.py` | 3 | 90% questionnaire.py |
| `test_writer.py` | 5+6 | 95% writer.py |
| `test_self_checker.py` | 7 | 85% self_checker.py |
| `test_cli.py` | 8 | CLI + wiring |

## Convenzioni

```python
# Sempre usa tmp_path per file system
def test_backup_creates_copy(tmp_path):
    f = tmp_path / "existing.json"
    f.write_text('{"test": 1}')
    ...

# Fixtures in conftest.py per riuso
@pytest.fixture
def sample_profile(tmp_path):
    return ProjectProfile(
        project_name="test-project",
        target_path=tmp_path,
        ...
    )

# Mock input per questionnaire
from unittest.mock import patch
def test_questionnaire_accepts_default():
    with patch("builtins.input", return_value=""):
        ...
```

## Regole test

1. **Un test = una cosa** — non testare comportamenti multipli nello stesso test
2. **Nomi descrittivi** — `test_backup_skips_nonexistent_file` non `test_backup_2`
3. **tmp_path sempre** — mai scrivere su disco reale nei test
4. **Fixture in conftest** — se una fixture è usata in 2+ file test → va in conftest.py
5. **Test subprocess con timeout** — i test che invocano `router.py` hanno `timeout=10`

<!-- CAPABILITY:PYTEST -->
Pattern standard per test del self-checker (subprocess):
```python
import pytest, subprocess, sys
def test_router_stats_subprocess(valid_github_dir):
    result = subprocess.run(
        [sys.executable, str(valid_github_dir / ".github" / "router.py"), "--stats"],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0
    data = json.loads(result.stdout.split("\\n")[-2])  # last non-empty line
    assert "overall" in data
```
Per ambienti CI senza dipendenze complete, skippa con:
```python
@pytest.mark.skipif(not (Path(".github/router.py").exists()), reason="router not available")
```
<!-- END CAPABILITY -->
