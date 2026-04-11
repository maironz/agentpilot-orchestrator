#!/usr/bin/env python3
from __future__ import annotations

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


def get_mcp_status() -> dict:
    repo_root = Path(__file__).resolve().parent.parent
    workspace_cfg = repo_root / ".vscode" / "mcp.json"
    configured = workspace_cfg.exists()
    log_state = _latest_vscode_mcp_state()
    active = log_state == "Active" or _process_has_mcp_server()

    return {
        "mcp": "Active" if active else "Inactive",
        "configured": configured,
        "workspace_config": str(workspace_cfg.relative_to(repo_root)).replace('\\', '/'),
        "source": "vscode-log" if log_state is not None else "process-scan",
    }


if __name__ == "__main__":
    json.dump(get_mcp_status(), sys.stdout, ensure_ascii=False)
