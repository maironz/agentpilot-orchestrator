"""Filesystem policy layer for AgentPilot workspace hygiene.

All writes performed by rgen and core modules MUST go through this module.
Writes outside whitelisted paths produce a warning (default) or raise an
error (strict mode / ``--fs-strict``).

Whitelisted root: ``.agentpilot/`` relative to the project root.
Exception: ``.github/`` writes are allowed only when explicitly requested
and are always logged as a warning.

Usage
-----
from rgen.fs_policy import FSPolicy

policy = FSPolicy(project_root=Path("."), strict=False)
policy.write_file(policy.DIR_MAP["state"] / "session.json", content)
policy.write_atomic(policy.DIR_MAP["cache"] / "version.json", data)
"""

from __future__ import annotations

import logging
import os
import platform
import tempfile
import warnings
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Central directory map — all modules must use these keys instead of
# hardcoding paths.  Relative to the project root passed at construction.
# ---------------------------------------------------------------------------
_DIR_MAP_TEMPLATE: dict[str, str] = {
    "state": ".agentpilot/runtime/state",
    "logs": ".agentpilot/logs",
    "cache": ".agentpilot/cache",
    "tmp": ".agentpilot/tmp",
    "reports": ".agentpilot/reports",
    "backups": ".agentpilot/backups",
    "artifacts": ".agentpilot/artifacts",
}

_IS_WINDOWS = platform.system() == "Windows"


def _normalize(p: Path) -> str:
    """Return a canonical string for whitelist comparison."""
    s = str(p.resolve())
    return s.lower() if _IS_WINDOWS else s


class PolicyViolation(RuntimeError):
    """Raised in strict mode when a write falls outside the whitelist."""


