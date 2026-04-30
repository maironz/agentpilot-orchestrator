#!/usr/bin/env python3
"""
PSM Stack — Intervention Memory (SQLite + FTS5)

Stores intervention history for routing self-improvement.
Append-only design with full-text search via FTS5.

Usage:
    from interventions import InterventionStore
    store = InterventionStore()          # auto-creates DB if missing
    store.log(agent="fullstack", scenario="database_optimization",
              query="optimize slow query", resolution="Added index on created_at",
              files_touched=["Z:/joomla/src/Model/Invoice.php"],
              tags=["performance", "sql"])
    results = store.search("slow query")
    stats = store.stats()
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "interventions.db"

_SCHEMA = """
-- Core intervention log
CREATE TABLE IF NOT EXISTS interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    agent TEXT NOT NULL,
    scenario TEXT NOT NULL,
    query TEXT NOT NULL,
    resolution TEXT NOT NULL DEFAULT '',
    files_touched TEXT NOT NULL DEFAULT '[]',  -- JSON array
    tags TEXT NOT NULL DEFAULT '[]',           -- JSON array
    duration_min REAL,                         -- estimated effort in minutes
    outcome TEXT NOT NULL DEFAULT 'success',   -- success | partial | failed | reverted
    -- Milestone 2: session + recovery + trace fields
    session_id TEXT,                           -- UUID grouping related interventions
    trace_id TEXT,                             -- UUID for end-to-end request trace
    error_class TEXT,                          -- timeout | ambiguity | policy | network | unknown
    recovery_action TEXT,                      -- retry | fallback | abort | none
    retry_count INTEGER NOT NULL DEFAULT 0,    -- number of retries attempted
    parent_id INTEGER REFERENCES interventions(id)  -- link to parent intervention
);

