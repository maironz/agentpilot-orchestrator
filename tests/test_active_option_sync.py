from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_active_sync_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / ".github" / "active_option_sync.py"
    spec = importlib.util.spec_from_file_location("active_option_sync_test_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_active_option_status_detects_drift(tmp_path: Path, monkeypatch) -> None:
    module = _load_active_sync_module()

    root = tmp_path / "repo"
    (root / "core").mkdir(parents=True)
    (root / ".github").mkdir(parents=True)

    (root / "core" / "router.py").write_text("# core", encoding="utf-8")
    (root / ".github" / "router.py").write_text("# active", encoding="utf-8")

    monkeypatch.setattr(module, "_repo_root", lambda: root)

    status = module.get_active_option_status()
    assert status["status"] == "outdated"
    assert status["update_available"] is True
    assert status["drift_count"] == 1
    assert ".github/router.py" in status["drift_files"]


def test_active_option_apply_sync_updates_file(tmp_path: Path, monkeypatch) -> None:
    module = _load_active_sync_module()

    root = tmp_path / "repo"
    (root / "core").mkdir(parents=True)
    (root / ".github").mkdir(parents=True)

    (root / "core" / "router.py").write_text("# core", encoding="utf-8")
    (root / ".github" / "router.py").write_text("# old", encoding="utf-8")

    monkeypatch.setattr(module, "_repo_root", lambda: root)

    result = module.apply_active_option_update(confirm=True)
    assert result["updated"] is True
    assert result["status"] == "updated"
    assert (root / ".github" / "router.py").read_text(encoding="utf-8") == "# core"
