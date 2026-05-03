"""Tests for A4 — .github/ write hardening (persistent audit log)."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from rgen.fs_policy import FSPolicy, PolicyViolation

_AUDIT_LOG_REL = Path(".agentpilot") / "logs" / "github_writes.log"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_audit(tmp_path: Path) -> str:
    log = tmp_path / _AUDIT_LOG_REL
    return log.read_text(encoding="utf-8") if log.is_file() else ""


def _github_file(tmp_path: Path, name: str = "test.txt") -> Path:
    gh = tmp_path / ".github"
    gh.mkdir(exist_ok=True)
    return gh / name


# ---------------------------------------------------------------------------
# Audit log is always written
# ---------------------------------------------------------------------------


def test_audit_log_created_on_github_write_allowed(tmp_path):
    """Audit log is written even when allow_github_write=True."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=True)
    target = _github_file(tmp_path)
    policy.write_file(target, "data")

    log_content = _read_audit(tmp_path)
    assert log_content, "audit log must not be empty"
    assert str(target) in log_content or ".github" in log_content


def test_audit_log_created_on_github_write_denied(tmp_path):
    """Audit log is written even when the write is denied (allow=False)."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=False, strict=False)
    target = _github_file(tmp_path)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        policy.write_file(target, "data")

    log_content = _read_audit(tmp_path)
    assert log_content, "audit log must not be empty even on denied write"


def test_audit_log_appends_multiple_entries(tmp_path):
    """Each github write appends a new line."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=True)
    for i in range(3):
        target = _github_file(tmp_path, f"file{i}.txt")
        policy.write_file(target, f"content {i}")

    log_content = _read_audit(tmp_path)
    lines = [l for l in log_content.splitlines() if l.strip()]
    assert len(lines) == 3


def test_audit_log_contains_timestamp(tmp_path):
    """Each audit entry contains an ISO-8601 timestamp."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=True)
    policy.write_file(_github_file(tmp_path), "x")

    log_content = _read_audit(tmp_path)
    # ISO timestamp format: 2026-05-03T...
    assert "T" in log_content and "+" in log_content or "Z" in log_content or "UTC" in log_content or log_content.count("-") >= 2


def test_audit_log_contains_allow_flag(tmp_path):
    """Audit entry records the value of allow_github_write."""
    policy_yes = FSPolicy(project_root=tmp_path, allow_github_write=True)
    policy_yes.write_file(_github_file(tmp_path, "a.txt"), "x")

    policy_no = FSPolicy(project_root=tmp_path, allow_github_write=False, strict=False)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        policy_no.write_file(_github_file(tmp_path, "b.txt"), "x")

    log_content = _read_audit(tmp_path)
    assert "allow=True" in log_content
    assert "allow=False" in log_content


def test_audit_log_contains_caller(tmp_path):
    """Audit entry records the caller module/function."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=True)
    policy.write_file(_github_file(tmp_path), "x")

    log_content = _read_audit(tmp_path)
    assert "caller=" in log_content


def test_audit_log_contains_path(tmp_path):
    """Audit entry records the target path."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=True)
    target = _github_file(tmp_path, "canary.txt")
    policy.write_file(target, "x")

    log_content = _read_audit(tmp_path)
    assert "canary.txt" in log_content


def test_audit_log_path_configurable(tmp_path):
    """_github_audit_log is set to .agentpilot/logs/github_writes.log."""
    policy = FSPolicy(project_root=tmp_path)
    expected = (tmp_path / _AUDIT_LOG_REL).resolve()
    assert policy._github_audit_log.resolve() == expected


# ---------------------------------------------------------------------------
# Non-github writes do NOT produce audit entries
# ---------------------------------------------------------------------------


def test_audit_log_not_written_for_agentpilot_write(tmp_path):
    """Writes inside .agentpilot/ must not add github audit entries."""
    policy = FSPolicy(project_root=tmp_path)
    target = tmp_path / ".agentpilot" / "state" / "run.json"
    policy.write_file(target, "{}")

    # Audit log must not exist (or be empty) for non-github writes
    log = tmp_path / _AUDIT_LOG_REL
    if log.is_file():
        content = log.read_text(encoding="utf-8")
        assert "run.json" not in content


# ---------------------------------------------------------------------------
# allow_github_write enforcement
# ---------------------------------------------------------------------------


def test_github_write_blocked_when_not_allowed_warns(tmp_path):
    """With allow_github_write=False (non-strict), a warning is emitted."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=False, strict=False)
    target = _github_file(tmp_path)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        policy.write_file(target, "x")
    assert any("whitelist" in str(x.message) for x in w)


def test_github_write_blocked_strict_raises(tmp_path):
    """With allow_github_write=False and strict=True, PolicyViolation is raised."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=False, strict=True)
    target = _github_file(tmp_path)
    with pytest.raises(PolicyViolation):
        policy.write_file(target, "x")


def test_github_write_allowed_succeeds(tmp_path):
    """With allow_github_write=True, the file is actually written."""
    policy = FSPolicy(project_root=tmp_path, allow_github_write=True)
    target = _github_file(tmp_path, "ok.txt")
    policy.write_file(target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"
