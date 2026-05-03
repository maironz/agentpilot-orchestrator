"""Tests for X1 (audit_mode) and X2 (dry_run) in FSPolicy."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from rgen.fs_policy import FSPolicy


# ---------------------------------------------------------------------------
# audit_mode (X1)
# ---------------------------------------------------------------------------


def test_audit_mode_logs_write_file(tmp_path, caplog):
    policy = FSPolicy(project_root=tmp_path, audit_mode=True)
    target = tmp_path / ".agentpilot" / "state" / "run.json"
    with caplog.at_level(logging.INFO, logger="rgen.fs_policy"):
        policy.write_file(target, "{}")
    assert any("audit" in r.message and "write_file" in r.message for r in caplog.records)


def test_audit_mode_logs_write_bytes(tmp_path, caplog):
    policy = FSPolicy(project_root=tmp_path, audit_mode=True)
    target = tmp_path / ".agentpilot" / "cache" / "data.bin"
    with caplog.at_level(logging.INFO, logger="rgen.fs_policy"):
        policy.write_bytes_file(target, b"\x00\x01")
    assert any("audit" in r.message and "write_bytes_file" in r.message for r in caplog.records)


def test_audit_mode_logs_write_atomic(tmp_path, caplog):
    policy = FSPolicy(project_root=tmp_path, audit_mode=True)
    target = tmp_path / ".agentpilot" / "state" / "atomic.json"
    with caplog.at_level(logging.INFO, logger="rgen.fs_policy"):
        policy.write_atomic(target, "{}")
    assert any("audit" in r.message and "write_atomic" in r.message for r in caplog.records)


def test_audit_mode_logs_mkdir(tmp_path, caplog):
    policy = FSPolicy(project_root=tmp_path, audit_mode=True)
    d = tmp_path / ".agentpilot" / "custom"
    with caplog.at_level(logging.INFO, logger="rgen.fs_policy"):
        policy.mkdir(d)
    assert any("audit" in r.message and "mkdir" in r.message for r in caplog.records)


def test_audit_mode_logs_delete(tmp_path, caplog):
    policy = FSPolicy(project_root=tmp_path, audit_mode=True)
    f = tmp_path / ".agentpilot" / "state" / "x.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x", encoding="utf-8")
    with caplog.at_level(logging.INFO, logger="rgen.fs_policy"):
        policy.delete(f)
    assert any("audit" in r.message and "delete" in r.message for r in caplog.records)


def test_audit_mode_false_no_info_logs(tmp_path, caplog):
    policy = FSPolicy(project_root=tmp_path, audit_mode=False)
    target = tmp_path / ".agentpilot" / "state" / "run.json"
    with caplog.at_level(logging.INFO, logger="rgen.fs_policy"):
        policy.write_file(target, "{}")
    assert not any("audit" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# dry_run (X2)
# ---------------------------------------------------------------------------


def test_dry_run_write_file_does_not_create_file(tmp_path):
    policy = FSPolicy(project_root=tmp_path, dry_run=True)
    target = tmp_path / ".agentpilot" / "state" / "ghost.json"
    policy.write_file(target, "{}")
    assert not target.exists(), "dry_run must not create the file"


def test_dry_run_write_bytes_does_not_create_file(tmp_path):
    policy = FSPolicy(project_root=tmp_path, dry_run=True)
    target = tmp_path / ".agentpilot" / "cache" / "ghost.bin"
    policy.write_bytes_file(target, b"\x00")
    assert not target.exists()


def test_dry_run_write_atomic_does_not_create_file(tmp_path):
    policy = FSPolicy(project_root=tmp_path, dry_run=True)
    target = tmp_path / ".agentpilot" / "state" / "ghost_atomic.json"
    policy.write_atomic(target, "{}")
    assert not target.exists()


def test_dry_run_mkdir_does_not_create_dir(tmp_path):
    policy = FSPolicy(project_root=tmp_path, dry_run=True)
    d = tmp_path / ".agentpilot" / "custom_dry"
    policy.mkdir(d)
    assert not d.exists(), "dry_run must not create the directory"


def test_dry_run_delete_does_not_remove_file(tmp_path):
    policy = FSPolicy(project_root=tmp_path, dry_run=True)
    f = tmp_path / ".agentpilot" / "state" / "keep.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("keep", encoding="utf-8")
    policy.delete(f)
    assert f.exists(), "dry_run must not delete the file"


def test_dry_run_policy_check_still_runs(tmp_path):
    """Policy check (whitelist) must still run in dry_run mode."""
    import warnings
    policy = FSPolicy(project_root=tmp_path, dry_run=True, strict=False)
    bad = tmp_path / "outside" / "ghost.txt"
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        policy.write_file(bad, "x")
    assert any("whitelist" in str(x.message) for x in w)


def test_dry_run_strict_still_raises(tmp_path):
    """In dry_run + strict mode, policy violations still raise."""
    from rgen.fs_policy import PolicyViolation
    policy = FSPolicy(project_root=tmp_path, dry_run=True, strict=True)
    bad = tmp_path / "outside" / "ghost.txt"
    with pytest.raises(PolicyViolation):
        policy.write_file(bad, "x")


# ---------------------------------------------------------------------------
# audit_mode + dry_run combined
# ---------------------------------------------------------------------------


def test_audit_dry_run_logs_and_no_write(tmp_path, caplog):
    policy = FSPolicy(project_root=tmp_path, audit_mode=True, dry_run=True)
    target = tmp_path / ".agentpilot" / "state" / "combo.json"
    with caplog.at_level(logging.INFO, logger="rgen.fs_policy"):
        policy.write_file(target, "{}")
    assert any("audit" in r.message and "dry_run=True" in r.message for r in caplog.records)
    assert not target.exists()
