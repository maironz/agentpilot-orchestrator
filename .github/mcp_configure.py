#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_NAME = "agentpilot-orchestrator"
SERVER_CONFIG = {
    "type": "stdio",
    "command": "${workspaceFolder}/.venv/Scripts/agentpilot-mcp.exe",
    "cwd": "${workspaceFolder}",
}


def _resolve_target_dir(target_dir: Path | None = None) -> Path:
    if target_dir is not None:
        return target_dir.resolve()

    env_target_dir = os.environ.get("AGENTPILOT_TARGET_DIR")
    if env_target_dir:
        return Path(env_target_dir).expanduser().resolve()

    return DEFAULT_REPO_ROOT


def _config_paths(target_dir: Path | None = None) -> tuple[Path, Path]:
    root_dir = _resolve_target_dir(target_dir)
    vscode_dir = root_dir / ".vscode"
    return root_dir, vscode_dir / "mcp.json"


def _load_config(target_dir: Path | None = None) -> dict:
    _, mcp_json = _config_paths(target_dir)
    if not mcp_json.exists():
        return {"servers": {}}
    return json.loads(mcp_json.read_text(encoding="utf-8"))


def _save_config(config: dict, target_dir: Path | None = None) -> Path:
    root_dir, mcp_json = _config_paths(target_dir)
    (root_dir / ".vscode").mkdir(parents=True, exist_ok=True)
    mcp_json.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return mcp_json


def enable(target_dir: Path | None = None) -> dict:
    root_dir, mcp_json = _config_paths(target_dir)
    config = _load_config(root_dir)
    servers = config.setdefault("servers", {})
    servers[SERVER_NAME] = SERVER_CONFIG
    _save_config(config, root_dir)
    return {
        "status": "enabled",
        "server": SERVER_NAME,
        "config_file": str(mcp_json.relative_to(root_dir)).replace('\\', '/'),
        "target_dir": str(root_dir),
    }


def disable(target_dir: Path | None = None) -> dict:
    root_dir, mcp_json = _config_paths(target_dir)
    config = _load_config(root_dir)
    servers = config.setdefault("servers", {})
    removed = servers.pop(SERVER_NAME, None) is not None
    _save_config(config, root_dir)
    return {
        "status": "disabled" if removed else "already-disabled",
        "server": SERVER_NAME,
        "config_file": str(mcp_json.relative_to(root_dir)).replace('\\', '/'),
        "target_dir": str(root_dir),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enable or disable VS Code MCP workspace configuration.")
    parser.add_argument("action", choices=("enable", "disable"))
    parser.add_argument("--target-dir", type=Path, help="Workspace root where .vscode/mcp.json should be managed.")
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    result = enable(args.target_dir) if args.action == "enable" else disable(args.target_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
