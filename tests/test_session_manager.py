"""
Tests for SessionManager — TTL lifecycle, create/touch/expire/cleanup.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from session_manager import SessionManager


@pytest.fixture
def mgr(tmp_path):
    db = tmp_path / "test_sessions.db"
    m = SessionManager(db_path=db, ttl=3600)
    yield m
    m.close()


# ─── create ───

def test_create_returns_uuid(mgr):
    sid = mgr.create()
    assert isinstance(sid, str)
    assert len(sid) == 36  # UUID4 format


def test_create_with_agent(mgr):
    sid = mgr.create(agent="backend")
    session = mgr.get(sid)
    assert session is not None
    assert session["agent"] == "backend"


def test_create_custom_ttl(mgr):
    sid = mgr.create(ttl=7200)
    session = mgr.get(sid)
    assert session is not None
    assert session["ttl_seconds"] == 7200


# ─── get ───

def test_get_returns_none_for_unknown(mgr):
    assert mgr.get("nonexistent-id") is None


def test_get_returns_active_session(mgr):
    sid = mgr.create()
    session = mgr.get(sid)
    assert session is not None
    assert session["session_id"] == sid
    assert session["active"] == 1


def test_get_returns_none_for_expired_session(tmp_path):
    db = tmp_path / "ttl_test.db"
    mgr = SessionManager(db_path=db, ttl=0)  # TTL=0 → expires immediately
    sid = mgr.create()
    # Force expiry by using a TTL of 0 and touching the DB directly
    mgr._conn.execute(
        "UPDATE sessions SET last_activity = '2000-01-01T00:00:00Z' WHERE session_id = ?",
        (sid,),
    )
    mgr._conn.commit()
    result = mgr.get(sid)
    assert result is None
    mgr.close()


# ─── touch ───

def test_touch_returns_true_for_active(mgr):
    sid = mgr.create()
    assert mgr.touch(sid) is True


def test_touch_returns_false_for_unknown(mgr):
    assert mgr.touch("bad-id") is False


# ─── update_summary ───

def test_update_summary(mgr):
    sid = mgr.create()
    mgr.update_summary(sid, "Fixed DB index", increment_count=True)
    session = mgr.get(sid)
    assert session["summary"] == "Fixed DB index"
    assert session["intervention_count"] == 1


def test_update_summary_increments(mgr):
    sid = mgr.create()
    mgr.update_summary(sid, "step 1", increment_count=True)
    mgr.update_summary(sid, "step 2", increment_count=True)
    session = mgr.get(sid)
    assert session["intervention_count"] == 2


# ─── close_session ───

def test_close_session(mgr):
    sid = mgr.create()
    assert mgr.close_session(sid) is True
    assert mgr.get(sid) is None  # closed → not alive


def test_close_session_unknown(mgr):
    assert mgr.close_session("nope") is False


# ─── cleanup_expired ───

def test_cleanup_expired(tmp_path):
    db = tmp_path / "cleanup.db"
    mgr = SessionManager(db_path=db, ttl=3600)
    sid1 = mgr.create()
    sid2 = mgr.create()
    # Artificially expire sid1
    mgr._conn.execute(
        "UPDATE sessions SET last_activity = '2000-01-01T00:00:00Z' WHERE session_id = ?",
        (sid1,),
    )
    mgr._conn.commit()
    expired = mgr.cleanup_expired()
    assert expired == 1
    assert mgr.get(sid1) is None
    assert mgr.get(sid2) is not None
    mgr.close()


# ─── list_active ───

def test_list_active(mgr):
    sid1 = mgr.create(agent="backend")
    sid2 = mgr.create(agent="devops")
    active = mgr.list_active()
    ids = [s["session_id"] for s in active]
    assert sid1 in ids
    assert sid2 in ids


# ─── stats ───

def test_stats_empty(mgr):
    stats = mgr.stats()
    assert stats["total_sessions"] == 0
    assert stats["active_sessions"] == 0


def test_stats_with_sessions(mgr):
    mgr.create()
    mgr.create()
    stats = mgr.stats()
    assert stats["total_sessions"] == 2
    assert stats["active_sessions"] == 2
    assert stats["expired_sessions"] == 0


# ─── context manager ───

def test_context_manager(tmp_path):
    db = tmp_path / "ctx.db"
    with SessionManager(db_path=db) as m:
        sid = m.create()
        assert m.get(sid) is not None
    # After exit, connection closed — no exception expected
