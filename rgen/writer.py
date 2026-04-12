"""Writer -- writes generated files to disk with backup integration."""

from __future__ import annotations

import shutil
from pathlib import Path

from rgen.backup import BackupEngine
from rgen.models import GenerationResult


class Writer:
    """Writes adapter output to disk, backing up existing files first.

    Args:
        core_dir: Directory containing invariant core files (router.py, etc.)
                  that are copied into every generated project.
        backup_dir_name: Name of the backup directory created inside
                         ``target_dir/.github/`` (default: ``.rgen-backups``).
    """

    CORE_FILES = (
        "router.py",
        "router_audit.py",
        "router_planner.py",
        "interventions.py",
        "mcp_server.py",
        "requirements.txt",
    )

    def __init__(
        self,
        core_dir: Path,
        backup_dir_name: str = ".rgen-backups",
    ) -> None:
        self._core_dir = Path(core_dir)
        self._backup_dir_name = backup_dir_name

    def generate(self, files: dict[str, str], target_dir: Path) -> GenerationResult:
        """Runs the full pipeline: write generated files + copy core files.

        Args:
            files: ``{relative_path: content}`` from :class:`~rgen.adapter.Adapter`.
            target_dir: Project root where files are written.

        Returns:
            :class:`~rgen.models.GenerationResult` with aggregated stats.
        """
        target_dir = Path(target_dir)
        backup_engine = BackupEngine(
            target_dir / ".github" / self._backup_dir_name,
            project_root=target_dir,
            command="generate",
            target=str(target_dir),
        )

        r1 = self.write_all(files, target_dir, backup_engine)
        r2 = self.copy_core_files(target_dir, backup_engine)

        return GenerationResult(
            success=not r1.errors and not r2.errors,
            files_written=r1.files_written + r2.files_written,
            files_skipped=r1.files_skipped + r2.files_skipped,
            errors=r1.errors + r2.errors,
            backup_dir=backup_engine.session_dir if (r1.files_written or r2.files_written) else None,
        )

    def write_all(
        self,
        files: dict[str, str],
        target_dir: Path,
        backup_engine: BackupEngine | None = None,
    ) -> GenerationResult:
        """Writes ``{relative_path: content}`` files under ``target_dir``.

        Creates missing parent directories. Backs up existing files before
        overwriting. Continues on error, recording each failure.

        Args:
            files: Dict of relative paths to file contents.
            target_dir: Root directory for the write.
            backup_engine: Optional engine; created lazily if omitted.

        Returns:
            :class:`~rgen.models.GenerationResult`.
        """
        target_dir = Path(target_dir)
        if backup_engine is None:
            backup_engine = BackupEngine(
                target_dir / ".github" / self._backup_dir_name,
                project_root=target_dir,
                command="write_all",
                target=str(target_dir),
            )

        result = GenerationResult(success=True)
        for rel_path, content in files.items():
            dest = target_dir / rel_path
            try:
                existed_before = dest.exists()
                backup_engine.backup_if_exists(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                backup_engine.record_written_file(dest, existed_before=existed_before)
                result.files_written.append(dest)
            except Exception as exc:
                result.errors.append(f"{rel_path}: {exc}")

        if result.errors:
            result.success = False
        return result

    def copy_core_files(
        self,
        target_dir: Path,
        backup_engine: BackupEngine | None = None,
    ) -> GenerationResult:
        """Copies core invariant files from ``core_dir`` into ``target_dir/.github/``.

        Args:
            target_dir: Project root; files land in ``.github/``.
            backup_engine: Optional engine; created lazily if omitted.

        Returns:
            :class:`~rgen.models.GenerationResult`.
        """
        target_dir = Path(target_dir)
        github_dir = target_dir / ".github"
        if backup_engine is None:
            backup_engine = BackupEngine(
                github_dir / self._backup_dir_name,
                project_root=target_dir,
                command="copy_core_files",
                target=str(target_dir),
            )

        result = GenerationResult(success=True)
        for name in self.CORE_FILES:
            src = self._core_dir / name
            if not src.exists():
                result.files_skipped.append(src)
                continue
            dest = github_dir / name
            try:
                existed_before = dest.exists()
                backup_engine.backup_if_exists(dest)
                github_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                backup_engine.record_written_file(dest, existed_before=existed_before)
                result.files_written.append(dest)
            except Exception as exc:
                result.errors.append(f"{name}: {exc}")

        if result.errors:
            result.success = False
        return result