-- FTS5 virtual table for full-text search on query + resolution + tags
CREATE VIRTUAL TABLE IF NOT EXISTS interventions_fts USING fts5(
    query, resolution, tags,
    content='interventions',
    content_rowid='id'
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS interventions_ai AFTER INSERT ON interventions BEGIN
    INSERT INTO interventions_fts(rowid, query, resolution, tags)
    VALUES (new.id, new.query, new.resolution, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS interventions_ad AFTER DELETE ON interventions BEGIN
    INSERT INTO interventions_fts(interventions_fts, rowid, query, resolution, tags)
    VALUES ('delete', old.id, old.query, old.resolution, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS interventions_au AFTER UPDATE ON interventions BEGIN
    INSERT INTO interventions_fts(interventions_fts, rowid, query, resolution, tags)
    VALUES ('delete', old.id, old.query, old.resolution, old.tags);
    INSERT INTO interventions_fts(rowid, query, resolution, tags)
    VALUES (new.id, new.query, new.resolution, new.tags);
END;

-- Indices for common queries
CREATE INDEX IF NOT EXISTS idx_interventions_agent ON interventions(agent);
CREATE INDEX IF NOT EXISTS idx_interventions_scenario ON interventions(scenario);
CREATE INDEX IF NOT EXISTS idx_interventions_ts ON interventions(ts);
CREATE INDEX IF NOT EXISTS idx_interventions_outcome ON interventions(outcome);
CREATE INDEX IF NOT EXISTS idx_interventions_session_id ON interventions(session_id);
CREATE INDEX IF NOT EXISTS idx_interventions_trace_id ON interventions(trace_id);
"""

# Additive migration: add Milestone 2 columns to existing DBs without data loss
_MIGRATION_M2 = """
ALTER TABLE interventions ADD COLUMN session_id TEXT;
ALTER TABLE interventions ADD COLUMN trace_id TEXT;
ALTER TABLE interventions ADD COLUMN error_class TEXT;
ALTER TABLE interventions ADD COLUMN recovery_action TEXT;
ALTER TABLE interventions ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE interventions ADD COLUMN parent_id INTEGER REFERENCES interventions(id);
"""


class InterventionStore:
    """SQLite-backed intervention memory with FTS5 full-text search."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._conn: Any = None
        self._ensure_db()

    def _ensure_db(self):
        """Create DB and schema if missing; apply additive migrations."""
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._apply_migrations()

    def _apply_migrations(self):
        """Apply additive ALTER TABLE migrations for existing DBs (idempotent)."""
        existing_cols = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(interventions)").fetchall()
        }
        m2_cols = {
            "session_id": "ALTER TABLE interventions ADD COLUMN session_id TEXT",
            "trace_id": "ALTER TABLE interventions ADD COLUMN trace_id TEXT",
            "error_class": "ALTER TABLE interventions ADD COLUMN error_class TEXT",
            "recovery_action": "ALTER TABLE interventions ADD COLUMN recovery_action TEXT",
            "retry_count": "ALTER TABLE interventions ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0",
            "parent_id": "ALTER TABLE interventions ADD COLUMN parent_id INTEGER REFERENCES interventions(id)",
        }
        for col, stmt in m2_cols.items():
            if col not in existing_cols:
                self._conn.execute(stmt)
        self._conn.commit()
        # Add new indices if not present
        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_interventions_session_id ON interventions(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_interventions_trace_id ON interventions(trace_id)",
        ):
            self._conn.execute(stmt)
        self._conn.commit()

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ─── Write Operations ───

    def log(
        self,
        agent: str,
        scenario: str,
        query: str,
        resolution: str = "",
        files_touched: list[str] | None = None,
        tags: list[str] | None = None,
        duration_min: float | None = None,
        outcome: str = "success",
        # Milestone 2 fields
        session_id: str | None = None,
        trace_id: str | None = None,
        error_class: str | None = None,
        recovery_action: str | None = None,
        retry_count: int = 0,
        parent_id: int | None = None,
    ) -> int:
        """
        Log a new intervention. Returns the inserted row ID.

        Args:
            agent: Agent that handled the intervention (fullstack, sistemista, etc.)
            scenario: Routing scenario that matched
            query: Original user query/request
            resolution: What was done to resolve it
            files_touched: List of file paths modified
            tags: Categorization tags
            duration_min: Estimated effort in minutes
            outcome: success | partial | failed | reverted
            session_id: UUID grouping related interventions in a session
            trace_id: UUID for end-to-end request trace
            error_class: timeout | ambiguity | policy | network | unknown
            recovery_action: retry | fallback | abort | none
            retry_count: Number of retries attempted
            parent_id: ID of parent intervention for trace linking
        """
        files_json = json.dumps(files_touched or [], ensure_ascii=False)
        tags_json = json.dumps(tags or [], ensure_ascii=False)

        cursor = self._conn.execute(
            """INSERT INTO interventions
               (agent, scenario, query, resolution, files_touched, tags, duration_min, outcome,
                session_id, trace_id, error_class, recovery_action, retry_count, parent_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (agent, scenario, query, resolution, files_json, tags_json, duration_min, outcome,
             session_id, trace_id, error_class, recovery_action, retry_count, parent_id),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def update_resolution(self, intervention_id: int, resolution: str, outcome: str = "success"):
        """Update the resolution of an existing intervention (e.g., after completing work)."""
        self._conn.execute(
            "UPDATE interventions SET resolution = ?, outcome = ? WHERE id = ?",
            (resolution, outcome, intervention_id),
        )
        self._conn.commit()

    # ─── Read Operations ───

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Full-text search across query, resolution, and tags.
        Returns interventions ranked by relevance (BM25).
        Tokenizes the query and uses OR for broader matching.
        """
        # Tokenize query into individual words and join with OR for broader matching
        tokens = [t.strip() for t in query.split() if len(t.strip()) > 2]
        if not tokens:
            return []
        fts_query = " OR ".join(tokens)

        rows = self._conn.execute(
            """SELECT i.*, rank
               FROM interventions_fts fts
               JOIN interventions i ON i.id = fts.rowid
               WHERE interventions_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (fts_query, limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def recent(self, limit: int = 20) -> list[dict]:
        """Get most recent interventions."""
        rows = self._conn.execute(
            "SELECT * FROM interventions ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def by_scenario(self, scenario: str, limit: int = 20) -> list[dict]:
        """Get interventions for a specific scenario."""
        rows = self._conn.execute(
            "SELECT * FROM interventions WHERE scenario = ? ORDER BY ts DESC LIMIT ?",
            (scenario, limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def by_agent(self, agent: str, limit: int = 20) -> list[dict]:
        """Get interventions handled by a specific agent."""
        rows = self._conn.execute(
            "SELECT * FROM interventions WHERE agent = ? ORDER BY ts DESC LIMIT ?",
            (agent, limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def hotspots(self, limit: int = 10) -> list[dict]:
        """
        Find hot files — files that appear most frequently in interventions.
        Useful for identifying recurring problem areas.
        """
        # SQLite doesn't have unnest, so we process in Python
        rows = self._conn.execute(
            "SELECT files_touched FROM interventions WHERE files_touched != '[]'"
        ).fetchall()

        file_counts: dict[str, int] = {}
        for row in rows:
            files = json.loads(row["files_touched"])
            for f in files:
                file_counts[f] = file_counts.get(f, 0) + 1

        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"file": f, "count": c} for f, c in sorted_files[:limit]]

    def recurrences(self, min_count: int = 2) -> list[dict]:
        """
        Find recurring patterns — scenarios that trigger repeatedly.
        Signals areas needing structural fixes rather than point solutions.
        """
        rows = self._conn.execute(
            """SELECT scenario, agent, COUNT(*) as count,
                      MIN(ts) as first_seen, MAX(ts) as last_seen
               FROM interventions
               GROUP BY scenario, agent
               HAVING COUNT(*) >= ?
               ORDER BY count DESC""",
            (min_count,),
        ).fetchall()
        return [dict(r) for r in rows]

    def misrouted(self) -> list[dict]:
        """
        Find interventions marked as failed or reverted — potential misrouting.
        """
        rows = self._conn.execute(
            """SELECT * FROM interventions
               WHERE outcome IN ('failed', 'reverted')
               ORDER BY ts DESC""",
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def stats(self) -> dict:
        """
        Aggregate statistics about the intervention history.
        """
        total = self._conn.execute("SELECT COUNT(*) as c FROM interventions").fetchone()["c"]

        if total == 0:
            return {
                "total_interventions": 0,
                "by_agent": {},
                "by_outcome": {},
                "by_scenario_top10": [],
                "hotspot_files_top5": [],
                "date_range": None,
            }

        by_agent = self._conn.execute(
            "SELECT agent, COUNT(*) as c FROM interventions GROUP BY agent ORDER BY c DESC"
        ).fetchall()

        by_outcome = self._conn.execute(
            "SELECT outcome, COUNT(*) as c FROM interventions GROUP BY outcome ORDER BY c DESC"
        ).fetchall()

        by_scenario = self._conn.execute(
            "SELECT scenario, COUNT(*) as c FROM interventions GROUP BY scenario ORDER BY c DESC LIMIT 10"
        ).fetchall()

        date_range = self._conn.execute(
            "SELECT MIN(ts) as first, MAX(ts) as last FROM interventions"
        ).fetchone()

        return {
            "total_interventions": total,
            "by_agent": {r["agent"]: r["c"] for r in by_agent},
            "by_outcome": {r["outcome"]: r["c"] for r in by_outcome},
            "by_scenario_top10": [{"scenario": r["scenario"], "count": r["c"]} for r in by_scenario],
            "hotspot_files_top5": self.hotspots(limit=5),
            "date_range": {"first": date_range["first"], "last": date_range["last"]} if date_range else None,
        }

    # ─── Helpers ───

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict, parsing JSON fields."""
        d = dict(row)
        for field in ("files_touched", "tags"):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except json.JSONDecodeError:
                    pass
        # Remove FTS rank if present
        d.pop("rank", None)
        return d


# ─── CLI ───

def main():
    """Simple CLI for intervention management."""
    import sys

    args = sys.argv[1:]
    if not args:
        print("""
Intervention Memory CLI
  python .github/interventions.py stats           → Show statistics
  python .github/interventions.py recent [N]      → Recent N interventions
  python .github/interventions.py search "query"  → Full-text search
  python .github/interventions.py hotspots        → Most-touched files
  python .github/interventions.py recurrences     → Recurring patterns
  python .github/interventions.py misrouted       → Failed/reverted interventions
        """)
        return

    store = InterventionStore()
    cmd = args[0]

    if cmd == "stats":
        print(json.dumps(store.stats(), indent=2, ensure_ascii=False))
    elif cmd == "recent":
        limit = int(args[1]) if len(args) > 1 else 20
        for item in store.recent(limit):
            print(f"  [{item['ts'][:10]}] {item['agent']}/{item['scenario']}: {item['query'][:80]}")
    elif cmd == "search" and len(args) > 1:
        query = " ".join(args[1:])
        results = store.search(query)
        if not results:
            print("Nessun risultato.")
        for item in results:
            print(f"  [{item['ts'][:10]}] {item['agent']}/{item['scenario']}: {item['query'][:80]}")
            if item.get("resolution"):
                print(f"    → {item['resolution'][:100]}")
    elif cmd == "hotspots":
        for h in store.hotspots():
            print(f"  {h['count']}x {h['file']}")
    elif cmd == "recurrences":
        for r in store.recurrences():
            print(f"  {r['count']}x {r['scenario']} ({r['agent']}) [{r['first_seen'][:10]} → {r['last_seen'][:10]}]")
    elif cmd == "misrouted":
        for item in store.misrouted():
            print(f"  [{item['ts'][:10]}] {item['agent']}/{item['scenario']}: {item['query'][:80]} → {item['outcome']}")
    else:
        print(f"Comando sconosciuto: {cmd}")

    store.close()


if __name__ == "__main__":
    main()
