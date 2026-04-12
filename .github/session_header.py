from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _extract_json_blob(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in command output")
    return json.loads(text[start:])


def _extract_routing_stats_line(stats_out: str) -> str:
    for line in stats_out.splitlines():
        if line.startswith("Routing:"):
            return line.replace("Routing: ", "").strip()
    return "unknown"


def _compact_routing_stats(stats_line: str) -> str:
    scnkw = re.search(r"(\d+scn/\d+kw)", stats_line)
    overlap = re.search(r"(overlap:[0-9.]+%)", stats_line)

    if "CRIT" in stats_line:
        level = "[CRIT]"
    elif "WARN" in stats_line:
        level = "[WARN]"
    else:
        level = "[OK]"

    parts = []
    if scnkw:
        parts.append(scnkw.group(1))
    if overlap:
        parts.append(overlap.group(1))
    parts.append(level)
    return "|".join(parts)


def _budget_from_priority(priority: str | None) -> int:
    mapping = {
        "high": 20,
        "medium": 35,
        "low": 15,
    }
    return mapping.get((priority or "").lower(), 10)


def _fmt_confidence(value) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.3f}"
    return "n/a"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate full operational header in one command")
    parser.add_argument("--query", required=True, help="User query to route")
    parser.add_argument("--auto-update", action="store_true", help="Enable update_report --auto")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    py = sys.executable

    stats_cmd = [py, str(repo_root / ".github" / "router.py"), "--stats"]
    route_cmd = [py, str(repo_root / ".github" / "router.py"), "--direct", args.query]
    update_cmd = [
        py,
        str(repo_root / ".github" / "update_report.py"),
        "--output",
        ".github/UPDATE_STATUS.md",
    ]
    if args.auto_update:
        update_cmd.append("--auto")
    mcp_cmd = [py, str(repo_root / ".github" / "mcp_status.py")]

    code, stats_out, stats_err = _run(stats_cmd)
    if code != 0:
        print(f"[ERROR] router --stats failed: {stats_err or stats_out}", file=sys.stderr)
        return 2

    code, route_out, route_err = _run(route_cmd)
    if code != 0:
        print(f"[ERROR] router --direct failed: {route_err or route_out}", file=sys.stderr)
        return 2

    code, update_out, update_err = _run(update_cmd)
    if code != 0:
        print(f"[ERROR] update_report failed: {update_err or update_out}", file=sys.stderr)
        return 2

    code, mcp_out, mcp_err = _run(mcp_cmd)
    if code != 0:
        print(f"[ERROR] mcp_status failed: {mcp_err or mcp_out}", file=sys.stderr)
        return 2

    routing_stats_raw = _extract_routing_stats_line(stats_out)
    routing_stats = _compact_routing_stats(routing_stats_raw)
    routing = _extract_json_blob(route_out)
    update = json.loads(update_out)
    mcp = json.loads(mcp_out)

    model = "GPT-5.3-Codex"
    agent = routing.get("agent", "orchestratore")
    scenario = routing.get("scenario", "_fallback")
    budget = _budget_from_priority(routing.get("priority"))

    update_value = update.get("update_value") or update.get("update_label") or "ok"
    update_label = update.get("update_label") or "ok"
    confidence = _fmt_confidence(routing.get("confidence"))
    needs_clarification = bool(routing.get("needs_clarification"))
    exploration = routing.get("repo_exploration", {}).get("recommended_scope", "n/a")

    header = (
        f"🤖 {model} | Agente: {agent} | Scenario: {scenario} | Budget: ~{budget}k tok | "
        f"Routing: {routing_stats} | Update: {update_value} | MCP: {mcp.get('mcp', 'Inactive')}"
    )
    print(header)
    print(
        "Riepilogo: "
        f"confidence={confidence} | "
        f"clarify={'yes' if needs_clarification else 'no'}"
    )
    print("KPI details: [.github/kpi/KPI_METHODS.md](.github/kpi/KPI_METHODS.md)")

    if str(update_label).lower() == "need update":
        print("Update details: [.github/UPDATE_STATUS.md](.github/UPDATE_STATUS.md)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
