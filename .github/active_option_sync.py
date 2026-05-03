from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    runtime_suffixes = {".db", ".sqlite"}
    runtime_names = {"__init__.py"}

    if not core_dir.exists() or not active_dir.exists():
        return pairs

    for src in sorted(core_dir.iterdir()):
        if not src.is_file() or src.name in runtime_names or src.suffix in runtime_suffixes:
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


def _sync_with_override_zones(src: Path, dest: Path) -> bool:
    """
    Sync src → dest respecting override zone markers.
    If both files have <!-- start AgentPilot Rules -->...<!-- end AgentPilot Rules --> markers,
    replace only that section. Otherwise, fallback to flat copy.
    
    Returns True if sync was performed (either smart or flat), False if skipped due to missing markers.
    """
    if not src.exists():
        return False
    
    src_content = src.read_text(encoding='utf-8')
    dest_content = dest.read_text(encoding='utf-8') if dest.exists() else ""
    
    pattern = r'<!-- start AgentPilot Rules -->(.*?)<!-- end AgentPilot Rules -->'
    
    # Check if src has the override zone markers
    src_match = re.search(pattern, src_content, re.DOTALL)
    if not src_match:
        # No markers in source → skip (fallback safety)
        return False
    
    override_block = src_match.group(0)  # Include the markers
    
    # Check if dest has the override zone markers
    if dest_content and re.search(pattern, dest_content, re.DOTALL):
        # Both have markers → replace only the override zone
        merged = re.sub(pattern, override_block, dest_content, flags=re.DOTALL)
    elif dest_content:
        # Dest exists but has no markers → skip (safety: don't touch files without markers)
        return False
    else:
        # Dest doesn't exist → use source content as is
        merged = src_content
    
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(merged, encoding='utf-8')
    return True


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
    skipped: list[str] = []
    
    for rel in drift_files:
        dest = root / rel
        src = root / "core" / dest.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Try smart sync with override zones first (only for copilot-instructions.md)
        if src.name == "copilot-instructions.md":
            smart_synced = _sync_with_override_zones(src, dest)
            if smart_synced:
                copied.append(rel)
            else:
                # Fallback: markers missing, skip the update (safety)
                skipped.append(f"{rel} (no override zones, skipped)")
        else:
            # For other files, use flat copy
            shutil.copy2(src, dest)
            copied.append(rel)

    post = get_active_option_status()
    result = {
        "updated": True if copied else False,
        "status": "updated" if copied else "skipped",
        "message": f"Active option updated for {len(copied)} files.",
        "files_updated": copied,
        "details": post,
    }
    
    if skipped:
        result["files_skipped"] = skipped
        result["message"] += f" ({len(skipped)} files skipped due to missing override zones)"
    
    return result


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
