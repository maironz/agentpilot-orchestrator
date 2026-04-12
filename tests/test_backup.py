"""Tests for backup engine."""

import json
from pathlib import Path

import pytest

from rgen.backup import BackupEngine


# ---------------------------------------------------------------------------
# backup_if_exists
# ---------------------------------------------------------------------------

def test_backup_copies_existing_file(tmp_path: Path) -> None:
    src = tmp_path / "routing-map.json"
    src.write_text('{"test": 1}')
    engine = BackupEngine(tmp_path / ".rgen-backups", project_root=tmp_path)

    result = engine.backup_if_exists(src)

    assert result is not None
    assert result.exists()
    assert result.read_text() == '{"test": 1}'


def test_backup_returns_none_for_nonexistent_file(tmp_path: Path) -> None:
    engine = BackupEngine(tmp_path / ".rgen-backups", project_root=tmp_path)
    result = engine.backup_if_exists(tmp_path / "missing.json")
    assert result is None


def test_backup_dir_created_lazily(tmp_path: Path) -> None:
    backup_root = tmp_path / ".rgen-backups"
    engine = BackupEngine(backup_root, project_root=tmp_path)

    assert not backup_root.exists(), "dir should not exist before any backup"

    src = tmp_path / "file.txt"
    src.write_text("content")
    engine.backup_if_exists(src)

    assert backup_root.exists(), "dir should be created after first backup"


def test_backup_dir_not_created_when_file_missing(tmp_path: Path) -> None:
    backup_root = tmp_path / ".rgen-backups"
    engine = BackupEngine(backup_root, project_root=tmp_path)
    engine.backup_if_exists(tmp_path / "missing.txt")
    assert not backup_root.exists()


def test_multiple_backups_share_session_dir(tmp_path: Path) -> None:
    f1 = tmp_path / "a.json"
    f2 = tmp_path / "b.json"
    f1.write_text("a")
    f2.write_text("b")
    engine = BackupEngine(tmp_path / ".rgen-backups", project_root=tmp_path)

    engine.backup_if_exists(f1)
    engine.backup_if_exists(f2)

    sessions = engine.list_backups()
    assert len(sessions) == 1, "Both files should be in the same session"


def test_backup_preserves_nested_relative_paths(tmp_path: Path) -> None:
    src = tmp_path / ".github" / "esperti" / "esperto_dev.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("# Dev")

    engine = BackupEngine(tmp_path / ".github" / ".rgen-backups", project_root=tmp_path)
    backup_path = engine.backup_if_exists(src)

    assert backup_path is not None
    assert backup_path.relative_to(engine.session_dir).as_posix() == ".github/esperti/esperto_dev.md"


# ---------------------------------------------------------------------------
# list_backups and history
# ---------------------------------------------------------------------------

def test_list_backups_empty_when_no_backup_dir(tmp_path: Path) -> None:
    engine = BackupEngine(tmp_path / ".rgen-backups", project_root=tmp_path)
    assert engine.list_backups() == []


def test_list_backups_sorted_newest_first(tmp_path: Path) -> None:
    backup_root = tmp_path / ".rgen-backups"
    (backup_root / "20240101_100000").mkdir(parents=True)
    (backup_root / "20240102_100000").mkdir()
    (backup_root / "20240103_100000").mkdir()

    engine = BackupEngine(backup_root, project_root=tmp_path)
    names = [d.name for d in engine.list_backups()]
    assert names == ["20240103_100000", "20240102_100000", "20240101_100000"]


def test_history_tracks_written_and_updated_counts(tmp_path: Path) -> None:
    project = tmp_path / "app"
    backup = project / ".github" / ".rgen-backups"
    engine = BackupEngine(backup, project_root=project, command="generate")

    created = project / ".github" / "new.md"
    created.parent.mkdir(parents=True, exist_ok=True)
    created.write_text("new")
    engine.record_written_file(created, existed_before=False)

    updated = project / ".github" / "router.py"
    updated.write_text("new-router")
    engine.record_written_file(updated, existed_before=True)

    history = engine.history()
    assert len(history) == 1
    assert history[0]["written_count"] == 1
    assert history[0]["updated_count"] == 1


def test_history_supports_five_generations_sequence(tmp_path: Path) -> None:
    project = tmp_path / "app"
    backup = project / ".github" / ".rgen-backups"
    backup.mkdir(parents=True, exist_ok=True)

    for idx in range(5):
        generation = backup / f"20240101_12000{idx}"
        generation.mkdir(parents=True, exist_ok=True)
        metadata = {
            "generation_id": generation.name,
            "created_at": f"2024-01-01T12:00:0{idx}Z",
            "command": "generate",
            "target": str(project),
            "pattern": "psm_stack",
            "language": "en",
            "written_files": [f".github/generated-{idx}.md"],
            "updated_files": [],
            "checksum_map": {},
            "outcome": "success",
        }
        (generation / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    engine = BackupEngine(backup, project_root=project)
    history = engine.history(limit=5)

    assert len(history) == 5
    assert history[0]["generation_id"] == "20240101_120004"
    assert history[-1]["generation_id"] == "20240101_120000"


# ---------------------------------------------------------------------------
# rollback and restore
# ---------------------------------------------------------------------------

def test_rollback_restores_updated_and_removes_created_files(tmp_path: Path) -> None:
    project = tmp_path / "app"
    existing = project / ".github" / "router.py"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old")

    engine = BackupEngine(project / ".github" / ".rgen-backups", project_root=project)
    engine.backup_if_exists(existing)
    existing.write_text("new")
    engine.record_written_file(existing, existed_before=True)

    created = project / ".github" / "copilot-instructions.md"
    created.write_text("generated")
    engine.record_written_file(created, existed_before=False)

    generation_id = engine.history()[0]["generation_id"]
    report = engine.rollback(str(generation_id))

    assert existing.read_text() == "old"
    assert not created.exists()
    assert ".github/router.py" in report["restored"]
    assert ".github/copilot-instructions.md" in report["removed"]


def test_rollback_skips_manual_changes_without_force(tmp_path: Path) -> None:
    project = tmp_path / "app"
    existing = project / ".github" / "router.py"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old")

    engine = BackupEngine(project / ".github" / ".rgen-backups", project_root=project)
    engine.backup_if_exists(existing)
    existing.write_text("new")
    engine.record_written_file(existing, existed_before=True)

    existing.write_text("manual")
    generation_id = str(engine.history()[0]["generation_id"])
    report = engine.rollback(generation_id)

    assert existing.read_text() == "manual"
    assert ".github/router.py" in report["skipped_manual"]


def test_restore_copies_files_to_target(tmp_path: Path) -> None:
    backup_root = tmp_path / ".rgen-backups"
    session = backup_root / "20240101_120000"
    nested = session / ".github" / "routing-map.json"
    nested.parent.mkdir(parents=True)
    nested.write_text('{"restored": true}')

    engine = BackupEngine(backup_root, project_root=tmp_path)
    restore_dir = tmp_path / "restored"
    restored = engine.restore("20240101_120000", restore_dir)

    assert len(restored) == 1
    assert (restore_dir / ".github" / "routing-map.json").read_text() == '{"restored": true}'


def test_restore_raises_for_missing_session(tmp_path: Path) -> None:
    engine = BackupEngine(tmp_path / ".rgen-backups", project_root=tmp_path)
    with pytest.raises(FileNotFoundError, match="Backup session not found"):
        engine.restore("99991231_235959", tmp_path / "out")
