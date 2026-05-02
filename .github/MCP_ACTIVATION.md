# MCP Activation Guide

Use this file when the response header shows `MCP: Inactive` or when you want to move a configured server from `MCP: Standby` to `MCP: Active`.

## Standard User Flow

1. Open this repository in VS Code.
2. Make sure the recommended extensions are installed:
   - GitHub Copilot
   - GitHub Copilot Chat
   - Python
3. Install the MCP runtime in the workspace environment:
   - `pip install -e ".[mcp]"`
4. Enable workspace MCP configuration:
   - `python .github/mcp_configure.py enable`
   - external host project: `python .github/mcp_configure.py enable --target-dir H:/Projects/MyHostProject`
   - equivalent env var: set `AGENTPILOT_TARGET_DIR` to the host workspace root before running the command
5. Open the Command Palette with `Ctrl+Shift+P`.
6. Run `MCP: List Servers`.
7. Select `agentpilot-orchestrator`.
8. Choose `Start` or `Enable`.
9. Confirm trust when VS Code asks for permission to run the local MCP server.
10. In Chat, open `Configure Tools` or `Chat: Open Chat Customizations` and make sure `agentpilot-orchestrator` is enabled for the models you actually use.

## Important Note About Models

In practice, VS Code can require an extra manual step after server startup: the MCP server may be running, but not yet enabled for every model/chat configuration.

If the server starts correctly but tools are not being used, check that `agentpilot-orchestrator` is selected in the chat tools configuration for all relevant models.

## Easy Disable

To disable the repository MCP server from workspace configuration:

- `python .github/mcp_configure.py disable`

This removes `agentpilot-orchestrator` from `.vscode/mcp.json`.
If the server is already running in VS Code, stop or disable it from `MCP: List Servers`.

## Why This Does Not Use NPM

This project is a Python MCP server, so the standard-user path is a Python console script, not an NPM package.

- workspace config points to `agentpilot-mcp.exe` inside `.venv/Scripts/`
- the command is created by `pip install -e ".[mcp]"`
- workspace config can be enabled or disabled without hand-editing JSON paths

## Expected Result

- The server appears as running in MCP server management.
- Chat can use MCP tools from `.github/mcp_server.py`.
- `agentpilot-orchestrator` is enabled in chat tools for the models you use.
- `MCP: Standby` means `.vscode/mcp.json` is configured correctly and VS Code will start the server on first tool use.
- The status header should change from `MCP: Standby` or `MCP: Inactive` to `MCP: Active` after VS Code starts the server.

## If It Does Not Start

1. Check that `.vscode/mcp.json` contains a configured server.
2. Check that the workspace virtual environment exists at `.venv/`.
3. Install or reinstall the workspace package with MCP extras:
   - `pip install -e ".[mcp]"`
4. Check Chat tool configuration and enable `agentpilot-orchestrator` for the models you use.
5. Open the MCP server output log from VS Code and inspect the startup error.

## Host Project Note

If AgentPilot lives inside a larger repository, point MCP configuration and status checks at the host workspace root, not at the nested AgentPilot repository:

- configure: `python .github/mcp_configure.py enable --target-dir <host-root>`
- status: `python .github/mcp_status.py --target-dir <host-root>`

This ensures `.vscode/mcp.json` is read and written where VS Code actually resolves the workspace server configuration.

## Pip Notice Caveat

Some environments report non-empty stderr or even a non-zero wrapper exit when running `pip install "mcp[cli]>=1.0.0"` even though `mcp` is already installed and usable.

If your integration check shells out to pip, do not treat stderr text alone as proof of failure. Prefer a post-check such as `pip show mcp` or an import/version probe in the same environment before marking MCP setup as failed.