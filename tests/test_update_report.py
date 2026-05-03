from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_update_report_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / ".github" / "update_report.py"

    sys.path.insert(0, str(module_path.parent))
    try:
        spec = importlib.util.spec_from_file_location("update_report_test_module", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_update_report_need_update_includes_link_fields(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_update_report_module()

    monkeypatch.setattr(
        module,
        "get_active_option_status",
        lambda: {
            "source": "active-option",
            "status": "outdated",
            "update_available": True,
            "compared_files": 7,
            "drift_count": 2,
            "drift_files": [".github/router.py", ".github/update_manager.py"],
            "manual_update_command": "python .github/active_option_sync.py --apply",
        },
    )
    monkeypatch.setattr(module, "apply_active_option_update", lambda confirm: {"status": "updated", "updated": True})

    output = tmp_path / "UPDATE_STATUS.md"
    monkeypatch.setattr(sys, "argv", ["update_report.py", "--output", str(output)])

    rc = module.main()
    assert rc == 0

    payload = json.loads(capsys.readouterr().out.strip())
    expected_path = str(output).replace("\\", "/")
    assert payload["update_label"] == "Need Update"
    assert payload["update_value"] == f"[Need Update]({expected_path})"
    assert payload["update_link_target"] == expected_path

    report = output.read_text(encoding="utf-8")
    assert "Banner label: Need Update" in report
    assert "Banner value: [Need Update](" in report
    assert "## Manual Update" in report
    assert "python .github/active_option_sync.py --apply" in report
    assert "Source: active-option" in report


def test_update_report_ok_has_no_link_target(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_update_report_module()

    monkeypatch.setattr(
        module,
        "get_active_option_status",
        lambda: {
            "source": "active-option",
            "status": "up-to-date",
            "update_available": False,
            "compared_files": 7,
            "drift_count": 0,
            "drift_files": [],
            "manual_update_command": "python .github/active_option_sync.py --apply",
        },
    )
    monkeypatch.setattr(module, "apply_active_option_update", lambda confirm: {"status": "up-to-date", "updated": False})
    monkeypatch.setattr(
        module,
        "get_remote_version_status",
        lambda no_refresh=False: {
            "branch_state": "in-sync",
            "update_available": False,
            "remote_commit": "abc123def456",
        },
    )

    output = tmp_path / "UPDATE_STATUS.md"
    monkeypatch.setattr(sys, "argv", ["update_report.py", "--output", str(output)])

    rc = module.main()
    assert rc == 0

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["update_label"] == "ok"
    assert payload["update_value"] == "ok"
    assert payload["update_link_target"] is None

    report = output.read_text(encoding="utf-8")
    assert "## Manual Update" in report
    assert "python .github/active_option_sync.py --apply" in report


def test_update_report_auto_mode_calls_manual_update(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_update_report_module()

    monkeypatch.setattr(
        module,
        "get_active_option_status",
        lambda: {
            "source": "active-option",
            "status": "outdated",
            "update_available": True,
            "compared_files": 7,
            "drift_count": 1,
            "drift_files": [".github/router.py"],
            "manual_update_command": "python .github/active_option_sync.py --apply",
        },
    )

    called = {"value": False}

    def _apply_active_option_update(confirm: bool):
        called["value"] = True
        assert confirm is True
        return {"status": "updated", "updated": True, "message": "done"}

    monkeypatch.setattr(module, "apply_active_option_update", _apply_active_option_update)

    output = tmp_path / "UPDATE_STATUS.md"
    monkeypatch.setattr(sys, "argv", ["update_report.py", "--output", str(output), "--auto"])

    rc = module.main()
    assert rc == 0

    payload = json.loads(capsys.readouterr().out.strip())
    assert called["value"] is True
    assert payload["auto_update_requested"] is True
    assert payload["auto_update_status"] == "updated"

    report = output.read_text(encoding="utf-8")
    assert "## Auto Update Result" in report
