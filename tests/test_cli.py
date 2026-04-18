"""Integration tests for CLI -- Step 8."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from rgen.cli import main, _build_parser, _ask_output_language


# ---------------------------------------------------------------------------
# --list-patterns
# ---------------------------------------------------------------------------

def test_list_patterns_finds_psm_stack(capsys: pytest.CaptureFixture) -> None:
    ret = main(["--list-patterns"])
    out = capsys.readouterr().out
    assert ret == 0
    assert "psm_stack" in out


def test_list_patterns_empty_kb(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ret = main(["--list-patterns", "--kb", str(tmp_path / "empty_kb")])
    out = capsys.readouterr().out
    assert ret == 0
    assert "Nessun pattern" in out


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------

def test_check_passes_on_valid_project(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    gh = tmp_path / ".github"
    experts = gh / "esperti"
    experts.mkdir(parents=True)
    routing = {
        "s1": {"agent": "dev", "keywords": ["k"], "files": [".github/esperti/esperto_dev.md"], "context": "", "priority": "high"},
        "s2": {"agent": "dev", "keywords": ["k2"], "files": [], "context": "", "priority": "medium"},
        "s3": {"agent": "dev", "keywords": ["k3"], "files": [], "context": "", "priority": "low"},
    }
    (gh / "routing-map.json").write_text(json.dumps(routing))
    (experts / "esperto_dev.md").write_text("# Dev")
    (gh / "copilot-instructions.md").write_text("## DISPATCHER\nrouter.py")
    (gh / "subagent-brief.md").write_text("# Brief")
    (gh / "AGENT_REGISTRY.md").write_text("# Registry\ndev")
    (gh / "router.py").write_text("# stub")
    (gh / "interventions.py").write_text("# stub")
    (gh / "mcp_server.py").write_text("# stub")
    (gh / "mcp_status.py").write_text("# stub")
    (gh / "update_manager.py").write_text("# stub")

    ret = main(["--check", "--target", str(tmp_path)])
    assert ret == 0


def test_check_fails_on_missing_target(capsys: pytest.CaptureFixture) -> None:
    ret = main(["--check", "--target", "/nonexistent/path"])
    assert ret == 2


# ---------------------------------------------------------------------------
# --dry-run
# ---------------------------------------------------------------------------

def test_dry_run_does_not_write_files(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ret = main([
        "--dry-run",
        "--pattern", "psm_stack",
        "--name", "test-project",
        "--target", str(tmp_path / "output"),
    ])
    assert ret == 0
    # No files should have been written
    assert not (tmp_path / "output" / ".github").exists()

    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert ".github/routing-map.json" in out


# ---------------------------------------------------------------------------
# --restore
# ---------------------------------------------------------------------------

def test_restore_lists_backups_when_no_timestamp(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ret = main(["--restore", "--target", str(tmp_path)])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Nessun backup" in out


def test_restore_fails_on_missing_timestamp(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ret = main(["--restore", "--target", str(tmp_path), "--timestamp", "99990101_999999"])
    assert ret == 2


def test_history_json_with_diffs(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    project = tmp_path / "acme"
    ret = main([
        "--direct",
        "--pattern", "psm_stack",
        "--name", "acme",
        "--target", str(project),
    ])
    assert ret == 0
    capsys.readouterr()

    ret = main(["--history", "--target", str(project), "--history-format", "json", "--show-diffs"])
    assert ret == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert isinstance(payload, list)
    assert payload
    assert "diff" in payload[0]


def test_rollback_requires_to_argument(tmp_path: Path) -> None:
    ret = main(["--rollback", "--target", str(tmp_path)])
    assert ret == 2


def test_rollback_skips_manual_changes_by_default(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    project = tmp_path / "app"
    gh = project / ".github"
    gh.mkdir(parents=True)
    (gh / "router.py").write_text("# old content")

    ret = main(["--update", "--target", str(project)])
    assert ret == 0
    capsys.readouterr()

    (gh / "router.py").write_text("# manual edit")
    sessions = json.loads((gh / ".rgen-backups" / "index.json").read_text(encoding="utf-8"))
    generation_id = sessions[0]["generation_id"]

    ret = main(["--rollback", "--target", str(project), "--to", generation_id])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Saltati:" in out
    assert (gh / "router.py").read_text() == "# manual edit"


# ---------------------------------------------------------------------------
# --direct (non-interactive generation)
# ---------------------------------------------------------------------------

def test_direct_generates_github_dir(tmp_path: Path) -> None:
    ret = main([
        "--direct",
        "--pattern", "psm_stack",
        "--name", "acme",
        "--target", str(tmp_path / "acme"),
    ])
    assert ret == 0
    assert (tmp_path / "acme" / ".github" / "routing-map.json").exists()
    assert (tmp_path / "acme" / ".github" / "router.py").exists()
    assert (tmp_path / "acme" / ".github" / "copilot-instructions.md").exists()
    assert (tmp_path / "acme" / ".github" / "standard" / "README.md").exists()


def test_direct_routing_map_is_valid_json(tmp_path: Path) -> None:
    ret = main([
        "--direct",
        "--pattern", "psm_stack",
        "--name", "acme",
        "--target", str(tmp_path / "acme"),
    ])
    assert ret == 0
    routing_map = json.loads(
        (tmp_path / "acme" / ".github" / "routing-map.json").read_text(encoding="utf-8")
    )
    scenarios = {k: v for k, v in routing_map.items() if not k.startswith("_")}
    assert len(scenarios) >= 5


def test_direct_scratch_generates_from_domains(tmp_path: Path) -> None:
    ret = main([
        "--direct",
        "--name", "scratch-app",
        "--target", str(tmp_path / "scratch"),
        "--tech", "python,fastapi",
        "--domains", "api,auth",
    ])
    assert ret == 0
    routing_map = json.loads(
        (tmp_path / "scratch" / ".github" / "routing-map.json").read_text(encoding="utf-8")
    )
    assert "api" in routing_map or "auth" in routing_map
    assert (tmp_path / "scratch" / ".github" / "standard" / "python-style-guide.md").exists()


# ---------------------------------------------------------------------------
# Parser structure
# ---------------------------------------------------------------------------

def test_parser_modes_are_mutually_exclusive() -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--direct", "--dry-run"])


# ---------------------------------------------------------------------------
# --update
# ---------------------------------------------------------------------------

def test_update_copies_core_files_to_existing_project(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    (tmp_path / ".github").mkdir()
    ret = main(["--update", "--target", str(tmp_path)])
    assert ret == 0
    out = capsys.readouterr().out
    assert "aggiornati" in out
    assert (tmp_path / ".github" / "router.py").exists()


def test_update_fails_when_no_github_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    ret = main(["--update", "--target", str(tmp_path)])
    assert ret == 2
    err = capsys.readouterr().err
    assert ".github" in err


def test_update_creates_backup(tmp_path: Path) -> None:
    gh = tmp_path / ".github"
    gh.mkdir()
    (gh / "router.py").write_text("# old content")
    ret = main(["--update", "--target", str(tmp_path)])
    assert ret == 0
    backup_root = gh / ".rgen-backups"
    assert backup_root.exists()
    backup_slots = list(backup_root.iterdir())
    assert len(backup_slots) >= 1


def test_update_flat_copies_to_root(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ret = main(["--update", "--flat", "--target", str(tmp_path)])
    assert ret == 0
    out = capsys.readouterr().out
    assert "aggiornati" in out
    assert (tmp_path / "router.py").exists()


def test_update_flat_creates_backup_in_root(tmp_path: Path) -> None:
    (tmp_path / "router.py").write_text("# old")
    ret = main(["--update", "--flat", "--target", str(tmp_path)])
    assert ret == 0
    assert (tmp_path / ".rgen-backups").exists()


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------

def test_version_flag_exits_zero(capsys: pytest.CaptureFixture) -> None:
    from rgen import __version__

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_version_flag_includes_prog_name(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    out = capsys.readouterr().out
    assert "rgen" in out


def test_ask_output_language_accepts_default() -> None:
    with patch("builtins.input", return_value=""):
        assert _ask_output_language(default="en") == "en"


def test_ask_output_language_accepts_it_after_invalid() -> None:
    answers = iter(["zz", "it"])
    with patch("builtins.input", side_effect=answers):
        assert _ask_output_language(default="en") == "it"


# ---------------------------------------------------------------------------
# --kb custom path honored in _run_generation (bug fix)
# ---------------------------------------------------------------------------

def test_direct_respects_custom_kb_path(tmp_path: Path) -> None:
    """--kb override must be passed through to the Adapter, not silently ignored."""
    kb = tmp_path / "custom_kb"
    pattern_dir = kb / "mypattern"
    (pattern_dir / "esperti").mkdir(parents=True)
    (pattern_dir / "metadata.json").write_text(json.dumps({
        "id": "mypattern",
        "name": "My Custom Pattern",
        "tech_stack": ["python"],
        "agents": ["dev"],
        "agent_descriptions": {"dev": "Developer"},
    }), encoding="utf-8")
    routing = {
        "custom_scenario": {
            "agent": "dev",
            "keywords": ["custom", "unique_keyword_xyz"],
            "files": [".github/esperti/esperto_dev.md"],
            "context": "Custom context",
            "priority": "high",
        },
        "troubleshooting": {
            "agent": "dev",
            "keywords": ["error", "debug", "fix"],
            "files": [".github/esperti/esperto_dev.md"],
            "context": "Troubleshooting",
            "priority": "high",
        },
        "docs": {
            "agent": "dev",
            "keywords": ["docs", "readme"],
            "files": [".github/esperti/esperto_dev.md"],
            "context": "Documentation",
            "priority": "low",
        },
    }
    (pattern_dir / "routing-map.json").write_text(json.dumps(routing), encoding="utf-8")
    (pattern_dir / "esperti" / "esperto_dev.md").write_text("# Dev Expert", encoding="utf-8")

    out_dir = tmp_path / "output"
    ret = main([
        "--direct",
        "--pattern", "mypattern",
        "--name", "custom-project",
        "--target", str(out_dir),
        "--kb", str(kb),
    ])
    assert ret == 0
    rm = json.loads((out_dir / ".github" / "routing-map.json").read_text(encoding="utf-8"))
    scenarios = {k: v for k, v in rm.items() if not k.startswith("_")}
    assert "custom_scenario" in scenarios
    assert "unique_keyword_xyz" in scenarios["custom_scenario"]["keywords"]


# ---------------------------------------------------------------------------
# New patterns: python_api and node_ts
# ---------------------------------------------------------------------------

def test_list_patterns_finds_python_api(capsys: pytest.CaptureFixture) -> None:
    ret = main(["--list-patterns"])
    out = capsys.readouterr().out
    assert ret == 0
    assert "python_api" in out


def test_list_patterns_finds_node_ts(capsys: pytest.CaptureFixture) -> None:
    ret = main(["--list-patterns"])
    out = capsys.readouterr().out
    assert ret == 0
    assert "node_ts" in out


def test_direct_python_api_generates_backend_and_devops_agents(tmp_path: Path) -> None:
    ret = main([
        "--direct", "--pattern", "python_api",
        "--name", "my-api", "--target", str(tmp_path / "api"),
    ])
    assert ret == 0
    rm = json.loads((tmp_path / "api" / ".github" / "routing-map.json").read_text(encoding="utf-8"))
    agents = {v["agent"] for k, v in rm.items() if not k.startswith("_")}
    assert "backend" in agents
    assert "devops" in agents
    assert (tmp_path / "api" / ".github" / "esperti" / "esperto_backend.md").exists()
    assert (tmp_path / "api" / ".github" / "esperti" / "esperto_devops.md").exists()


def test_direct_python_api_routing_map_has_key_scenarios(tmp_path: Path) -> None:
    ret = main([
        "--direct", "--pattern", "python_api",
        "--name", "my-api", "--target", str(tmp_path / "api"),
    ])
    assert ret == 0
    rm = json.loads((tmp_path / "api" / ".github" / "routing-map.json").read_text(encoding="utf-8"))
    for scenario in ("api_endpoints", "database", "auth", "testing", "docker_infra", "security"):
        assert scenario in rm, f"Missing scenario: {scenario}"


def test_direct_node_ts_generates_frontend_agent(tmp_path: Path) -> None:
    ret = main([
        "--direct", "--pattern", "node_ts",
        "--name", "my-app", "--target", str(tmp_path / "app"),
    ])
    assert ret == 0
    rm = json.loads((tmp_path / "app" / ".github" / "routing-map.json").read_text(encoding="utf-8"))
    agents = {v["agent"] for k, v in rm.items() if not k.startswith("_")}
    assert "frontend" in agents
    assert (tmp_path / "app" / ".github" / "esperti" / "esperto_frontend.md").exists()


def test_direct_node_ts_routing_map_has_key_scenarios(tmp_path: Path) -> None:
    ret = main([
        "--direct", "--pattern", "node_ts",
        "--name", "my-app", "--target", str(tmp_path / "app"),
    ])
    assert ret == 0
    rm = json.loads((tmp_path / "app" / ".github" / "routing-map.json").read_text(encoding="utf-8"))
    for scenario in ("typescript_code", "api_routes", "frontend_components", "database", "security"):
        assert scenario in rm, f"Missing scenario: {scenario}"


def test_dry_run_python_api_lists_expected_files(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ret = main([
        "--dry-run", "--pattern", "python_api",
        "--name", "my-api", "--target", str(tmp_path / "api"),
    ])
    assert ret == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "esperto_backend.md" in out
    assert "esperto_devops.md" in out
    assert not (tmp_path / "api" / ".github").exists()


def test_search_patterns_returns_results(capsys: pytest.CaptureFixture) -> None:
    ret = main(["--search-patterns", "python"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "python_api" in out


def test_download_installs_local_pattern_pack(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    kb = pack / "knowledge_base" / "demo_pack"
    kb.mkdir(parents=True)

    manifest = {
        "id": "demo_pack",
        "name": "Demo Pack",
        "version": "1.0.0",
    }
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kb / "metadata.json").write_text(
        json.dumps({"id": "demo_pack", "name": "Demo Pack", "tech_stack": ["python"]}),
        encoding="utf-8",
    )
    (kb / "routing-map.json").write_text(json.dumps({"a": {"agent": "dev", "keywords": [], "files": [], "context": "", "priority": "low"}}), encoding="utf-8")

    install_dir = tmp_path / "installed"
    ret = main(["--download", str(pack), "--install-dir", str(install_dir)])
    assert ret == 0
    assert (install_dir / "demo_pack" / "metadata.json").exists()


def test_download_installs_remote_zip_pack(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    kb = pack / "knowledge_base" / "zip_pack"
    kb.mkdir(parents=True)

    manifest = {
        "id": "zip_pack",
        "name": "Zip Pack",
        "version": "1.0.0",
    }
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kb / "metadata.json").write_text(
        json.dumps({"id": "zip_pack", "name": "Zip Pack", "tech_stack": ["python"]}),
        encoding="utf-8",
    )

    archive = tmp_path / "zip_pack.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in pack.rglob("*"):
            if file_path.is_file():
                rel = file_path.relative_to(pack).as_posix()
                zf.write(file_path, f"zip_pack/{rel}")

    install_dir = tmp_path / "installed"
    ret = main(["--download", archive.as_uri(), "--install-dir", str(install_dir)])
    assert ret == 0
    assert (install_dir / "zip_pack" / "metadata.json").exists()
