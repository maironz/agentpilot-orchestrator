"""Read policy for sensitive files in AgentPilot workspace.

Prevents accidental reads of ``.env``, ``secrets.*``, ``*.pem``, ``*.key``
and similar sensitive files outside of explicitly approved paths.

Usage
-----
from rgen.read_policy import ReadPolicy, ReadPolicyViolation

rp = ReadPolicy(project_root=target)
content = rp.read_file(path)          # raises/warns if path is sensitive
safe = rp.is_sensitive(path)          # True when path matches a sensitive pattern
"""

from __future__ import annotations

import logging
import re
import warnings
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sensitive filename patterns (case-insensitive match against the final name)
# ---------------------------------------------------------------------------
_SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\.env$", re.IGNORECASE),
    re.compile(r"^\.env\..+", re.IGNORECASE),          # .env.local, .env.prod …
    re.compile(r"^secrets(\..+)?$", re.IGNORECASE),    # secrets, secrets.yaml …
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"\.key$", re.IGNORECASE),
    re.compile(r"\.pfx$", re.IGNORECASE),
    re.compile(r"\.p12$", re.IGNORECASE),
    re.compile(r"^credentials(\..+)?$", re.IGNORECASE),
    re.compile(r"^\.netrc$", re.IGNORECASE),
    re.compile(r"^id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$", re.IGNORECASE),
]


class ReadPolicyViolation(RuntimeError):
    """Raised in strict mode when a sensitive file read is attempted."""


class ReadPolicy:
    """Enforce read policy on sensitive files.

    Parameters
    ----------
    project_root:
        Root of the target project.
    strict:
        When *True*, reading a sensitive file raises :class:`ReadPolicyViolation`.
        When *False* (default) a warning is emitted and the read proceeds.
    allowed_paths:
        Explicit set of absolute paths that are always allowed regardless of
        the pattern check (e.g. a known safe ``.env.example``).
    """

    def __init__(
        self,
        project_root: Union[Path, str, None] = None,
        strict: bool = False,
        allowed_paths: list[Union[Path, str]] | None = None,
    ) -> None:
        self._root = Path(project_root).resolve() if project_root else Path(".").resolve()
        self._strict = strict
        self._allowed: set[str] = set()
        for p in allowed_paths or []:
            self._allowed.add(str(Path(p).resolve()))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_sensitive(self, path: Union[Path, str]) -> bool:
        """Return *True* if *path* matches a sensitive filename pattern."""
        name = Path(path).name
        return any(pat.search(name) for pat in _SENSITIVE_PATTERNS)

    def check_read(self, path: Union[Path, str]) -> None:
        """Raise or warn if *path* is a sensitive file not in the allow-list.

        Does nothing when the file is not sensitive or is explicitly allowed.
        """
        p = Path(path).resolve()
        if str(p) in self._allowed:
            return
        if not self.is_sensitive(p):
            return

        msg = (
            f"read_policy: sensitive file read — path={p} "
            f"(add to allowed_paths to suppress)"
        )
        logger.warning("read_policy: sensitive read — path=%s", p)
        if self._strict:
            raise ReadPolicyViolation(msg)
        warnings.warn(msg, stacklevel=3)

    def read_file(
        self,
        path: Union[Path, str],
        encoding: str = "utf-8",
    ) -> str:
        """Read and return the text content of *path* after the policy check.

        In strict mode, raises :class:`ReadPolicyViolation` for sensitive
        files.  In non-strict mode, emits a warning and still returns the
        content.
        """
        self.check_read(path)
        return Path(path).read_text(encoding=encoding)

    def read_bytes(self, path: Union[Path, str]) -> bytes:
        """Read and return the binary content of *path* after the policy check."""
        self.check_read(path)
        return Path(path).read_bytes()

    def allow(self, path: Union[Path, str]) -> None:
        """Permanently allow *path* (e.g. a known-safe ``.env.example``)."""
        self._allowed.add(str(Path(path).resolve()))

    def deny(self, path: Union[Path, str]) -> None:
        """Remove *path* from the explicit allow-list."""
        self._allowed.discard(str(Path(path).resolve()))

    @property
    def sensitive_patterns(self) -> list[str]:
        """Return the active pattern list as strings (for inspection/testing)."""
        return [p.pattern for p in _SENSITIVE_PATTERNS]
