#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
    except Exception:
        return 1, ""
    return proc.returncode, f"{proc.stdout}\n{proc.stderr}".strip()


def _process_has_mcp_server() -> bool:
    if os.name == "nt":
        code, output = _run([
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'mcp_server.py' } | "
            "Select-Object -ExpandProperty ProcessId",
        ])
        return code == 0 and bool(output.strip())

    # POSIX fallback
    code, output = _run(["ps", "-ef"])
    if code != 0:
        return False
    return "mcp_server.py" in output


def _latest_vscode_mcp_state() -> Optional[str]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None

    logs_root = Path(appdata) / "Code" / "logs"
    if not logs_root.exists():
        return None

    candidates = sorted(
        logs_root.rglob("mcpServer.mcp.config.ws*.agentpilot-orchestrator.log"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None

    latest = candidates[0]
    try:
        lines = latest.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        if "Stato connessione: In esecuzione" in line:
            return "Active"
        if "Stato connessione: Arrestato" in line:
            return "Inactive"

    return None


def _resolve_target_dir(target_dir: Path | None = None) -> Path:
    if target_dir is not None:
        return target_dir.resolve()

    env_target_dir = os.environ.get("AGENTPILOT_TARGET_DIR")
    if env_target_dir:
        return Path(env_target_dir).expanduser().resolve()

    return Path(__file__).resolve().parent.parent


def get_mcp_status(target_dir: Path | None = None) -> dict:
    repo_root = _resolve_target_dir(target_dir)
    workspace_cfg = repo_root / ".vscode" / "mcp.json"
    configured = workspace_cfg.exists()
    log_state = _latest_vscode_mcp_state()
    active = log_state == "Active" or _process_has_mcp_server()
    status = "Active" if active else "Standby" if configured else "Inactive"

    payload = {
        "mcp": status,
        "configured": configured,
        "workspace_config": str(workspace_cfg.relative_to(repo_root)).replace('\\', '/'),
        "source": "vscode-log" if log_state is not None else "process-scan",
        "target_dir": str(repo_root),
    }
    if status == "Standby":
        payload["note"] = "Server starts on first VS Code tool call."
    return payload


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report VS Code MCP configuration and runtime status.")
    parser.add_argument("--target-dir", type=Path, help="Workspace root whose .vscode/mcp.json should be checked.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    json.dump(get_mcp_status(args.target_dir), sys.stdout, ensure_ascii=False)
