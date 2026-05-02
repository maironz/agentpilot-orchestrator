from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    script_path = Path(__file__).parent.parent / ".github" / "mcp_status.py"
    spec = importlib.util.spec_from_file_location("mcp_status_for_tests", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_get_mcp_status_returns_standby_when_configured_but_not_running(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "mcp.json").write_text(json.dumps({"servers": {"agentpilot-orchestrator": {}}}), encoding="utf-8")

    monkeypatch.setattr(module, "_latest_vscode_mcp_state", lambda: None)
    monkeypatch.setattr(module, "_process_has_mcp_server", lambda: False)

    result = module.get_mcp_status(tmp_path)

    assert result["mcp"] == "Standby"
    assert result["configured"] is True
    assert result["source"] == "process-scan"
    assert result["workspace_config"] == ".vscode/mcp.json"
    assert "first VS Code tool call" in result["note"]


def test_get_mcp_status_returns_inactive_when_not_configured(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_latest_vscode_mcp_state", lambda: None)
    monkeypatch.setattr(module, "_process_has_mcp_server", lambda: False)

    result = module.get_mcp_status(tmp_path)

    assert result["mcp"] == "Inactive"
    assert result["configured"] is False
    assert "note" not in result


def test_get_mcp_status_uses_environment_target_dir(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "mcp.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("AGENTPILOT_TARGET_DIR", str(tmp_path))
    monkeypatch.setattr(module, "_latest_vscode_mcp_state", lambda: None)
    monkeypatch.setattr(module, "_process_has_mcp_server", lambda: False)

    result = module.get_mcp_status()

    assert result["configured"] is True
    assert result["target_dir"] == str(tmp_path.resolve())