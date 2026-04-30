from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from active_option_sync import apply_active_option_update, get_active_option_status

_REMOTE_VERSION_URL = (
    "https://raw.githubusercontent.com/maironz/agentpilot-orchestrator/main/VERSION"
)
_VERSION_TIMEOUT = 5
_VERSION_CACHE_PATH = Path(__file__).resolve().parent / ".remote_version_cache.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _local_version() -> str:
    candidates = [
        Path(__file__).resolve().parent.parent / "VERSION",
        Path(__file__).resolve().parent / "VERSION",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    return "unknown"


def _load_cached_remote_version() -> dict | None:
    if not _VERSION_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(_VERSION_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if not data.get("remote_version"):
        return None
    return data


def _save_cached_remote_version(remote_version: str) -> None:
    payload = {
        "remote_version": remote_version,
        "cached_at": _utc_now(),
        "source_url": _REMOTE_VERSION_URL,
    }
    _VERSION_CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_remote_version_status() -> dict:
    """Confronta la versione locale con quella pubblicata su origin/main."""
    local = _local_version()
    try:
        with urllib.request.urlopen(_REMOTE_VERSION_URL, timeout=_VERSION_TIMEOUT) as resp:
            remote = resp.read().decode("utf-8").strip()
        _save_cached_remote_version(remote)
    except urllib.error.URLError as exc:
        cached = _load_cached_remote_version()
        if cached:
            cached_remote = str(cached.get("remote_version", "unknown"))
            update_available = (local != "unknown") and (cached_remote != local)
            return {
                "source": "remote-version-cache",
                "local_version": local,
                "remote_version": cached_remote,
                "update_available": update_available,
                "offline_fallback": True,
                "cached_at": cached.get("cached_at"),
                "error": str(exc),
            }
        return {
            "source": "remote-version",
            "local_version": local,
            "remote_version": "unreachable",
            "update_available": False,
            "offline_fallback": False,
            "error": str(exc),
        }
    update_available = (local != "unknown") and (remote != local)
    return {
        "source": "remote-version",
        "local_version": local,
        "remote_version": remote,
        "update_available": update_available,
        "offline_fallback": False,
    }


def _banner_update_label(status: dict, remote_status: dict | None = None) -> str:
    if (remote_status or {}).get("update_available") or status.get("update_available"):
        return "Need Update"
    return "ok"


def _banner_update_value(status: dict, report_path: str, remote_status: dict | None = None) -> str:
    if (remote_status or {}).get("update_available") or status.get("update_available"):
        return f"[Need Update]({report_path})"
    return "ok"


def _banner_update_link_target(status: dict, report_path: str, remote_status: dict | None = None) -> str | None:
    if (remote_status or {}).get("update_available") or status.get("update_available"):
        return report_path
    return None


def _format_markdown(status: dict, report_data: dict, auto_result: dict | None) -> str:
    lines: list[str] = []
    lines.append("# Update Status Report")
    lines.append("")
    lines.append(f"Generated at: {_utc_now()}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Banner label: {report_data['update_label']}")
    lines.append(f"- Banner value: {report_data['update_value']}")
    lines.append(f"- Source: {status.get('source', 'unknown')}")
    lines.append(f"- Status: {status.get('status', 'unknown')}")
    lines.append(f"- Compared files: {status.get('compared_files', '-')}")
    lines.append(f"- Drift files: {status.get('drift_count', '-')}")
    if status.get("drift_files"):
        lines.append(f"- Drift list: {', '.join(status.get('drift_files', []))}")
    lines.append(f"- Suggested manual command: {status.get('manual_update_command', '-')}")
    lines.append("")
    remote = report_data.get("remote_version_status") or {}
    lines.append("## Remote Version Check")
    lines.append(f"- Local version: {remote.get('local_version', '-')}")
    lines.append(f"- Remote version: {remote.get('remote_version', '-')}")
    if remote.get("offline_fallback"):
        lines.append("- Check mode: offline fallback (cached remote version)")
        if remote.get("cached_at"):
            lines.append(f"- Cached at: {remote.get('cached_at')}")
    if remote.get("error"):
        lines.append(f"- Remote check error: {remote['error']}")
    elif remote.get("update_available"):
        lines.append("- **A new version is available — update recommended.**")
    else:
        lines.append("- Up to date with remote.")
    lines.append("")
    lines.append("## Manual Update")
    lines.append("- Run this command to update without enabling auto mode:")
    lines.append(f"  - `{status.get('manual_update_command', 'python .github/active_option_sync.py --apply')}`")
    if status.get("drift_count", 0) > 0:
        lines.append("- This updates the active option files under `.github/` from source files in `core/`.")
    lines.append("")
    lines.append("## Auto Update")
    lines.append("- Optional auto-update is available via: `python .github/update_report.py --auto`")
    lines.append("- Auto mode calls active option sync and writes result in this report.")
    lines.append("")

    if auto_result is not None:
        lines.append("## Auto Update Result")
        lines.append(f"- updated: {auto_result.get('updated')}")
        lines.append(f"- status: {auto_result.get('status')}")
        lines.append(f"- message: {auto_result.get('message')}")
        if auto_result.get("error"):
            lines.append(f"- error: {auto_result.get('error')}")
        lines.append("")

    lines.append("## Raw Status JSON")
    lines.append("```json")
    lines.append(json.dumps(status, indent=2, ensure_ascii=False))
    lines.append("```")

    if auto_result is not None:
        lines.append("")
        lines.append("## Raw Auto Result JSON")
        lines.append("```json")
        lines.append(json.dumps(auto_result, indent=2, ensure_ascii=False))
        lines.append("```")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate update status report for header linking")
    parser.add_argument("--output", default=".github/UPDATE_STATUS.md", help="Output report path")
    parser.add_argument("--auto", action="store_true", help="Also run active option sync update")
    parser.add_argument("--no-refresh", action="store_true", help="Skip fetch before status check")
    args = parser.parse_args()

    status = get_active_option_status()
    remote_status = get_remote_version_status()
    auto_result = apply_active_option_update(confirm=True) if args.auto else None

    report_path = Path(args.output)
    report_data = {
        "generated_at": _utc_now(),
        "update_label": _banner_update_label(status, remote_status),
        "update_value": _banner_update_value(status, str(report_path).replace("\\", "/"), remote_status),
        "update_link_target": _banner_update_link_target(status, str(report_path).replace("\\", "/"), remote_status),
        "status": status,
        "remote_version_status": remote_status,
        "auto_update_requested": bool(args.auto),
        "auto_update_result": auto_result,
        "report_path": str(report_path).replace("\\", "/"),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_format_markdown(status, report_data, auto_result), encoding="utf-8")

    print(json.dumps({
        "update_label": report_data["update_label"],
        "update_value": report_data["update_value"],
        "update_link_target": report_data["update_link_target"],
        "report_path": report_data["report_path"],
        "auto_update_requested": report_data["auto_update_requested"],
        "auto_update_status": auto_result.get("status") if auto_result else None,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
