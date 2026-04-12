from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from active_option_sync import apply_active_option_update, get_active_option_status


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _banner_update_label(status: dict) -> str:
    if status.get("update_available"):
        return "Need Update"
    return "ok"


def _banner_update_value(status: dict, report_path: str) -> str:
    if status.get("update_available"):
        return f"[Need Update]({report_path})"
    return "ok"


def _banner_update_link_target(status: dict, report_path: str) -> str | None:
    if status.get("update_available"):
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
    auto_result = apply_active_option_update(confirm=True) if args.auto else None

    report_path = Path(args.output)
    report_data = {
        "generated_at": _utc_now(),
        "update_label": _banner_update_label(status),
        "update_value": _banner_update_value(status, str(report_path).replace("\\", "/")),
        "update_link_target": _banner_update_link_target(status, str(report_path).replace("\\", "/")),
        "status": status,
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