class FSPolicy:
    """Enforce write path policy for AgentPilot operations.

    Parameters
    ----------
    project_root:
        Absolute path to the project root.  All path checks are relative to
        this directory.
    strict:
        When *True*, any policy violation raises :class:`PolicyViolation`
        and no write is performed.  When *False* (default) a warning is
        emitted and execution continues.
    allow_github_write:
        Permit writes to ``.github/`` — always logged regardless of this
        flag.
    """

    def __init__(
        self,
        project_root: Union[Path, str, None] = None,
        strict: bool = False,
        allow_github_write: bool = False,
    ) -> None:
        self._root = Path(project_root).resolve() if project_root else Path(".").resolve()
        self._strict = strict
        self._allow_github_write = allow_github_write

        # Build the concrete DIR_MAP bound to this root.
        self.DIR_MAP: dict[str, Path] = {
            key: self._root / rel for key, rel in _DIR_MAP_TEMPLATE.items()
        }

        self._allowed_root = self._root / ".agentpilot"
        self._github_root = self._root / ".github"

    @classmethod
    def from_config(cls, project_root: Union[Path, str, None] = None) -> "FSPolicy":
        """Build an :class:`FSPolicy` instance from ``.agentpilot/config.yaml``.

        Falls back to safe defaults when the config file is absent or PyYAML
        is not installed.
        """
        from rgen.config import load as _load_cfg  # lazy to avoid circular import

        cfg = _load_cfg(project_root)
        return cls(
            project_root=project_root,
            strict=cfg.fs_strict,
            allow_github_write=cfg.allow_github_write,
        )

    # ------------------------------------------------------------------
    # Public write API
    # ------------------------------------------------------------------

    def write_file(self, path: Union[Path, str], content: str, encoding: str = "utf-8") -> None:
        """Write *content* to *path* after whitelist check.

        Raises :class:`PolicyViolation` in strict mode on violations.
        """
        p = self._resolve_and_check(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Re-validate after mkdir (anti-TOCTOU)
        self._resolve_and_check(path)
        p.write_text(content, encoding=encoding)

    def write_bytes_file(self, path: Union[Path, str], data: bytes) -> None:
        """Write binary *data* to *path* after whitelist check."""
        p = self._resolve_and_check(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._resolve_and_check(path)
        p.write_bytes(data)

    def write_atomic(self, path: Union[Path, str], content: str, encoding: str = "utf-8") -> None:
        """Atomically write *content* to *path* (write-then-rename).

        Prevents partial writes on crash/interrupt.  Use for ``state/`` and
        ``cache/`` files.
        """
        p = self._resolve_and_check(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._resolve_and_check(path)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, prefix=".tmp-", suffix=p.suffix)
        try:
            with os.fdopen(tmp_fd, "w", encoding=encoding) as fh:
                fh.write(content)
            Path(tmp_path).replace(p)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def write_best_effort(self, path: Union[Path, str], content: str, encoding: str = "utf-8") -> None:
        """Write *content* to *path*; on any error log a warning and continue.

        Use for ``logs/`` and ``tmp/`` where a write failure must not abort
        the current run.
        """
        try:
            self.write_file(path, content, encoding=encoding)
        except (PolicyViolation, OSError, PermissionError) as exc:
            logger.warning("fs_policy: best_effort write failed — path=%s error=%s", path, exc)

    def mkdir(self, path: Union[Path, str]) -> None:
        """Create directory *path* after whitelist check."""
        p = self._resolve_and_check(path)
        p.mkdir(parents=True, exist_ok=True)

    def delete(self, path: Union[Path, str]) -> None:
        """Delete file *path* after whitelist check."""
        p = self._resolve_and_check(path)
        if p.is_file() or p.is_symlink():
            p.unlink(missing_ok=True)
        # Directories are not deleted via this API to avoid accidental rm -rf.

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_and_check(self, path: Union[Path, str]) -> Path:
        """Resolve *path* and verify it is inside an allowed root.

        Returns the resolved :class:`~pathlib.Path` on success.
        Emits warning or raises :class:`PolicyViolation` on violation.

        Symlinks are followed: only the fully-resolved path is checked,
        never the original (anti-traversal).
        """
        p = Path(path)
        # If relative, anchor to project root.
        if not p.is_absolute():
            p = self._root / p
        resolved = p.resolve()

        if self._is_allowed(resolved):
            return resolved

        if self._is_github(resolved):
            import inspect
            caller = _caller_name(inspect.stack())
            logger.warning(
                "fs_policy: github_write — path=%s caller=%s allow_github_write=%s",
                resolved,
                caller,
                self._allow_github_write,
            )
            if self._allow_github_write:
                return resolved

        msg = (
            f"fs_policy: write outside whitelist — path={resolved} "
            f"(allowed root: {self._allowed_root})"
        )
        if self._strict:
            raise PolicyViolation(msg)
        warnings.warn(msg, stacklevel=4)
        return resolved

    def _is_allowed(self, resolved: Path) -> bool:
        norm_path = _normalize(resolved)
        norm_root = _normalize(self._allowed_root)
        return norm_path.startswith(norm_root + os.sep) or norm_path == norm_root

    def _is_github(self, resolved: Path) -> bool:
        norm_path = _normalize(resolved)
        norm_root = _normalize(self._github_root)
        return norm_path.startswith(norm_root + os.sep) or norm_path == norm_root


# ---------------------------------------------------------------------------
# Module-level convenience: lazily initialised default policy instance.
# ---------------------------------------------------------------------------
_default: FSPolicy | None = None


def get_default(project_root: Union[Path, str, None] = None, strict: bool = False) -> FSPolicy:
    """Return (or create) the module-level default :class:`FSPolicy` instance.

    Loads ``fs_strict`` and ``allow_github_write`` from
    ``.agentpilot/config.yaml`` when constructing for the first time.
    The *strict* parameter acts as an override (higher precedence).
    """
    global _default
    if _default is None or project_root is not None:
        _default = FSPolicy.from_config(project_root=project_root)
        if strict:
            _default._strict = True
    return _default


# ---------------------------------------------------------------------------
# Internal utility
# ---------------------------------------------------------------------------

def _caller_name(stack: list) -> str:
    """Best-effort: return '<file>:<func>' of the first non-policy caller."""
    for frame_info in stack[1:]:
        fname = frame_info.filename or ""
        if "fs_policy" not in fname:
            func = frame_info.function or "?"
            short = Path(fname).name
            return f"{short}:{func}"
    return "unknown"
