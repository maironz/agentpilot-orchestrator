"""Lifecycle cleanup for AgentPilot workspace directories.

Provides:
- Log rotation: keep the N most-recent ``.log`` files in ``.agentpilot/logs/``
- Cache cap: delete files beyond a max total size in ``.agentpilot/cache/``
- Tmp cleanup: delete all files in ``.agentpilot/tmp/``
- ``cleanup_on_exit``: register a :mod:`atexit` hook that runs when
  ``cleanup_on_exit=True`` in ``.agentpilot/config.yaml``

Usage
-----
from rgen.lifecycle import LifecycleManager

mgr = LifecycleManager(project_root=target)
mgr.rotate_logs(keep=20)
mgr.cap_cache(max_bytes=50 * 1024 * 1024)  # 50 MB
mgr.clean_tmp()

# Or auto-register atexit hook based on config:
mgr.register_atexit_if_configured()
"""

from __future__ import annotations

import atexit
import logging
import shutil
from pathlib import Path
from typing import Union

from rgen.config import load as _load_cfg

logger = logging.getLogger(__name__)

# Defaults
_DEFAULT_LOG_KEEP = 20
_DEFAULT_CACHE_MAX_BYTES = 50 * 1024 * 1024  # 50 MB

_LOGS_REL = Path(".agentpilot") / "logs"
_CACHE_REL = Path(".agentpilot") / "cache"
_TMP_REL = Path(".agentpilot") / "tmp"


class LifecycleManager:
    """Manages cleanup of AgentPilot runtime directories.

    Parameters
    ----------
    project_root:
        Root of the target project.  Defaults to ``Path(".")``.
    log_keep:
        Maximum number of ``.log`` files to keep in ``logs/`` during
        rotation.  Oldest files (by mtime) are deleted first.
    cache_max_bytes:
        Maximum total size of files in ``cache/`` before eviction.
        Oldest files (by mtime) are deleted first.
    """

    def __init__(
        self,
        project_root: Union[Path, str, None] = None,
        log_keep: int = _DEFAULT_LOG_KEEP,
        cache_max_bytes: int = _DEFAULT_CACHE_MAX_BYTES,
    ) -> None:
        self._root = Path(project_root).resolve() if project_root else Path(".").resolve()
        self.log_keep = log_keep
        self.cache_max_bytes = cache_max_bytes

        self.logs_dir: Path = self._root / _LOGS_REL
        self.cache_dir: Path = self._root / _CACHE_REL
        self.tmp_dir: Path = self._root / _TMP_REL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rotate_logs(self, keep: int | None = None) -> list[Path]:
        """Delete oldest ``.log`` files from ``logs/``, keeping *keep* files.

        Returns the list of deleted paths.
        """
        n = keep if keep is not None else self.log_keep
        if not self.logs_dir.is_dir():
            return []

        log_files = sorted(
            self.logs_dir.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
        )
        to_delete = log_files[: max(0, len(log_files) - n)]
        deleted: list[Path] = []
        for f in to_delete:
            try:
                f.unlink()
                deleted.append(f)
                logger.debug("lifecycle: deleted log %s", f.name)
            except OSError as exc:
                logger.warning("lifecycle: could not delete log %s — %s", f, exc)
        return deleted

    def cap_cache(self, max_bytes: int | None = None) -> list[Path]:
        """Evict oldest files from ``cache/`` until total size ≤ *max_bytes*.

        Returns the list of deleted paths.
        """
        limit = max_bytes if max_bytes is not None else self.cache_max_bytes
        if not self.cache_dir.is_dir():
            return []

        files = sorted(
            (f for f in self.cache_dir.rglob("*") if f.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
        total = sum(f.stat().st_size for f in files)
        deleted: list[Path] = []
        for f in files:
            if total <= limit:
                break
            try:
                size = f.stat().st_size
                f.unlink()
                total -= size
                deleted.append(f)
                logger.debug("lifecycle: evicted cache file %s (%d bytes)", f.name, size)
            except OSError as exc:
                logger.warning("lifecycle: could not evict cache file %s — %s", f, exc)
        return deleted

    def clean_tmp(self) -> int:
        """Delete all files (not directories) inside ``tmp/``.

        Returns the count of deleted items.
        """
        if not self.tmp_dir.is_dir():
            return 0

        count = 0
        for item in list(self.tmp_dir.iterdir()):
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    count += 1
                logger.debug("lifecycle: cleaned tmp item %s", item.name)
            except OSError as exc:
                logger.warning("lifecycle: could not clean tmp item %s — %s", item, exc)
        return count

    def run_all(
        self,
        log_keep: int | None = None,
        cache_max_bytes: int | None = None,
    ) -> dict[str, object]:
        """Run all cleanup operations and return a summary dict."""
        deleted_logs = self.rotate_logs(keep=log_keep)
        evicted_cache = self.cap_cache(max_bytes=cache_max_bytes)
        tmp_count = self.clean_tmp()
        return {
            "deleted_logs": deleted_logs,
            "evicted_cache": evicted_cache,
            "tmp_cleaned": tmp_count,
        }

    # ------------------------------------------------------------------
    # atexit integration
    # ------------------------------------------------------------------

    def register_atexit_if_configured(self) -> bool:
        """Register :meth:`run_all` as an atexit hook if ``cleanup_on_exit=True``.

        Reads ``cleanup_on_exit`` from ``.agentpilot/config.yaml``.
        Returns *True* when the hook is registered, *False* otherwise.
        """
        cfg = _load_cfg(self._root)
        if cfg.cleanup_on_exit:
            atexit.register(self.run_all)
            logger.debug("lifecycle: cleanup_on_exit registered")
            return True
        return False


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def get_manager(
    project_root: Union[Path, str, None] = None,
    **kwargs: object,
) -> LifecycleManager:
    """Return a :class:`LifecycleManager` for *project_root*."""
    return LifecycleManager(project_root=project_root, **kwargs)
