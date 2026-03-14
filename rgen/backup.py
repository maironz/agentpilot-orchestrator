"""Backup engine -- backs up existing files before overwriting."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


class BackupEngine:
    """Creates timestamped backups of files before they are overwritten.

    The backup directory is created lazily on the first actual backup.

    Args:
        base_dir: Root directory where backups are stored.
                  A timestamped subdirectory is created inside it per session.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)
        self._session_dir: Path | None = None

    @property
    def session_dir(self) -> Path:
        """Returns (and lazily creates) the timestamped session backup dir."""
        if self._session_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._session_dir = self._base_dir / timestamp
            self._session_dir.mkdir(parents=True, exist_ok=True)
        return self._session_dir

    def backup_if_exists(self, target: Path) -> Path | None:
        """Copies *target* into the session backup dir if it exists.

        Args:
            target: File to back up.

        Returns:
            Path to the backup copy, or None if the file did not exist.
        """
        target = Path(target)
        if not target.exists():
            return None
        dest = self.session_dir / target.name
        shutil.copy2(target, dest)
        return dest

    def list_backups(self) -> list[Path]:
        """Returns all timestamped session dirs under base_dir, sorted newest first."""
        if not self._base_dir.exists():
            return []
        return sorted(
            (d for d in self._base_dir.iterdir() if d.is_dir()),
            reverse=True,
        )

    def restore(self, timestamp: str, target_dir: Path) -> list[Path]:
        """Copies all files from backup session *timestamp* into *target_dir*.

        Args:
            timestamp: Name of the session backup dir (e.g. '20240101_120000').
            target_dir: Directory where files are restored.

        Returns:
            List of restored file paths.

        Raises:
            FileNotFoundError: If the requested backup session does not exist.
        """
        session = self._base_dir / timestamp
        if not session.exists():
            raise FileNotFoundError(f"Backup session not found: {session}")
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        restored: list[Path] = []
        for src in session.iterdir():
            if src.is_file():
                dest = target_dir / src.name
                shutil.copy2(src, dest)
                restored.append(dest)
        return restored
