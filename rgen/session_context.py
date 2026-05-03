"""Session context for AgentPilot workspace isolation.

Each rgen run that touches runtime state receives an isolated directory::

    .agentpilot/runtime/state/<session_id>/

The session ID is a short UUID (8 hex chars) generated once per process and
cached as a module-level singleton.  It can also be seeded explicitly (e.g.
in tests or from a CLI ``--session`` flag).

Usage
-----
from rgen.session_context import SessionContext, get_active

# Acquire a session (creates the directory)
with SessionContext(project_root=target) as ctx:
    state_dir = ctx.state_dir   # Path(".agentpilot/runtime/state/<id>/")
    ctx.policy.write_file(state_dir / "run.json", json_content)

# Or use the module-level singleton (lazy-created)
ctx = get_active(project_root=target)
"""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Union

from rgen.fs_policy import FSPolicy

_STATE_REL = Path(".agentpilot") / "runtime" / "state"

# Module-level singleton — created on first call to get_active()
_active: "SessionContext | None" = None


# ---------------------------------------------------------------------------
# SessionContext
# ---------------------------------------------------------------------------


class SessionContext:
    """Isolated runtime-state directory for one rgen session.

    Parameters
    ----------
    project_root:
        Root of the target project.
    session_id:
        Explicit session identifier.  Defaults to a freshly generated short
        UUID (8 hex chars).
    policy:
        :class:`~rgen.fs_policy.FSPolicy` to use.  When *None* a
        :meth:`~rgen.fs_policy.FSPolicy.from_config` instance is created.

    Attributes
    ----------
    session_id : str
        The active session identifier.
    state_dir : Path
        Absolute path to the session-scoped state directory
        (``.agentpilot/runtime/state/<session_id>/``).
    policy : FSPolicy
        The policy instance — its whitelist has been extended to allow
        writes to :attr:`state_dir`.
    """

    def __init__(
        self,
        project_root: Union[Path, str, None] = None,
        session_id: str | None = None,
        policy: FSPolicy | None = None,
    ) -> None:
        root = Path(project_root).resolve() if project_root else Path(".").resolve()
        self.session_id: str = session_id or _new_id()
        self.state_dir: Path = (root / _STATE_REL / self.session_id).resolve()

        if policy is None:
            policy = FSPolicy.from_config(project_root=root)
        self.policy = policy
        # Register this session's directory as an extra allowed path.
        self.policy.add_allowed_path(self.state_dir)

        self._root = root
        self._started_at: datetime | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Create the session directory and write a ``session.json`` manifest."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._started_at = datetime.now(tz=timezone.utc)
        manifest = {
            "session_id": self.session_id,
            "started_at": self._started_at.isoformat(),
            "project_root": str(self._root),
        }
        (self.state_dir / "session.json").write_text(  # fs-policy: ok
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

    def stop(self) -> None:
        """Write a ``session_end.json`` marker (best-effort; never raises)."""
        if not self.state_dir.is_dir():
            return
        try:
            ended_at = datetime.now(tz=timezone.utc)
            marker = {
                "session_id": self.session_id,
                "ended_at": ended_at.isoformat(),
                "started_at": self._started_at.isoformat() if self._started_at else None,
            }
            (self.state_dir / "session_end.json").write_text(  # fs-policy: ok
                json.dumps(marker, indent=2), encoding="utf-8"
            )
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Context-manager protocol
    # ------------------------------------------------------------------

    def __enter__(self) -> "SessionContext":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def get_active(
    project_root: Union[Path, str, None] = None,
    session_id: str | None = None,
) -> "SessionContext":
    """Return (or create) the module-level active :class:`SessionContext`.

    Subsequent calls with the same *project_root* return the cached instance.
    Pass a new *project_root* to reset.
    """
    global _active
    if _active is None or project_root is not None:
        _active = SessionContext(project_root=project_root, session_id=session_id)
        _active.start()
    return _active


def reset_active() -> None:
    """Close and discard the module-level active session (mainly for tests)."""
    global _active
    if _active is not None:
        _active.stop()
        _active = None


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _new_id() -> str:
    """Return a short random session ID (8 lowercase hex chars)."""
    return uuid.uuid4().hex[:8]
