"""Gitignore wizard — checks and proposes ``.agentpilot/`` exclusion rules.

Recommended ``.gitignore`` entries added by this module
--------------------------------------------------------
# AgentPilot workspace
.agentpilot/

Optionally, when ``track_artifacts=True``, a negation rule keeps the
``artifacts/`` folder tracked::

    !.agentpilot/artifacts/

Usage (non-interactive, e.g. CLI --init)
-----------------------------------------
from rgen.gitignore_wizard import run_wizard
run_wizard(project_root=target, track_artifacts=False, interactive=False)

Usage (interactive prompt)
--------------------------
from rgen.gitignore_wizard import run_wizard
run_wizard(project_root=target)
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Union

_COMMENT = "# AgentPilot workspace"
_ENTRY_MAIN = ".agentpilot/"
_ENTRY_ARTIFACTS_KEEP = "!.agentpilot/artifacts/"


def _entry_in_content(entry: str, content: str) -> bool:
    """Return True if *entry* matches a line in *content* (exact, stripped)."""
    return any(line.strip() == entry for line in content.splitlines())


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def is_agentpilot_ignored(project_root: Union[Path, str, None] = None) -> bool:
    """Return *True* if ``.agentpilot/`` is already in ``.gitignore``."""
    root = Path(project_root).resolve() if project_root else Path(".").resolve()
    gi = root / ".gitignore"
    if not gi.is_file():
        return False
    return _entry_in_content(_ENTRY_MAIN, gi.read_text(encoding="utf-8", errors="replace"))


def missing_entries(
    project_root: Union[Path, str, None] = None,
    track_artifacts: bool = False,
) -> list[str]:
    """Return the list of ``.gitignore`` entries not yet present in the file.

    An empty list means no action is required.
    """
    root = Path(project_root).resolve() if project_root else Path(".").resolve()
    gi = root / ".gitignore"
    existing = gi.read_text(encoding="utf-8", errors="replace") if gi.is_file() else ""

    result: list[str] = []
    if not _entry_in_content(_ENTRY_MAIN, existing):
        result.append(_ENTRY_MAIN)

    if track_artifacts and not _entry_in_content(_ENTRY_ARTIFACTS_KEEP, existing):
        result.append(_ENTRY_ARTIFACTS_KEEP)

    return result


def apply_entries(
    entries: list[str],
    project_root: Union[Path, str, None] = None,
) -> None:
    """Append *entries* to ``.gitignore`` (creates the file if absent).

    A comment header is prepended before the block so entries are easy to
    locate.  Already-present entries are skipped (idempotent).
    """
    if not entries:
        return

    root = Path(project_root).resolve() if project_root else Path(".").resolve()
    gi = root / ".gitignore"
    existing = gi.read_text(encoding="utf-8", errors="replace") if gi.is_file() else ""

    to_add = [e for e in entries if not _entry_in_content(e, existing)]
    if not to_add:
        return

    sep = "" if (not existing or existing.endswith("\n")) else "\n"
    block = _COMMENT + "\n" + "\n".join(to_add) + "\n"
    gi.write_text(existing + sep + "\n" + block, encoding="utf-8")  # fs-policy: ok


# ---------------------------------------------------------------------------
# High-level wizard
# ---------------------------------------------------------------------------


def run_wizard(
    project_root: Union[Path, str, None] = None,
    track_artifacts: bool = False,
    interactive: bool = True,
) -> bool:
    """Check ``.gitignore`` and propose/apply missing AgentPilot entries.

    Parameters
    ----------
    project_root:
        Root of the target project.  Defaults to ``Path(".")``.
    track_artifacts:
        When *True*, also propose ``!.agentpilot/artifacts/`` so that the
        artifacts folder is tracked by git.
    interactive:
        When *True* (default), prompt the user before applying changes.
        When *False*, apply silently (use in CLI ``--init`` flows).

    Returns
    -------
    bool
        *True* if entries are applied or were already present; *False* if the
        user declined and entries were **not** applied.
    """
    needed = missing_entries(project_root=project_root, track_artifacts=track_artifacts)
    if not needed:
        return True

    if not interactive:
        apply_entries(needed, project_root=project_root)
        return True

    print("\n[AgentPilot] The following entries are missing from .gitignore:")
    for entry in needed:
        print(f"  {entry}")

    try:
        ans = input("Add them now? [Y/n] ").strip().lower()
    except EOFError:
        ans = "n"

    if ans in ("", "y", "yes"):
        apply_entries(needed, project_root=project_root)
        print("[AgentPilot] .gitignore updated.")
        return True

    warnings.warn(
        "agentpilot: .agentpilot/ is not excluded from git — "
        "runtime state, logs and cache may be committed accidentally.",
        stacklevel=2,
    )
    return False
