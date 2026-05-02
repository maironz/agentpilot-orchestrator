"""Backup engine -- backs up existing files before overwriting."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


class BackupEngine:
    """Creates timestamped backups of files before they are overwritten.

    The backup directory is created lazily on the first actual backup.

    Args:
        base_dir: Root directory where backups are stored.
        project_root: Project root used to persist relative paths in metadata.
        command: Optional command label persisted in generation metadata.
        target: Optional target path persisted in generation metadata.
        pattern: Optional pattern id persisted in generation metadata.
        language: Optional language persisted in generation metadata.
    """

    INDEX_FILE = "index.json"
    METADATA_FILE = "metadata.json"

    def __init__(
        self,
        base_dir: Path,
        project_root: Path | None = None,
        command: str = "",
        target: str = "",
        pattern: str = "",
        language: str = "",
    ) -> None:
        self._base_dir = Path(base_dir)
        self._project_root = Path(project_root) if project_root else self._infer_project_root(self._base_dir)
        self._command = command
        self._target = target
        self._pattern = pattern
        self._language = language
        self._session_dir: Path | None = None
        self._session_metadata: dict[str, object] | None = None

    @staticmethod
    def _infer_project_root(base_dir: Path) -> Path:
        if base_dir.parent.name == ".github":
            return base_dir.parent.parent
        return base_dir.parent

    @property
    def session_dir(self) -> Path:
        """Returns (and lazily creates) the timestamped session backup dir."""
        if self._session_dir is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            self._session_dir = self._base_dir / timestamp
            self._session_dir.mkdir(parents=True, exist_ok=True)
        return self._session_dir

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _relative_path(self, target: Path) -> Path:
        try:
            return target.resolve().relative_to(self._project_root.resolve())
        except ValueError:
            return Path(target.name)

    def _new_metadata(self, generation_id: str) -> dict[str, object]:
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "generation_id": generation_id,
            "created_at": created_at,
            "command": self._command,
            "target": self._target,
            "pattern": self._pattern,
            "language": self._language,
            "written_files": [],
            "updated_files": [],
            "checksum_map": {},
            "outcome": "success",
        }

    def _load_index(self) -> list[dict[str, object]]:
        index_path = self._base_dir / self.INDEX_FILE
        if not index_path.exists():
            return []
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _write_index(self) -> None:
        metadata = self._ensure_session_metadata()
        summary = {
            "generation_id": metadata["generation_id"],
            "created_at": metadata["created_at"],
            "command": metadata.get("command", ""),
            "target": metadata.get("target", ""),
            "pattern": metadata.get("pattern", ""),
            "language": metadata.get("language", ""),
            "written_count": len(metadata.get("written_files", [])),
            "updated_count": len(metadata.get("updated_files", [])),
            "outcome": metadata.get("outcome", "success"),
        }
        items = [
            item
            for item in self._load_index()
            if item.get("generation_id") != summary["generation_id"]
        ]
        items.append(summary)
        items.sort(key=lambda item: str(item.get("generation_id", "")), reverse=True)
        index_path = self._base_dir / self.INDEX_FILE
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")  # fs-policy: ok

    def _persist_metadata(self) -> None:
        metadata = self._session_metadata
        if metadata is None:
            return
        metadata_path = self.session_dir / self.METADATA_FILE
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")  # fs-policy: ok
        self._write_index()

    def _ensure_session_metadata(self) -> dict[str, object]:
        if self._session_metadata is None:
            self._session_metadata = self._new_metadata(self.session_dir.name)
            self._persist_metadata()
        return self._session_metadata

    def backup_if_exists(self, target: Path) -> Path | None:
        """Copies *target* into the session backup dir if it exists."""
        target = Path(target)
        if not target.exists():
            return None
        dest = self.session_dir / self._relative_path(target)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, dest)
        return dest

    def record_written_file(self, target: Path, existed_before: bool) -> None:
        """Track files written by the current generation session."""
        target = Path(target)
        metadata = self._ensure_session_metadata()
        rel_path = self._relative_path(target).as_posix()
        bucket = "updated_files" if existed_before else "written_files"
        if rel_path not in metadata[bucket]:
            metadata[bucket].append(rel_path)
        metadata["checksum_map"][rel_path] = self._checksum(target)
        self._persist_metadata()

    def list_backups(self) -> list[Path]:
        """Returns all timestamped session dirs under base_dir, sorted newest first."""
        if not self._base_dir.exists():
            return []
        return sorted(
            (d for d in self._base_dir.iterdir() if d.is_dir()),
            reverse=True,
        )

    def get_generation(self, generation_id: str) -> dict[str, object]:
        """Return structured metadata for one generation."""
        session = self._base_dir / generation_id
        if not session.exists():
            raise FileNotFoundError(f"Backup session not found: {session}")

        metadata_path = session / self.METADATA_FILE
        if metadata_path.exists():
            return json.loads(metadata_path.read_text(encoding="utf-8"))

        updated_files: list[str] = []
        for path in session.rglob("*"):
            if path.is_file():
                updated_files.append(path.relative_to(session).as_posix())
        return {
            "generation_id": generation_id,
            "created_at": generation_id,
            "command": "",
            "target": "",
            "pattern": "",
            "language": "",
            "written_files": [],
            "updated_files": sorted(updated_files),
            "checksum_map": {},
            "outcome": "success",
        }

    def history(self, limit: int | None = None) -> list[dict[str, object]]:
        """Return known generations, newest first."""
        index = self._load_index()
        if index:
            return index[:limit] if limit is not None else index

        history: list[dict[str, object]] = []
        for session in self.list_backups():
            item = self.get_generation(session.name)
            history.append(
                {
                    "generation_id": item["generation_id"],
                    "created_at": item.get("created_at", item["generation_id"]),
                    "command": item.get("command", ""),
                    "target": item.get("target", ""),
                    "pattern": item.get("pattern", ""),
                    "language": item.get("language", ""),
                    "written_count": len(item.get("written_files", [])),
                    "updated_count": len(item.get("updated_files", [])),
                    "outcome": item.get("outcome", "success"),
                }
            )
        return history[:limit] if limit is not None else history

    def describe_generation(self, generation_id: str) -> list[dict[str, str]]:
        """Describe files touched by a generation and current state."""
        item = self.get_generation(generation_id)
        checksum_map = item.get("checksum_map", {})
        changes: list[dict[str, str]] = []

        for rel_path in item.get("written_files", []):
            changes.append(
                {
                    "path": rel_path,
                    "change": "created",
                    "current_state": self._current_state(rel_path, checksum_map),
                }
            )

        for rel_path in item.get("updated_files", []):
            changes.append(
                {
                    "path": rel_path,
                    "change": "updated",
                    "current_state": self._current_state(rel_path, checksum_map),
                }
            )
        return changes

    def _current_state(self, rel_path: str, checksum_map: dict[str, str]) -> str:
        current = self._project_root / Path(rel_path)
        if not current.exists():
            return "deleted"
        expected = checksum_map.get(rel_path)
        if not expected:
            return "unknown"
        if self._checksum(current) == expected:
            return "unchanged"
        return "modified"

    def rollback(self, generation_id: str, force: bool = False) -> dict[str, list[str]]:
        """Rollback one generation preserving manual edits by default."""
        item = self.get_generation(generation_id)
        session = self._base_dir / generation_id
        checksum_map = item.get("checksum_map", {})
        report = {"restored": [], "removed": [], "skipped_manual": [], "missing": []}

        for rel_path in item.get("updated_files", []):
            current = self._project_root / Path(rel_path)
            backup = session / Path(rel_path)
            expected = checksum_map.get(rel_path)
            if current.exists() and expected and not force and self._checksum(current) != expected:
                report["skipped_manual"].append(rel_path)
                continue
            if not backup.exists():
                report["missing"].append(rel_path)
                continue
            current.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, current)
            report["restored"].append(rel_path)

        for rel_path in item.get("written_files", []):
            current = self._project_root / Path(rel_path)
            expected = checksum_map.get(rel_path)
            if not current.exists():
                report["missing"].append(rel_path)
                continue
            if expected and not force and self._checksum(current) != expected:
                report["skipped_manual"].append(rel_path)
                continue
            current.unlink()
            report["removed"].append(rel_path)

        return report

    def restore(self, timestamp: str, target_dir: Path) -> list[Path]:
        """Copies all files from backup session *timestamp* into *target_dir*."""
        session = self._base_dir / timestamp
        if not session.exists():
            raise FileNotFoundError(f"Backup session not found: {session}")
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        restored: list[Path] = []
        for src in session.rglob("*"):
            if src.is_file() and src.name != self.METADATA_FILE:
                dest = target_dir / src.relative_to(session)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                restored.append(dest)
        return restored
