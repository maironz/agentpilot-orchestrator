"""Tests for writer -- Steps 5+6."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from rgen.backup import BackupEngine
from rgen.writer import Writer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def core_dir(tmp_path: Path) -> Path:
    """Minimal core/ directory with a few stub files."""
    d = tmp_path / "core"
    d.mkdir()
    (d / "router.py").write_text("# router stub")
    (d / "interventions.py").write_text("# interventions stub")
    (d / "mcp_server.py").write_text("# mcp stub")
    return d


@pytest.fixture
def target_dir(tmp_path: Path) -> Path:
    return tmp_path / "my-project"


@pytest.fixture
def sample_files() -> dict[str, str]:
    return {
        ".github/routing-map.json": json.dumps({"scenario_a": {"agent": "dev"}}),
        ".github/esperti/esperto_developer.md": "# Developer",
        ".github/copilot-instructions.md": "# Copilot",
    }


# ---------------------------------------------------------------------------
# write_all
# ---------------------------------------------------------------------------

def test_write_all_creates_files(core_dir: Path, target_dir: Path, sample_files: dict) -> None:
    writer = Writer(core_dir)
    result = writer.write_all(sample_files, target_dir)

    assert result.success
    assert len(result.files_written) == 3
    assert (target_dir / ".github" / "routing-map.json").exists()
    assert (target_dir / ".github" / "esperti" / "esperto_developer.md").exists()


def test_write_all_creates_missing_parent_dirs(core_dir: Path, target_dir: Path) -> None:
    writer = Writer(core_dir)
    result = writer.write_all(
        {".github/deep/nested/file.md": "content"},
        target_dir,
    )
    assert (target_dir / ".github" / "deep" / "nested" / "file.md").exists()


def test_write_all_backs_up_existing_file(core_dir: Path, target_dir: Path) -> None:
    existing = target_dir / ".github" / "routing-map.json"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old content")

    writer = Writer(core_dir)
    writer.write_all({".github/routing-map.json": "new content"}, target_dir)

    assert (target_dir / ".github" / "routing-map.json").read_text() == "new content"
    backup_root = target_dir / ".github" / ".rgen-backups"
    backups = list(backup_root.iterdir())
    assert len(backups) == 1
    assert (backups[0] / "routing-map.json").read_text() == "old content"


def test_write_all_returns_error_on_write_failure(core_dir: Path, target_dir: Path) -> None:
    writer = Writer(core_dir)
    # Write a file and then make the directory read-only to simulate failure
    # Instead, use a path that is a file (not a directory) as parent
    bad_path = target_dir / ".github"
    bad_path.mkdir(parents=True, exist_ok=True)
    (bad_path / "blocking-file").write_text("I am a file")
    result = writer.write_all(
        {".github/blocking-file/child.json": "content"},
        target_dir,
    )
    assert not result.success
    assert len(result.errors) == 1


def test_write_all_continues_after_single_error(core_dir: Path, target_dir: Path) -> None:
    """Files after a failed write should still be written."""
    bad_path = target_dir / ".github"
    bad_path.mkdir(parents=True, exist_ok=True)
    (bad_path / "blocker").write_text("file")

    files = {
        ".github/blocker/child.json": "bad",
        ".github/ok.md": "good",
    }
    writer = Writer(core_dir)
    result = writer.write_all(files, target_dir)

    assert not result.success
    assert len(result.errors) == 1
    assert (target_dir / ".github" / "ok.md").exists()


# ---------------------------------------------------------------------------
# copy_core_files
# ---------------------------------------------------------------------------

def test_copy_core_files_copies_known_files(core_dir: Path, target_dir: Path) -> None:
    writer = Writer(core_dir)
    result = writer.copy_core_files(target_dir)

    assert result.success
    assert (target_dir / ".github" / "router.py").exists()
    assert (target_dir / ".github" / "interventions.py").exists()
    assert (target_dir / ".github" / "mcp_server.py").exists()


def test_copy_core_files_skips_missing_core_files(core_dir: Path, target_dir: Path) -> None:
    (core_dir / "router.py").unlink()
    writer = Writer(core_dir)
    result = writer.copy_core_files(target_dir)

    assert result.success
    assert any("router.py" in str(s) for s in result.files_skipped)
    assert not (target_dir / ".github" / "router.py").exists()


def test_copy_core_files_backs_up_existing(core_dir: Path, target_dir: Path) -> None:
    existing = target_dir / ".github" / "router.py"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("# old router")

    writer = Writer(core_dir)
    writer.copy_core_files(target_dir)

    assert existing.read_text() == "# router stub"
    backup_root = target_dir / ".github" / ".rgen-backups"
    sessions = list(backup_root.iterdir())
    assert len(sessions) == 1
    assert (sessions[0] / "router.py").read_text() == "# old router"


# ---------------------------------------------------------------------------
# generate (full pipeline)
# ---------------------------------------------------------------------------

def test_generate_writes_all_and_copies_core(
    core_dir: Path, target_dir: Path, sample_files: dict
) -> None:
    writer = Writer(core_dir)
    result = writer.generate(sample_files, target_dir)

    assert result.success
    # Generated files
    assert (target_dir / ".github" / "routing-map.json").exists()
    assert (target_dir / ".github" / "copilot-instructions.md").exists()
    # Core files
    assert (target_dir / ".github" / "router.py").exists()
    assert (target_dir / ".github" / "interventions.py").exists()


def test_generate_returns_combined_file_count(
    core_dir: Path, target_dir: Path, sample_files: dict
) -> None:
    writer = Writer(core_dir)
    result = writer.generate(sample_files, target_dir)
    # 3 generated + 3 core (router, interventions, mcp) + potentially skipped others
    assert len(result.files_written) >= 6
