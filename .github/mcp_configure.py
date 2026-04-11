#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VSCODE_DIR = REPO_ROOT / ".vscode"
MCP_JSON = VSCODE_DIR / "mcp.json"
SERVER_NAME = "agentpilot-orchestrator"
SERVER_CONFIG = {
    "type": "stdio",
    "command": "${workspaceFolder}/.venv/Scripts/agentpilot-mcp.exe",
    "cwd": "${workspaceFolder}",
}


def _load_config() -> dict:
    if not MCP_JSON.exists():
        return {"servers": {}}
    return json.loads(MCP_JSON.read_text(encoding="utf-8"))


def _save_config(config: dict) -> None:
    VSCODE_DIR.mkdir(parents=True, exist_ok=True)
    MCP_JSON.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def enable() -> dict:
    config = _load_config()
    servers = config.setdefault("servers", {})
    servers[SERVER_NAME] = SERVER_CONFIG
    _save_config(config)
    return {
        "status": "enabled",
        "server": SERVER_NAME,
        "config_file": ".vscode/mcp.json",
    }


def disable() -> dict:
    config = _load_config()
    servers = config.setdefault("servers", {})
    removed = servers.pop(SERVER_NAME, None) is not None
    _save_config(config)
    return {
        "status": "disabled" if removed else "already-disabled",
        "server": SERVER_NAME,
        "config_file": ".vscode/mcp.json",
    }


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"enable", "disable"}:
        print("Usage: python .github/mcp_configure.py [enable|disable]", file=sys.stderr)
        return 1

    action = sys.argv[1]
    result = enable() if action == "enable" else disable()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
