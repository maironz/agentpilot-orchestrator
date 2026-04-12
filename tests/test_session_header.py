from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_session_header_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / ".github" / "session_header.py"
    spec = importlib.util.spec_from_file_location("session_header_test_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_session_header_prints_details_only_for_need_update(monkeypatch, capsys) -> None:
    module = _load_session_header_module()

    def fake_run(cmd: list[str]):
        as_text = " ".join(cmd)
        if "router.py" in as_text and "--stats" in as_text:
            return 0, "Routing: 13scn/176kw|overlap:2.3%|[WARN]", ""
        if "router.py" in as_text and "--direct" in as_text:
            return 0, json.dumps({
                "agent": "orchestratore",
                "scenario": "_fallback",
                "priority": "low",
                "confidence": 0.123,
                "needs_clarification": True,
                "repo_exploration": {"recommended_scope": "clarify-then-repo-search"},
            }), ""
        if "update_report.py" in as_text:
            return 0, json.dumps({"update_label": "Need Update", "update_value": "[Need Update](.github/UPDATE_STATUS.md)"}), ""
        if "mcp_status.py" in as_text:
            return 0, json.dumps({"mcp": "Active"}), ""
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(sys, "argv", ["session_header.py", "--query", "check update"]) 

    rc = module.main()
    assert rc == 0

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 4
    assert "Update: [Need Update](.github/UPDATE_STATUS.md)" in lines[0]
    assert "Routing: 13scn/176kw|overlap:2.3%|[WARN]" in lines[0]
    assert lines[1].startswith("Riepilogo: confidence=0.123")
    assert "clarify=yes" in lines[1]
    assert lines[2] == "KPI details: [.github/kpi/KPI_METHODS.md](.github/kpi/KPI_METHODS.md)"
    assert lines[3] == "Update details: [.github/UPDATE_STATUS.md](.github/UPDATE_STATUS.md)"


def test_session_header_hides_details_when_update_is_ok(monkeypatch, capsys) -> None:
    module = _load_session_header_module()

    def fake_run(cmd: list[str]):
        as_text = " ".join(cmd)
        if "router.py" in as_text and "--stats" in as_text:
            return 0, "Routing: 13scn/176kw|overlap:2.3%|[WARN]", ""
        if "router.py" in as_text and "--direct" in as_text:
            return 0, json.dumps({
                "agent": "orchestratore",
                "scenario": "_fallback",
                "priority": "low",
                "confidence": 0.777,
                "needs_clarification": False,
                "repo_exploration": {"recommended_scope": "routed-files-only"},
            }), ""
        if "update_report.py" in as_text:
            return 0, json.dumps({"update_label": "ok", "update_value": "ok"}), ""
        if "mcp_status.py" in as_text:
            return 0, json.dumps({"mcp": "Active"}), ""
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(sys, "argv", ["session_header.py", "--query", "check update"]) 

    rc = module.main()
    assert rc == 0

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 3
    assert "| Update: ok |" in lines[0]
    assert lines[1].startswith("Riepilogo: confidence=0.777")
    assert "clarify=no" in lines[1]
    assert lines[2] == "KPI details: [.github/kpi/KPI_METHODS.md](.github/kpi/KPI_METHODS.md)"


def test_session_header_passes_auto_flag_to_update_report(monkeypatch, capsys) -> None:
    module = _load_session_header_module()
    update_cmds: list[list[str]] = []

    def fake_run(cmd: list[str]):
        as_text = " ".join(cmd)
        if "router.py" in as_text and "--stats" in as_text:
            return 0, "Routing: 13scn/176kw|overlap:2.3%|[WARN]", ""
        if "router.py" in as_text and "--direct" in as_text:
            return 0, json.dumps({
                "agent": "orchestratore",
                "scenario": "_fallback",
                "priority": "low",
            }), ""
        if "update_report.py" in as_text:
            update_cmds.append(cmd)
            return 0, json.dumps({"update_label": "ok", "update_value": "ok"}), ""
        if "mcp_status.py" in as_text:
            return 0, json.dumps({"mcp": "Active"}), ""
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(sys, "argv", ["session_header.py", "--query", "check update", "--auto-update"]) 

    rc = module.main()
    assert rc == 0
    capsys.readouterr()

    assert len(update_cmds) == 1
    assert "--auto" in update_cmds[0]
