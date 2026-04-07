from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from rgen.cli import main, _build_parser


def _seed_interventions_db(target: Path) -> None:
    gh = target / ".github"
    gh.mkdir(parents=True, exist_ok=True)
    db = gh / "interventions.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT CURRENT_TIMESTAMP,
            agent TEXT,
            scenario TEXT,
            query TEXT,
            resolution TEXT,
            files_touched TEXT,
            tags TEXT,
            duration_min REAL,
            outcome TEXT
        )
        """
    )
    rows = [
        ("orchestratore", "_fallback", "optimize postgres query performance", "", "[]", "[]", 1.0, "success"),
        ("orchestratore", "_fallback", "improve database query speed", "", "[]", "[]", 1.0, "success"),
        ("orchestratore", "_fallback", "speed up sql query execution", "", "[]", "[]", 1.0, "success"),
        ("orchestratore", "_fallback", "database operations are too slow", "", "[]", "[]", 1.0, "success"),
    ]
    conn.executemany(
        "INSERT INTO interventions (agent, scenario, query, resolution, files_touched, tags, duration_min, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_suggest_scenarios_cli_flag_recognized() -> None:
    parser = _build_parser()
    args = parser.parse_args([
        "--suggest-scenarios",
        "--min-cluster-size", "4",
        "--similarity-threshold", "0.2",
        "--min-confidence", "0.6",
    ])
    assert args.suggest_scenarios is True
    assert args.min_cluster_size == 4
    assert abs(args.similarity_threshold - 0.2) < 1e-9
    assert abs(args.min_confidence - 0.6) < 1e-9


def test_cli_suggest_scenarios_returns_json(tmp_path: Path, capsys) -> None:
    _seed_interventions_db(tmp_path)
    ret = main(["--suggest-scenarios", "--target", str(tmp_path)])
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "suggested_scenario" in data[0]
    assert data[0]["size"] >= 3


def test_cli_suggest_scenarios_honors_min_cluster_size(tmp_path: Path, capsys) -> None:
    _seed_interventions_db(tmp_path)
    ret = main([
        "--suggest-scenarios",
        "--target", str(tmp_path),
        "--min-cluster-size", "10",
    ])
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data == []


def test_cli_suggest_scenarios_writes_output_file(tmp_path: Path, capsys) -> None:
    _seed_interventions_db(tmp_path)
    output_file = tmp_path / "artifacts" / "scenario-suggestions.json"
    ret = main([
        "--suggest-scenarios",
        "--target", str(tmp_path),
        "--suggest-output", str(output_file),
    ])
    assert ret == 0

    # stdout still returns the same JSON payload
    out = capsys.readouterr().out
    stdout_payload = json.loads(out)

    assert output_file.exists()
    file_payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert file_payload == stdout_payload
    assert len(file_payload) >= 1


def test_cli_suggest_scenarios_honors_min_confidence(tmp_path: Path, capsys) -> None:
    _seed_interventions_db(tmp_path)
    ret = main([
        "--suggest-scenarios",
        "--target", str(tmp_path),
        "--min-confidence", "0.95",
    ])
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data == []
