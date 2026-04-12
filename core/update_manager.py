from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_version() -> str:
    try:
        return metadata.version("agentpilot-orchestrator")
    except metadata.PackageNotFoundError:
        return "unknown"


def _repo_root() -> Path:
    # core/update_manager.py -> repo root is parent of core/
    return Path(__file__).resolve().parent.parent


def _git(args: list[str], cwd: Path, timeout: int = 20) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return 127, "", "git executable not found"
    except Exception as exc:
        return 1, "", str(exc)

    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _parse_ahead_behind(counts: str) -> tuple[int, int]:
    ahead_str, behind_str = counts.split()
    return int(ahead_str), int(behind_str)


def _remote_default_branch(root: Path) -> str:
    code, out, _ = _git(["remote", "show", "origin"], root, timeout=30)
    if code == 0:
        for line in out.splitlines():
            stripped = line.strip()
            if stripped.startswith("HEAD branch:"):
                branch = stripped.split(":", 1)[1].strip()
                if branch:
                    return branch

    code, out, _ = _git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], root)
    if code == 0 and out.startswith("origin/") and len(out) > len("origin/"):
        return out.split("/", 1)[1]
    return "main"


def get_update_status(refresh: bool = False) -> dict:
    """
    Get update status using git metadata. This does not auto-update.

    Args:
        refresh: if True, runs a lightweight fetch before comparing with origin

    Returns:
        JSON-serializable status dict.
    """
    root = _repo_root()
    result = {
        "checked_at": _utc_now(),
        "current_version": _project_version(),
        "update_policy": "manual-only",
        "auto_update_enabled": False,
        "source": "git-origin",
    }

    if not (root / ".git").exists():
        result.update(
            {
                "status": "unsupported",
                "message": "No .git directory found: update checks require a git clone.",
            }
        )
        return result

    code, branch, err = _git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if code != 0:
        result.update(
            {
                "status": "error",
                "message": "Unable to detect current git branch.",
                "error": err,
            }
        )
        return result

    code, head, err = _git(["rev-parse", "--short", "HEAD"], root)
    if code != 0:
        result.update(
            {
                "status": "error",
                "message": "Unable to detect current git revision.",
                "error": err,
            }
        )
        return result

    default_branch = _remote_default_branch(root)

    if refresh:
        _git(["fetch", "--quiet", "origin"], root, timeout=30)

    upstream = f"origin/{branch}"
    code, counts, err = _git(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"], root)
    if code != 0:
        result.update(
            {
                "status": "unknown",
                "branch": branch,
                "local_head": head,
                "message": "Upstream comparison unavailable. Ensure origin remote and network access.",
                "error": err,
            }
        )
        return result

    try:
        ahead, behind = _parse_ahead_behind(counts)
    except Exception:
        result.update(
            {
                "status": "error",
                "branch": branch,
                "local_head": head,
                "message": "Unexpected git comparison output.",
                "raw": counts,
            }
        )
        return result

    default_ahead = 0
    default_behind = 0
    default_err = None
    default_ref = f"origin/{default_branch}"
    code, default_counts, err = _git(["rev-list", "--left-right", "--count", f"HEAD...{default_ref}"], root)
    if code == 0:
        try:
            default_ahead, default_behind = _parse_ahead_behind(default_counts)
        except Exception:
            default_err = f"Unexpected git comparison output for {default_ref}: {default_counts}"
    else:
        default_err = err

    update_available = behind > 0 or default_behind > 0
    status = "outdated" if update_available else "up-to-date"

    if behind > 0:
        manual_update_command = "git pull --ff-only"
    elif default_behind > 0 and branch != default_branch:
        manual_update_command = f"git fetch origin ; git merge --ff-only origin/{default_branch}"
    else:
        manual_update_command = "git pull --ff-only"

    result.update(
        {
            "status": status,
            "branch": branch,
            "default_branch": default_branch,
            "local_head": head,
            "ahead_commits": ahead,
            "behind_commits": behind,
            "ahead_default_commits": default_ahead,
            "behind_default_commits": default_behind,
            "update_available": update_available,
            "manual_update_command": manual_update_command,
        }
    )
    if default_err:
        result["default_branch_compare_error"] = default_err
    return result


def manual_update(confirm: bool = False) -> dict:
    """
    Run a manual fast-forward update. Auto-update remains disabled.

    Args:
        confirm: must be True to execute update.

    Returns:
        JSON-serializable result dict.
    """
    if not confirm:
        return {
            "updated": False,
            "status": "confirmation_required",
            "message": "Set confirm=true to run manual update.",
            "update_policy": "manual-only",
        }

    root = _repo_root()
    status = get_update_status(refresh=True)
    if status.get("status") in {"unsupported", "error"}:
        return {
            "updated": False,
            "status": "blocked",
            "message": "Cannot update because update status could not be determined.",
            "details": status,
        }

    code, dirty_out, dirty_err = _git(["status", "--porcelain"], root)
    if code != 0:
        return {
            "updated": False,
            "status": "error",
            "message": "Failed to check working tree state.",
            "error": dirty_err,
        }

    if dirty_out.strip():
        return {
            "updated": False,
            "status": "blocked",
            "message": "Working tree has local changes. Commit or stash changes before update.",
        }

    if not status.get("update_available", False):
        return {
            "updated": False,
            "status": "up-to-date",
            "message": "No update available.",
            "details": status,
        }

    if status.get("behind_commits", 0) == 0 and status.get("behind_default_commits", 0) > 0:
        return {
            "updated": False,
            "status": "needs_default_branch_sync",
            "message": (
                "Current branch is up-to-date with its upstream but behind the default branch. "
                "Sync with origin/default branch manually."
            ),
            "details": status,
        }

    code, pull_out, pull_err = _git(["pull", "--ff-only"], root, timeout=60)
    if code != 0:
        return {
            "updated": False,
            "status": "error",
            "message": "Manual update failed.",
            "error": pull_err,
            "output": pull_out,
        }

    post = get_update_status(refresh=False)
    return {
        "updated": True,
        "status": "updated",
        "message": "Repository updated successfully.",
        "output": pull_out,
        "details": post,
    }
