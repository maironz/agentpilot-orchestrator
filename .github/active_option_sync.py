from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _candidate_pairs(root: Path) -> list[tuple[Path, Path]]:
    core_dir = root / "core"
    active_dir = root / ".github"
    pairs: list[tuple[Path, Path]] = []

    if not core_dir.exists() or not active_dir.exists():
        return pairs

    for src in sorted(core_dir.iterdir()):
        if not src.is_file() or src.name == "__init__.py":
            continue
        dest = active_dir / src.name
        if dest.exists() and dest.is_file():
            pairs.append((src, dest))
    return pairs


def get_active_option_status() -> dict:
    root = _repo_root()
    pairs = _candidate_pairs(root)

    if not pairs:
        return {
            "checked_at": _utc_now(),
            "source": "active-option",
            "status": "unsupported",
            "message": "No overlapping files found between core/ and .github/.",
            "update_available": False,
            "manual_update_command": "python .github/active_option_sync.py --apply",
        }

    drift_files: list[str] = []
    for src, dest in pairs:
        if _sha256(src) != _sha256(dest):
            drift_files.append(dest.relative_to(root).as_posix())

    update_available = bool(drift_files)
    return {
        "checked_at": _utc_now(),
        "source": "active-option",
        "scope": "core->.github",
        "status": "outdated" if update_available else "up-to-date",
        "update_available": update_available,
        "compared_files": len(pairs),
        "drift_files": drift_files,
        "drift_count": len(drift_files),
        "manual_update_command": "python .github/active_option_sync.py --apply",
    }


def apply_active_option_update(confirm: bool = False) -> dict:
    if not confirm:
        return {
            "updated": False,
            "status": "confirmation_required",
            "message": "Set confirm=true to apply active option update.",
        }

    root = _repo_root()
    status = get_active_option_status()
    if status.get("status") == "unsupported":
        return {
            "updated": False,
            "status": "unsupported",
            "message": status.get("message", "Unsupported active option sync."),
            "details": status,
        }

    drift_files = status.get("drift_files", [])
    if not drift_files:
        return {
            "updated": False,
            "status": "up-to-date",
            "message": "Active option already aligned with core files.",
            "details": status,
        }

    copied: list[str] = []
    for rel in drift_files:
        dest = root / rel
        src = root / "core" / dest.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(rel)

    post = get_active_option_status()
    return {
        "updated": True,
        "status": "updated",
        "message": f"Active option updated for {len(copied)} files.",
        "files_updated": copied,
        "details": post,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync active option files from core/ to .github/")
    parser.add_argument("--apply", action="store_true", help="Apply sync now")
    args = parser.parse_args()

    if args.apply:
        payload = apply_active_option_update(confirm=True)
    else:
        payload = get_active_option_status()

    json.dump(payload, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
