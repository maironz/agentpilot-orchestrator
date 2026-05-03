"""Tests for rgen/session_context.py and FSPolicy dynamic whitelist (C3)."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from rgen.fs_policy import FSPolicy, PolicyViolation
from rgen.session_context import (
    SessionContext,
    _STATE_REL,
    _new_id,
    get_active,
    reset_active,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_module_singleton():
    """Always reset the module-level active session after each test."""
    yield
    reset_active()


# ---------------------------------------------------------------------------
# _new_id
# ---------------------------------------------------------------------------


def test_new_id_length():
    sid = _new_id()
    assert len(sid) == 8


def test_new_id_unique():
    ids = {_new_id() for _ in range(50)}
    assert len(ids) == 50


def test_new_id_hex():
    sid = _new_id()
    int(sid, 16)  # raises ValueError if not valid hex


# ---------------------------------------------------------------------------
# SessionContext lifecycle
# ---------------------------------------------------------------------------


def test_context_creates_state_dir(tmp_path):
    with SessionContext(project_root=tmp_path) as ctx:
        assert ctx.state_dir.is_dir()


def test_context_writes_session_json(tmp_path):
    with SessionContext(project_root=tmp_path) as ctx:
        manifest_path = ctx.state_dir / "session.json"
        assert manifest_path.is_file()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["session_id"] == ctx.session_id
        assert "started_at" in data
        assert data["project_root"] == str(tmp_path.resolve())


def test_context_writes_session_end_json(tmp_path):
    with SessionContext(project_root=tmp_path) as ctx:
        pass  # __exit__ calls stop()
    end_path = ctx.state_dir / "session_end.json"
    assert end_path.is_file()
    data = json.loads(end_path.read_text(encoding="utf-8"))
    assert data["session_id"] == ctx.session_id
    assert "ended_at" in data


def test_context_state_dir_path(tmp_path):
    ctx = SessionContext(project_root=tmp_path, session_id="abc12345")
    expected = (tmp_path / _STATE_REL / "abc12345").resolve()
    assert ctx.state_dir == expected


def test_context_explicit_session_id(tmp_path):
    ctx = SessionContext(project_root=tmp_path, session_id="deadbeef")
    assert ctx.session_id == "deadbeef"


def test_context_policy_registered(tmp_path):
    """After start(), state_dir must be in the policy whitelist."""
    with SessionContext(project_root=tmp_path) as ctx:
        from rgen.fs_policy import _normalize
        assert _normalize(ctx.state_dir) in ctx.policy._extra_allowed


def test_context_allows_write_in_state_dir(tmp_path):
    """Writes to state_dir must not raise or warn."""
    with SessionContext(project_root=tmp_path) as ctx:
        target = ctx.state_dir / "data.txt"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ctx.policy.write_file(target, "hello")
        assert not any("whitelist" in str(x.message) for x in w)
        assert target.read_text(encoding="utf-8") == "hello"


def test_context_stop_noop_if_not_started(tmp_path):
    """stop() on a never-started session must not raise."""
    ctx = SessionContext(project_root=tmp_path)
    ctx.stop()  # no state_dir yet — must be graceful


def test_context_stop_idempotent(tmp_path):
    """Calling stop() twice must not raise."""
    with SessionContext(project_root=tmp_path) as ctx:
        pass
    ctx.stop()  # second call


# ---------------------------------------------------------------------------
# FSPolicy.add_allowed_path / remove_allowed_path
# ---------------------------------------------------------------------------


def test_add_allowed_path_registers(tmp_path):
    policy = FSPolicy(project_root=tmp_path)
    extra = (tmp_path / "custom_dir").resolve()
    policy.add_allowed_path(extra)
    from rgen.fs_policy import _normalize
    assert _normalize(extra) in policy._extra_allowed


def test_add_allowed_path_permits_write(tmp_path):
    policy = FSPolicy(project_root=tmp_path)
    extra = tmp_path / "custom_dir"
    policy.add_allowed_path(extra)
    extra.mkdir()
    target = extra / "file.txt"
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        policy.write_file(target, "data")
    assert not any("whitelist" in str(x.message) for x in w)
    assert target.read_text(encoding="utf-8") == "data"


def test_remove_allowed_path_revokes(tmp_path):
    policy = FSPolicy(project_root=tmp_path, strict=False)
    extra = tmp_path / "custom_dir"
    policy.add_allowed_path(extra)
    policy.remove_allowed_path(extra)
    from rgen.fs_policy import _normalize
    assert _normalize(extra.resolve()) not in policy._extra_allowed


def test_add_allowed_path_outside_root_warns(tmp_path, tmp_path_factory):
    """Paths outside project root must not be registered (emit warning)."""
    other_root = tmp_path_factory.mktemp("other")
    policy = FSPolicy(project_root=tmp_path, strict=False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        policy.add_allowed_path(other_root / "escape")
    assert any("add_allowed_path outside project root" in str(x.message) for x in w)
    assert not policy._extra_allowed


def test_add_allowed_path_outside_root_strict(tmp_path, tmp_path_factory):
    """In strict mode, adding an out-of-root path raises PolicyViolation."""
    other_root = tmp_path_factory.mktemp("other_strict")
    policy = FSPolicy(project_root=tmp_path, strict=True)
    with pytest.raises(PolicyViolation, match="add_allowed_path outside project root"):
        policy.add_allowed_path(other_root / "escape")


# ---------------------------------------------------------------------------
# get_active / reset_active module singleton
# ---------------------------------------------------------------------------


def test_get_active_creates_singleton(tmp_path):
    ctx1 = get_active(project_root=tmp_path)
    ctx2 = get_active()  # no project_root → cached
    assert ctx1 is ctx2


def test_get_active_starts_session(tmp_path):
    ctx = get_active(project_root=tmp_path)
    assert ctx.state_dir.is_dir()
    assert (ctx.state_dir / "session.json").is_file()


def test_reset_active_discards_singleton(tmp_path):
    ctx1 = get_active(project_root=tmp_path)
    reset_active()
    ctx2 = get_active(project_root=tmp_path)
    assert ctx1 is not ctx2


def test_reset_active_writes_end_marker(tmp_path):
    ctx = get_active(project_root=tmp_path)
    state_dir = ctx.state_dir
    reset_active()
    assert (state_dir / "session_end.json").is_file()


def test_get_active_new_project_root_resets(tmp_path, tmp_path_factory):
    root2 = tmp_path_factory.mktemp("root2")
    ctx1 = get_active(project_root=tmp_path)
    ctx2 = get_active(project_root=root2)  # new root → new instance
    assert ctx1 is not ctx2
