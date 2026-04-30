#!/usr/bin/env python3
"""
PSM Stack — Session Manager (Milestone 2)

Manages routing sessions: UUID generation, TTL-based lifecycle, last-activity
refresh, and cleanup of expired sessions.

A session groups multiple related interventions under a single session_id,
enabling follow-up context propagation and rolling summaries.

Design decisions:
- SQLite-backed, same DB as interventions for atomic operations.
- Default TTL: 3600 seconds (1 hour). Override via SessionManager(ttl=N).
- Cleanup is lazy (on open/close) + explicit via cleanup_expired().
- No automatic background threads: routing layer is synchronous.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "interventions.db"

_SESSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_activity TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    ttl_seconds INTEGER NOT NULL DEFAULT 3600,
    agent TEXT,
    summary TEXT NOT NULL DEFAULT '',    -- compact rolling summary
    intervention_count INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1    -- 1=active, 0=expired/closed
);

CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(active);
"""

DEFAULT_TTL = 3600  # seconds


class SessionManager:
    """
    Manages routing sessions with TTL-based lifecycle.

    Usage:
        mgr = SessionManager()
        sid = mgr.create()
        mgr.touch(sid)
        session = mgr.get(sid)
        mgr.close_session(sid)
        mgr.cleanup_expired()
        mgr.close()
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        ttl: int = DEFAULT_TTL,
    ):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.default_ttl = ttl
        self._conn: Any = None
        self._ensure_db()

    def _ensure_db(self):
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SESSION_SCHEMA)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.commit()

    def create(self, agent: str | None = None, ttl: int | None = None) -> str:
        """
        Create a new session and return its session_id (UUID4).

        Args:
            agent: Primary agent for this session.
            ttl: Override default TTL in seconds.

        Returns:
            session_id string (UUID4).
        """
        sid = str(uuid.uuid4())
        effective_ttl = ttl if ttl is not None else self.default_ttl
        self._conn.execute(
            """INSERT INTO sessions (session_id, agent, ttl_seconds, active)
               VALUES (?, ?, ?, 1)""",
            (sid, agent, effective_ttl),
        )
        self._conn.commit()
        return sid

    def get(self, session_id: str) -> dict | None:
        """
        Retrieve a session by ID. Returns None if not found or expired.
        Does NOT auto-touch last_activity.
        """
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        session = dict(row)
        if not self._is_alive(session):
            return None
        return session

    def touch(self, session_id: str) -> bool:
        """
        Refresh last_activity timestamp for a session.
        Returns True if session was found and is still alive, False otherwise.
        """
        session = self.get(session_id)
        if session is None:
            return False
        self._conn.execute(
            "UPDATE sessions SET last_activity = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE session_id = ?",
            (session_id,),
        )
        self._conn.commit()
        return True

    def update_summary(self, session_id: str, summary: str, increment_count: bool = True) -> bool:
        """
        Update the rolling summary for a session.
        Returns True if session was found and updated.
        """
        session = self.get(session_id)
        if session is None:
            return False
        delta = 1 if increment_count else 0
        self._conn.execute(
            """UPDATE sessions
               SET summary = ?,
                   intervention_count = intervention_count + ?,
                   last_activity = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
               WHERE session_id = ?""",
            (summary, delta, session_id),
        )
        self._conn.commit()
        return True

    def close_session(self, session_id: str) -> bool:
        """
        Mark a session as closed (active=0). Returns True if found.
        """
        result = self._conn.execute(
            "UPDATE sessions SET active = 0 WHERE session_id = ?",
            (session_id,),
        )
        self._conn.commit()
        return result.rowcount > 0

    def cleanup_expired(self) -> int:
        """
        Mark all TTL-expired sessions as inactive.
        Returns the number of sessions expired.
        """
        # A session is expired if:
        # current_time - last_activity > ttl_seconds (AND active = 1)
        result = self._conn.execute(
            """UPDATE sessions
               SET active = 0
               WHERE active = 1
                 AND (
                     CAST((julianday('now') - julianday(last_activity)) * 86400 AS INTEGER)
                     > ttl_seconds
                 )""",
        )
        self._conn.commit()
        return result.rowcount

    def list_active(self, limit: int = 20) -> list[dict]:
        """Return active (non-expired) sessions, newest first."""
        self.cleanup_expired()
        rows = self._conn.execute(
            "SELECT * FROM sessions WHERE active = 1 ORDER BY last_activity DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        """Return aggregate session statistics."""
        total = self._conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
        active = self._conn.execute(
            "SELECT COUNT(*) as c FROM sessions WHERE active = 1"
        ).fetchone()["c"]
        expired = total - active
        avg_count_row = self._conn.execute(
            "SELECT AVG(intervention_count) as avg FROM sessions WHERE active = 1"
        ).fetchone()
        return {
            "total_sessions": total,
            "active_sessions": active,
            "expired_sessions": expired,
            "avg_interventions_per_active_session": round(avg_count_row["avg"] or 0.0, 1),
        }

    def _is_alive(self, session: dict) -> bool:
        """Check if a session dict is still within its TTL and active."""
        if not session.get("active", 0):
            return False
        last_activity = session.get("last_activity", "")
        ttl = session.get("ttl_seconds", self.default_ttl)
        if not last_activity:
            return True
        try:
            last_dt = datetime.fromisoformat(last_activity.rstrip("Z")).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            elapsed = (now - last_dt).total_seconds()
            return elapsed <= ttl
        except (ValueError, AttributeError):
            return True  # Be permissive on parse error

    def close(self):
        """Close the DB connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
