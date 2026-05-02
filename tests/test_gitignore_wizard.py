"""Tests for rgen/gitignore_wizard.py."""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from rgen.gitignore_wizard import (
    _COMMENT,
    _ENTRY_ARTIFACTS_KEEP,
    _ENTRY_MAIN,
    apply_entries,
    is_agentpilot_ignored,
    missing_entries,
    run_wizard,
)


# ---------------------------------------------------------------------------
# is_agentpilot_ignored
# ---------------------------------------------------------------------------


def test_is_agentpilot_ignored_no_gitignore(tmp_path):
    assert is_agentpilot_ignored(tmp_path) is False


def test_is_agentpilot_ignored_entry_absent(tmp_path):
    (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    assert is_agentpilot_ignored(tmp_path) is False


def test_is_agentpilot_ignored_entry_present(tmp_path):
    (tmp_path / ".gitignore").write_text(".agentpilot/\n", encoding="utf-8")
    assert is_agentpilot_ignored(tmp_path) is True


# ---------------------------------------------------------------------------
# missing_entries
# ---------------------------------------------------------------------------


def test_missing_entries_no_gitignore(tmp_path):
    result = missing_entries(project_root=tmp_path)
    assert _ENTRY_MAIN in result


def test_missing_entries_already_present(tmp_path):
    (tmp_path / ".gitignore").write_text(".agentpilot/\n", encoding="utf-8")
    assert missing_entries(project_root=tmp_path) == []


def test_missing_entries_track_artifacts_missing(tmp_path):
    (tmp_path / ".gitignore").write_text(".agentpilot/\n", encoding="utf-8")
    result = missing_entries(project_root=tmp_path, track_artifacts=True)
    assert _ENTRY_ARTIFACTS_KEEP in result


def test_missing_entries_track_artifacts_already_present(tmp_path):
    gi_content = ".agentpilot/\n!.agentpilot/artifacts/\n"
    (tmp_path / ".gitignore").write_text(gi_content, encoding="utf-8")
    assert missing_entries(project_root=tmp_path, track_artifacts=True) == []


def test_missing_entries_partial(tmp_path):
    """Only _ENTRY_MAIN absent — _ENTRY_ARTIFACTS_KEEP already present."""
    (tmp_path / ".gitignore").write_text("!.agentpilot/artifacts/\n", encoding="utf-8")
    result = missing_entries(project_root=tmp_path, track_artifacts=True)
    assert _ENTRY_MAIN in result
    assert _ENTRY_ARTIFACTS_KEEP not in result


# ---------------------------------------------------------------------------
# apply_entries
# ---------------------------------------------------------------------------


def test_apply_entries_creates_gitignore(tmp_path):
    apply_entries([_ENTRY_MAIN], project_root=tmp_path)
    gi = tmp_path / ".gitignore"
    assert gi.is_file()
    assert _ENTRY_MAIN in gi.read_text(encoding="utf-8")


def test_apply_entries_appends_to_existing(tmp_path):
    existing = "node_modules/\n"
    gi = tmp_path / ".gitignore"
    gi.write_text(existing, encoding="utf-8")
    apply_entries([_ENTRY_MAIN], project_root=tmp_path)
    content = gi.read_text(encoding="utf-8")
    assert "node_modules/" in content
    assert _ENTRY_MAIN in content


def test_apply_entries_contains_comment(tmp_path):
    apply_entries([_ENTRY_MAIN], project_root=tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert _COMMENT in content


def test_apply_entries_idempotent(tmp_path):
    apply_entries([_ENTRY_MAIN], project_root=tmp_path)
    apply_entries([_ENTRY_MAIN], project_root=tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    # Entry appears exactly once
    assert content.count(_ENTRY_MAIN) == 1


def test_apply_entries_empty_list_is_noop(tmp_path):
    apply_entries([], project_root=tmp_path)
    assert not (tmp_path / ".gitignore").exists()


def test_apply_entries_no_trailing_newline_before(tmp_path):
    """File without trailing newline: separator is added."""
    gi = tmp_path / ".gitignore"
    gi.write_text("node_modules/", encoding="utf-8")  # no trailing newline
    apply_entries([_ENTRY_MAIN], project_root=tmp_path)
    content = gi.read_text(encoding="utf-8")
    # node_modules/ and .agentpilot/ must be on separate lines
    assert "node_modules/" in content
    assert _ENTRY_MAIN in content
    lines = content.splitlines()
    assert lines.index("node_modules/") < lines.index(_ENTRY_MAIN)


# ---------------------------------------------------------------------------
# run_wizard
# ---------------------------------------------------------------------------


def test_run_wizard_no_action_needed(tmp_path):
    (tmp_path / ".gitignore").write_text(".agentpilot/\n", encoding="utf-8")
    result = run_wizard(project_root=tmp_path, interactive=False)
    assert result is True


def test_run_wizard_non_interactive_applies(tmp_path):
    result = run_wizard(project_root=tmp_path, interactive=False)
    assert result is True
    assert _ENTRY_MAIN in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_run_wizard_interactive_yes(tmp_path):
    with patch("builtins.input", return_value="y"):
        result = run_wizard(project_root=tmp_path, interactive=True)
    assert result is True
    assert is_agentpilot_ignored(tmp_path)


def test_run_wizard_interactive_no_warns(tmp_path):
    with patch("builtins.input", return_value="n"):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = run_wizard(project_root=tmp_path, interactive=True)

    assert result is False
    assert any("not excluded from git" in str(x.message) for x in w)
    assert not is_agentpilot_ignored(tmp_path)


def test_run_wizard_eof_treated_as_no(tmp_path):
    """EOFError (non-interactive shell) → wizard declines gracefully."""
    with patch("builtins.input", side_effect=EOFError):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = run_wizard(project_root=tmp_path, interactive=True)

    assert result is False
    assert any("not excluded from git" in str(x.message) for x in w)


def test_run_wizard_interactive_enter_applies(tmp_path):
    """Empty enter (default) is treated as yes."""
    with patch("builtins.input", return_value=""):
        result = run_wizard(project_root=tmp_path, interactive=True)
    assert result is True
    assert is_agentpilot_ignored(tmp_path)
