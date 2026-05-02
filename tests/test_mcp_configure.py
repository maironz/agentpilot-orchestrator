from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    script_path = Path(__file__).parent.parent / ".github" / "mcp_configure.py"
    spec = importlib.util.spec_from_file_location("mcp_configure_for_tests", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enable_writes_mcp_json_to_explicit_target_dir(tmp_path: Path) -> None:
    module = _load_module()

    result = module.enable(tmp_path)

    mcp_json = tmp_path / ".vscode" / "mcp.json"
    payload = json.loads(mcp_json.read_text(encoding="utf-8"))

    assert result["status"] == "enabled"
    assert result["config_file"] == ".vscode/mcp.json"
    assert result["target_dir"] == str(tmp_path.resolve())
    assert module.SERVER_NAME in payload["servers"]


def test_enable_uses_environment_target_dir(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    monkeypatch.setenv("AGENTPILOT_TARGET_DIR", str(tmp_path))

    result = module.enable()

    assert (tmp_path / ".vscode" / "mcp.json").exists()
    assert result["target_dir"] == str(tmp_path.resolve())