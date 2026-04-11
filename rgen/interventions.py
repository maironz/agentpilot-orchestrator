"""Lightweight intervention store for rgen CLI features."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class InterventionStore:
    """Read-only store used by analytics features (scenario suggestions)."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else Path(".github") / "interventions.db"
        self._conn: sqlite3.Connection | None = None
        self._open()

    def _open(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def recent(self, limit: int = 100) -> list[dict]:
        """Returns most recent interventions, newest first."""
        if self._conn is None:
            return []
        try:
            rows = self._conn.execute(
                "SELECT * FROM interventions ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.Error:
            return []
        return [dict(r) for r in rows]
