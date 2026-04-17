"""Tests for self-checker -- Step 7."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from rgen.self_checker import SelfChecker
from rgen.models import CheckReport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_github_dir(tmp_path: Path) -> Path:
    """A minimal but valid generated project directory."""
    gh = tmp_path / ".github"
    experts = gh / "esperti"
    experts.mkdir(parents=True)

    # routing-map.json with 3+ scenarios
    routing = {
        "_base_autoloaded": {"note": "ignore"},
        "s1": {"agent": "developer", "keywords": ["python"], "files": [".github/esperti/esperto_developer.md"], "context": "c", "priority": "high"},
        "s2": {"agent": "ops", "keywords": ["docker"], "files": [".github/esperti/esperto_ops.md"], "context": "c", "priority": "medium"},
        "s3": {"agent": "developer", "keywords": ["test"], "files": [".github/esperti/esperto_developer.md"], "context": "c", "priority": "low"},
    }
    (gh / "routing-map.json").write_text(json.dumps(routing), encoding="utf-8")
    (experts / "esperto_developer.md").write_text("# Developer")
    (experts / "esperto_ops.md").write_text("# Ops")
    (gh / "copilot-instructions.md").write_text("# Project\n## DISPATCHER\nrouter.py")
    (gh / "subagent-brief.md").write_text("# Brief")
    (gh / "AGENT_REGISTRY.md").write_text("# Registry\ndeveloper\nops")
    (gh / "router.py").write_text("# router stub - no real execution needed")
    (gh / "interventions.py").write_text("# interventions stub")
    (gh / "mcp_server.py").write_text("# mcp stub")
    (gh / "mcp_status.py").write_text("# mcp_status stub")
    (gh / "update_manager.py").write_text("# update_manager stub")
    return tmp_path


# ---------------------------------------------------------------------------
# required_files
# ---------------------------------------------------------------------------

def test_required_files_pass_when_all_present(valid_github_dir: Path) -> None:
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_required_files(report)
    assert not report.errors


def test_required_files_fails_when_file_missing(valid_github_dir: Path) -> None:
    (valid_github_dir / ".github" / "mcp_server.py").unlink()
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_required_files(report)
    assert any("mcp_server.py" in e for e in report.errors)


# ---------------------------------------------------------------------------
# routing_map
# ---------------------------------------------------------------------------

def test_routing_map_passes_valid_map(valid_github_dir: Path) -> None:
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_routing_map(report)
    assert not report.errors


def test_routing_map_fails_on_invalid_json(valid_github_dir: Path) -> None:
    (valid_github_dir / ".github" / "routing-map.json").write_text("not json")
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_routing_map(report)
    assert any("invalid JSON" in e for e in report.errors)


def test_routing_map_fails_when_too_few_scenarios(valid_github_dir: Path) -> None:
    (valid_github_dir / ".github" / "routing-map.json").write_text(
        json.dumps({"s1": {"agent": "dev", "keywords": [], "files": []}})
    )
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_routing_map(report)
    assert any("scenarios" in e for e in report.errors)


def test_routing_map_fails_on_missing_field(valid_github_dir: Path) -> None:
    (valid_github_dir / ".github" / "routing-map.json").write_text(
        json.dumps({
            "s1": {"agent": "dev", "files": []},  # no keywords
            "s2": {"agent": "dev", "keywords": [], "files": []},
            "s3": {"agent": "dev", "keywords": [], "files": []},
        })
    )
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_routing_map(report)
    assert any("keywords" in e for e in report.errors)


# ---------------------------------------------------------------------------
# expert_files
# ---------------------------------------------------------------------------

def test_expert_files_pass_when_present(valid_github_dir: Path) -> None:
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_expert_files(report)
    assert not report.errors


def test_expert_files_fails_when_agent_has_no_file(valid_github_dir: Path) -> None:
    (valid_github_dir / ".github" / "esperti" / "esperto_ops.md").unlink()
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_expert_files(report)
    assert any("esperto_ops.md" in e for e in report.errors)


# ---------------------------------------------------------------------------
# copilot_instructions
# ---------------------------------------------------------------------------

def test_copilot_instructions_passes_valid_file(valid_github_dir: Path) -> None:
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_copilot_instructions(report)
    assert not report.errors


def test_copilot_instructions_fails_without_dispatcher(valid_github_dir: Path) -> None:
    (valid_github_dir / ".github" / "copilot-instructions.md").write_text("# No dispatcher here")
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_copilot_instructions(report)
    assert any("DISPATCHER" in e for e in report.errors)


# ---------------------------------------------------------------------------
# template_vars
# ---------------------------------------------------------------------------

def test_template_vars_passes_when_no_placeholders(valid_github_dir: Path) -> None:
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_template_vars(report)
    assert not report.warnings


def test_template_vars_warns_on_leftover_placeholder(valid_github_dir: Path) -> None:
    (valid_github_dir / ".github" / "esperti" / "esperto_developer.md").write_text(
        "# Developer\nProject: {{PROJECT_NAME}}"
    )
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_template_vars(report)
    assert any("PROJECT_NAME" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# core_files
# ---------------------------------------------------------------------------

def test_core_files_pass_when_present(valid_github_dir: Path) -> None:
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_core_files(report)
    assert not report.errors


def test_core_files_fails_when_router_missing(valid_github_dir: Path) -> None:
    (valid_github_dir / ".github" / "router.py").unlink()
    checker = SelfChecker(valid_github_dir)
    report = CheckReport()
    checker._check_core_files(report)
    assert any("router.py" in e for e in report.errors)


# ---------------------------------------------------------------------------
# run_all (integration)
# ---------------------------------------------------------------------------

def test_run_all_passes_on_valid_project(valid_github_dir: Path) -> None:
    # Copy real router.py so subprocess check can work
    real_router = Path(__file__).parent.parent / ".github" / "router.py"
    dest = valid_github_dir / ".github" / "router.py"
    if real_router.exists():
        shutil.copy2(real_router, dest)
        # Copy routing-map so router can load it
        shutil.copy2(
            Path(__file__).parent.parent / ".github" / "routing-map.json",
            valid_github_dir / ".github" / "routing-map.json",
        )
        # Update expert files to match the copied routing-map agents
        shutil.copytree(
            Path(__file__).parent.parent / ".github" / "esperti",
            valid_github_dir / ".github" / "esperti",
            dirs_exist_ok=True,
        )

    checker = SelfChecker(valid_github_dir)
    report = checker.run_all()
    assert len(report.passed) >= 5, f"Only {len(report.passed)} passed. Errors: {report.errors}"


def test_run_all_captures_all_errors(valid_github_dir: Path) -> None:
    # Remove several files to cause multiple failures
    (valid_github_dir / ".github" / "routing-map.json").unlink()
    (valid_github_dir / ".github" / "mcp_server.py").unlink()
    checker = SelfChecker(valid_github_dir)
    report = checker.run_all()
    # Expect multiple errors
    assert not report.overall
    assert len(report.errors) >= 2
