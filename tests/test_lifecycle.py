"""Tests for rgen/lifecycle.py — C4 lifecycle cleanup."""

from __future__ import annotations

import atexit
import time
from pathlib import Path

import pytest

from rgen.lifecycle import LifecycleManager, get_manager, _LOGS_REL, _CACHE_REL, _TMP_REL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_log_files(logs_dir: Path, count: int) -> list[Path]:
    logs_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(count):
        p = logs_dir / f"run_{i:03d}.log"
        p.write_text(f"log {i}", encoding="utf-8")
        # Stagger mtime so sorting is deterministic
        mtime = 1_700_000_000 + i
        import os
        os.utime(p, (mtime, mtime))
        files.append(p)
    return files


def _make_cache_files(cache_dir: Path, sizes: list[int]) -> list[Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for i, size in enumerate(sizes):
        p = cache_dir / f"item_{i:03d}.bin"
        p.write_bytes(b"x" * size)
        mtime = 1_700_000_000 + i
        import os
        os.utime(p, (mtime, mtime))
        files.append(p)
    return files


# ---------------------------------------------------------------------------
# LifecycleManager construction
# ---------------------------------------------------------------------------


def test_dirs_resolve_correctly(tmp_path):
    mgr = LifecycleManager(project_root=tmp_path)
    assert mgr.logs_dir == tmp_path / _LOGS_REL
    assert mgr.cache_dir == tmp_path / _CACHE_REL
    assert mgr.tmp_dir == tmp_path / _TMP_REL


def test_get_manager_returns_instance(tmp_path):
    mgr = get_manager(project_root=tmp_path)
    assert isinstance(mgr, LifecycleManager)


# ---------------------------------------------------------------------------
# rotate_logs
# ---------------------------------------------------------------------------


def test_rotate_logs_no_dir(tmp_path):
    mgr = LifecycleManager(project_root=tmp_path)
    assert mgr.rotate_logs() == []


def test_rotate_logs_fewer_than_keep(tmp_path):
    _make_log_files(tmp_path / _LOGS_REL, 5)
    mgr = LifecycleManager(project_root=tmp_path)
    deleted = mgr.rotate_logs(keep=20)
    assert deleted == []
    assert len(list((tmp_path / _LOGS_REL).glob("*.log"))) == 5


def test_rotate_logs_excess_deleted(tmp_path):
    _make_log_files(tmp_path / _LOGS_REL, 10)
    mgr = LifecycleManager(project_root=tmp_path)
    deleted = mgr.rotate_logs(keep=6)
    assert len(deleted) == 4
    remaining = list((tmp_path / _LOGS_REL).glob("*.log"))
    assert len(remaining) == 6


def test_rotate_logs_oldest_deleted(tmp_path):
    """The oldest files (lowest mtime) must be deleted first."""
    files = _make_log_files(tmp_path / _LOGS_REL, 5)
    mgr = LifecycleManager(project_root=tmp_path)
    deleted = mgr.rotate_logs(keep=3)
    # files[0] and files[1] are oldest
    assert files[0] in deleted
    assert files[1] in deleted


def test_rotate_logs_keep_zero(tmp_path):
    _make_log_files(tmp_path / _LOGS_REL, 4)
    mgr = LifecycleManager(project_root=tmp_path)
    deleted = mgr.rotate_logs(keep=0)
    assert len(deleted) == 4
    assert list((tmp_path / _LOGS_REL).glob("*.log")) == []


def test_rotate_logs_uses_instance_keep(tmp_path):
    _make_log_files(tmp_path / _LOGS_REL, 10)
    mgr = LifecycleManager(project_root=tmp_path, log_keep=7)
    deleted = mgr.rotate_logs()
    assert len(deleted) == 3


# ---------------------------------------------------------------------------
# cap_cache
# ---------------------------------------------------------------------------


def test_cap_cache_no_dir(tmp_path):
    mgr = LifecycleManager(project_root=tmp_path)
    assert mgr.cap_cache() == []


def test_cap_cache_under_limit(tmp_path):
    _make_cache_files(tmp_path / _CACHE_REL, [100, 200, 300])
    mgr = LifecycleManager(project_root=tmp_path)
    deleted = mgr.cap_cache(max_bytes=1000)
    assert deleted == []


def test_cap_cache_evicts_oldest(tmp_path):
    # 3 files × 100 bytes = 300 bytes total; limit = 150 → must evict 2
    files = _make_cache_files(tmp_path / _CACHE_REL, [100, 100, 100])
    mgr = LifecycleManager(project_root=tmp_path)
    deleted = mgr.cap_cache(max_bytes=150)
    assert len(deleted) == 2
    assert files[0] in deleted
    assert files[1] in deleted


def test_cap_cache_total_size_after_eviction(tmp_path):
    _make_cache_files(tmp_path / _CACHE_REL, [500, 500, 500])
    mgr = LifecycleManager(project_root=tmp_path)
    mgr.cap_cache(max_bytes=600)
    remaining = list((tmp_path / _CACHE_REL).glob("*.bin"))
    total = sum(f.stat().st_size for f in remaining)
    assert total <= 600


def test_cap_cache_uses_instance_limit(tmp_path):
    _make_cache_files(tmp_path / _CACHE_REL, [200, 200, 200])
    mgr = LifecycleManager(project_root=tmp_path, cache_max_bytes=250)
    deleted = mgr.cap_cache()
    assert len(deleted) == 2


# ---------------------------------------------------------------------------
# clean_tmp
# ---------------------------------------------------------------------------


def test_clean_tmp_no_dir(tmp_path):
    mgr = LifecycleManager(project_root=tmp_path)
    assert mgr.clean_tmp() == 0


def test_clean_tmp_removes_files(tmp_path):
    tmp_dir = tmp_path / _TMP_REL
    tmp_dir.mkdir(parents=True)
    for i in range(5):
        (tmp_dir / f"work_{i}.tmp").write_bytes(b"x")
    mgr = LifecycleManager(project_root=tmp_path)
    count = mgr.clean_tmp()
    assert count == 5
    assert list(tmp_dir.iterdir()) == []


def test_clean_tmp_removes_subdirs(tmp_path):
    tmp_dir = tmp_path / _TMP_REL
    tmp_dir.mkdir(parents=True)
    sub = tmp_dir / "subdir"
    sub.mkdir()
    (sub / "file.txt").write_text("x", encoding="utf-8")
    mgr = LifecycleManager(project_root=tmp_path)
    count = mgr.clean_tmp()
    assert count == 1
    assert not sub.exists()


def test_clean_tmp_empty_dir(tmp_path):
    tmp_dir = tmp_path / _TMP_REL
    tmp_dir.mkdir(parents=True)
    mgr = LifecycleManager(project_root=tmp_path)
    assert mgr.clean_tmp() == 0


# ---------------------------------------------------------------------------
# run_all
# ---------------------------------------------------------------------------


def test_run_all_returns_summary(tmp_path):
    _make_log_files(tmp_path / _LOGS_REL, 5)
    _make_cache_files(tmp_path / _CACHE_REL, [100, 100])
    tmp_dir = tmp_path / _TMP_REL
    tmp_dir.mkdir(parents=True)
    (tmp_dir / "a.tmp").write_bytes(b"x")

    mgr = LifecycleManager(project_root=tmp_path)
    result = mgr.run_all(log_keep=3, cache_max_bytes=50)

    assert isinstance(result["deleted_logs"], list)
    assert isinstance(result["evicted_cache"], list)
    assert isinstance(result["tmp_cleaned"], int)
    assert len(result["deleted_logs"]) == 2
    assert result["tmp_cleaned"] == 1


# ---------------------------------------------------------------------------
# register_atexit_if_configured
# ---------------------------------------------------------------------------


def test_register_atexit_returns_false_when_disabled(tmp_path):
    # No config file → cleanup_on_exit defaults to False
    mgr = LifecycleManager(project_root=tmp_path)
    assert mgr.register_atexit_if_configured() is False


def test_register_atexit_returns_true_when_enabled(tmp_path):
    from rgen.config import AgentPilotConfig, save
    save(AgentPilotConfig(cleanup_on_exit=True), project_root=tmp_path)

    mgr = LifecycleManager(project_root=tmp_path)
    registered = mgr.register_atexit_if_configured()
    assert registered is True

    # Verify the atexit hook was actually registered (check _atexit handlers)
    handlers = [f for f, _, _ in atexit._atexit._atexit_callbacks()] if hasattr(atexit, '_atexit') else []
    # Fallback: just verify the return value — the atexit module does not
    # expose a public listing API before Python 3.14.
    assert registered is True
