"""Tests for backup engine -- Step 1."""

from pathlib import Path

import pytest

from rgen.backup import BackupEngine


# ---------------------------------------------------------------------------
# backup_if_exists
# ---------------------------------------------------------------------------

def test_backup_copies_existing_file(tmp_path: Path) -> None:
    src = tmp_path / "routing-map.json"
    src.write_text('{"test": 1}')
    engine = BackupEngine(tmp_path / ".rgen-backups")

    result = engine.backup_if_exists(src)

    assert result is not None
    assert result.exists()
    assert result.read_text() == '{"test": 1}'


def test_backup_returns_none_for_nonexistent_file(tmp_path: Path) -> None:
    engine = BackupEngine(tmp_path / ".rgen-backups")
    result = engine.backup_if_exists(tmp_path / "missing.json")
    assert result is None


def test_backup_dir_created_lazily(tmp_path: Path) -> None:
    backup_root = tmp_path / ".rgen-backups"
    engine = BackupEngine(backup_root)

    assert not backup_root.exists(), "dir should not exist before any backup"

    src = tmp_path / "file.txt"
    src.write_text("content")
    engine.backup_if_exists(src)

    assert backup_root.exists(), "dir should be created after first backup"


def test_backup_dir_not_created_when_file_missing(tmp_path: Path) -> None:
    backup_root = tmp_path / ".rgen-backups"
    engine = BackupEngine(backup_root)
    engine.backup_if_exists(tmp_path / "missing.txt")
    assert not backup_root.exists()


def test_multiple_backups_share_session_dir(tmp_path: Path) -> None:
    f1 = tmp_path / "a.json"
    f2 = tmp_path / "b.json"
    f1.write_text("a")
    f2.write_text("b")
    engine = BackupEngine(tmp_path / ".rgen-backups")

    engine.backup_if_exists(f1)
    engine.backup_if_exists(f2)

    sessions = engine.list_backups()
    assert len(sessions) == 1, "Both files should be in the same session"
    assert len(list(sessions[0].iterdir())) == 2


# ---------------------------------------------------------------------------
# list_backups
# ---------------------------------------------------------------------------

def test_list_backups_empty_when_no_backup_dir(tmp_path: Path) -> None:
    engine = BackupEngine(tmp_path / ".rgen-backups")
    assert engine.list_backups() == []


def test_list_backups_sorted_newest_first(tmp_path: Path) -> None:
    backup_root = tmp_path / ".rgen-backups"
    (backup_root / "20240101_100000").mkdir(parents=True)
    (backup_root / "20240102_100000").mkdir()
    (backup_root / "20240103_100000").mkdir()

    engine = BackupEngine(backup_root)
    names = [d.name for d in engine.list_backups()]
    assert names == ["20240103_100000", "20240102_100000", "20240101_100000"]


# ---------------------------------------------------------------------------
# restore
# ---------------------------------------------------------------------------

def test_restore_copies_files_to_target(tmp_path: Path) -> None:
    backup_root = tmp_path / ".rgen-backups"
    session = backup_root / "20240101_120000"
    session.mkdir(parents=True)
    (session / "routing-map.json").write_text('{"restored": true}')

    engine = BackupEngine(backup_root)
    restore_dir = tmp_path / "restored"
    restored = engine.restore("20240101_120000", restore_dir)

    assert len(restored) == 1
    assert (restore_dir / "routing-map.json").read_text() == '{"restored": true}'


def test_restore_raises_for_missing_session(tmp_path: Path) -> None:
    engine = BackupEngine(tmp_path / ".rgen-backups")
    with pytest.raises(FileNotFoundError, match="Backup session not found"):
        engine.restore("99991231_235959", tmp_path / "out")
