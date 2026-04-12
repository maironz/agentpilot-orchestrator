<div>
<div align="Left">

```
    _                    _   ____  _ _       _
   / \   __ _  ___ _ __ | |_|  _ \(_) | ___ | |_ 
  / _ \ / _` |/ _ \ '_ \| __| |_) | | |/ _ \| __|
 / ___ \ (_| |  __/ | | | |_|  __/| | | (_) | |_ 
/_/   \_\__, |\___|_| |_|\__|_|   |_|_|\___/ \__|
        |___/

        ___  ____   ____ _   _ _____ ____ _____ ____      _  _____ ___  ____
       / _ \|  _ \ / ___| | | | ____/ ___|_   _|  _ \    / \|_   _/ _ \|  _ \
      | | | | |_) | |   | |_| |  _| \___ \ | | | |_) |  / _ \ | || | | | |_) |
      | |_| |  _ <| |___|  _  | |___ ___) || | |  _ <  / ___ \| || |_| |  _ <
       \___/|_| \_\\____|_| |_|_____|____/ |_| |_| \_\/_/   \_\_| \___/|_| \_\
```
</div>
<div align="Center">
**Automatically generate a semantic AI routing system for any project.**

[![Python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-259%2F259-brightgreen?logo=pytest&logoColor=white)](tests/)
[![Dependencies](https://img.shields.io/badge/core-stdlib%20only%20%2B%20rich-orange)](pyproject.toml)
[![Works with](https://img.shields.io/badge/works%20with-Copilot%20%7C%20Claude%20%7C%20Cursor-blueviolet)](README.md)

</div>
</div>

---

# AgentPilot Orchestrator

Production-ready AI routing and orchestration for multi-agent workflows.

AgentPilot Orchestrator helps teams route each request to the right specialist context, reduce token waste, and keep AI outputs consistent across engineering domains.

> Built for teams that want explainable routing, cleaner prompts, and an MCP-ready interface without building orchestration glue from scratch.

Current release: `v0.4.0`. See `.github/RELEASE_NOTES.md` for release history and migration context.

**From an internal routing experiment to a reusable orchestration layer for AI-heavy engineering workflows.**

## At a Glance

| You need | AgentPilot Orchestrator gives you |
|---|---|
| Better request-to-expert matching | Scenario-based routing with confidence and priority |
| Less prompt sprawl | Targeted context loading instead of generic mega-prompts |
| Traceable assistant behavior | Auditable routing decisions and intervention history |
| Assistant ecosystem integration | MCP tools for routing, memory, and coverage checks |

## What It Does

AgentPilot Orchestrator gives engineering teams a routing layer for AI workflows.

- It classifies each request into a scenario.
- It selects the most appropriate specialist context.
- It exposes routing and memory through MCP tools.
- It records interventions so routing can be improved over time.

In short: it reduces noisy prompting and turns assistant usage into a repeatable operational system.

## Project Origin

AgentPilot Orchestrator started as a practical response to a familiar problem: once multiple assistants, prompt styles, and specialist contexts enter the same engineering workflow, quality becomes inconsistent fast.

The project was originally shaped to solve that operational gap with something more rigorous than a folder of prompts and more lightweight than a fully custom platform: a routing layer that can decide which context should answer, explain why, and improve over time.

What began as an internal orchestration system for structured engineering support evolved into a reusable open-core toolkit for teams that want assistant workflows to feel deliberate, inspectable, and production-aware.

## Why AgentPilot Orchestrator

- Route each request to the right agent context
- Reduce irrelevant context and token usage
- Keep routing decisions explainable (`scenario`, `confidence`, `priority`)
- Add MCP-native integration for assistant ecosystems
- Track interventions and improve routing over time
- Turn ad-hoc prompting into a repeatable engineering capability

## Core Capabilities

- Semantic scenario routing (`direct`, `follow-up`, `subagent`)
- Confidence scoring and ambiguity handling
- Agent-specific context loading
- Intervention memory with searchable history
- MCP server tools for native assistant integration
- Scenario suggestion workflow from historical interventions

## Skills vs Agents

Both are first-class building blocks, but they solve different problems.

| Component | Primary role | Scope | Typical trigger |
|---|---|---|---|
| Skills | Reusable operating playbooks | Task-level behavior | "How should this task be executed?" |
| Agents | Specialized decision and response profiles | Domain-level ownership | "Who should handle this request?" |

In practice:

- Use **Agents** to route requests to the right domain context (backend, devops, docs, orchestration).
- Use **Skills** to standardize *how* the selected agent executes the task (checks, workflows, quality gates).
- Combine both for reliable outcomes: **Agent = who**, **Skill = how**.

> Tip: if routing is correct but output quality is inconsistent, improve the Skill. If quality is good but the wrong domain is selected, tune the Agent routing map.

## How It Works

1. Input request arrives through CLI or MCP tool call.
2. Router evaluates scenarios using keyword sets, priorities, and confidence scoring.
3. Selected agent context and relevant files are attached to the task.
4. Response is produced and the intervention can be logged for future calibration.

Operational loop:

- route
- execute
- validate
- log
- tune

## Quick Start

> Tip: if you only want to see the router in action, install dependencies, run `python .github/router.py --stats`, then try a single `--direct` query before generating anything.

### 1) Clone and install

```bash
git clone https://github.com/maironz/agentpilot-orchestrator.git
cd agentpilot-orchestrator

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -e .
pip install -r requirements-dev.txt

# Optional: MCP runtime dependencies
pip install -e ".[mcp]"
```

### Fast path

```bash
python .github/router.py --stats
python .github/router.py --direct "debug Python API timeout"
```

### 2) Generate routing assets

```bash
rgen --direct --pattern python_api --name my-app --target ./my-app
```

### 3) Run router checks

```bash
python .github/router.py --stats
python .github/router.py --audit
```

### 4) Suggest new scenarios from history

```bash
rgen --suggest-scenarios --target ./my-app --suggest-format text
```

### 5) Inspect generation history and rollback safely

```bash
rgen --history --target ./my-app
rgen --history --show-diffs --history-format json --target ./my-app
rgen --rollback --to 20260411_103000 --target ./my-app
```

### 6) Marketplace MVP (local + remote)

```bash
rgen --search-patterns python
rgen --download ./pattern-pack --install-dir ./knowledge_base
rgen --download file:///C:/tmp/pattern-pack.zip --install-dir ./knowledge_base
rgen --download owner/repo:v1.0.0 --install-dir ./knowledge_base
```

## Practical Tips

- Start with `python .github/router.py --stats` before changing routing rules.
- Use `--direct` queries as smoke tests whenever you edit scenarios or keywords.
- Keep `knowledge_base` generic in public snapshots and move operational playbooks to private space.
- Run `rgen --suggest-scenarios` only after collecting enough intervention history, otherwise the signal is weak.
- Use `rgen --history --show-diffs` before a rollback when you need to verify which files are still unchanged since generation.
- For marketplace downloads, validate pack contents locally first and keep trusted sources in a curated registry.
- Install MCP extras only when you need the server runtime; the generator itself stays lightweight.

## Example Flow

```bash
# 1. Generate assets for a target repository
rgen --direct --pattern python_api --name payments-api --target ./payments-api

# 2. Inspect routing health
python .github/router.py --stats

# 3. Probe one realistic task
python .github/router.py --direct "investigate flaky pytest failure in CI"
```

## MCP Integration

AgentPilot Orchestrator includes an MCP server to expose routing and memory as native tools.

For standard VS Code users, this repository includes a ready-to-use workspace configuration in `.vscode/mcp.json`.
Open the repo in VS Code, install the workspace package with MCP extras, trust the MCP server when prompted, and use chat tools without manual JSON copy/paste.

You can also toggle the workspace MCP configuration without editing JSON manually:

```bash
python .github/mcp_configure.py enable
python .github/mcp_configure.py disable
```

> Tip: use the MCP server when you want assistants to call routing and memory as tools; use the CLI when you are iterating locally on patterns and scenarios.

```bash
pip install -e ".[mcp]"
agentpilot-mcp
```

Current MCP tools:

- `route_query`
- `search_history`
- `log_intervention`
- `get_stats`
- `audit_coverage`
- `get_update_status` (update check, optional refresh)
- `manual_update` (manual-only update, requires confirmation)

Update policy:

- no automatic self-update
- update checks are exposed via MCP status
- manual update is optional and explicit

## MCP Does Not Replace Instructions

MCP tools and workspace instructions solve different problems.

- Instructions define behavior: workflow, formatting, constraints, checks, and team rules.
- MCP provides capabilities: callable tools for routing, memory, health checks, and update status.

In practice:

- use instructions to tell the assistant how it should work
- use MCP to give the assistant real operational tools

Best results come from using both together.

- Without instructions, the assistant may have tools but follow the wrong workflow.
- Without MCP, the assistant may follow the workflow but lack real routing and operational capabilities.

## Why Install This MCP Server

If the server works in the background, it can feel "invisible". The practical value is that your assistant stops being generic and starts behaving like an orchestrated engineering operator.

Without this MCP server, chat replies rely mostly on raw model priors and broad workspace context. With this MCP server, each request can be:

- routed to a scenario with explicit `agent`, `priority`, and `confidence`
- backed by intervention memory from similar historical tasks
- validated with health and coverage checks before you trust changes

In short: less prompt guesswork, more repeatable operations.

## 5-Minute VS Code Demo (Visible Value)

Use this flow to make the value observable to end users.

### Step 1: Configure MCP in workspace

The repository already includes a workspace MCP configuration. The standard path is:

```bash
pip install -e ".[mcp]"
python .github/mcp_configure.py enable
```

If you need to create `.vscode/mcp.json` manually, use:

```json
{
    "servers": {
        "agentpilot-orchestrator": {
            "type": "stdio",
            "command": "${workspaceFolder}/.venv/Scripts/agentpilot-mcp.exe",
            "cwd": "${workspaceFolder}"
        }
    }
}
```

Then confirm trust and start the server from VS Code MCP controls.

### Step 2: Run three prompts in chat

Prompt A (routing):

```text
Route this task: optimize slow Postgres queries in our API.
```

What users should see:

- a routed scenario payload with `agent`, `scenario`, and `priority`

Prompt B (memory):

```text
Search intervention history for: flaky pytest timeout in CI.
```

What users should see:

- prior interventions or memory stats, instead of a generic answer

Prompt C (health):

```text
Get router health stats and summarize risks.
```

What users should see:

- measurable router health fields (status, overlap, map size, thresholds)

### Step 3: Verify it is actually working

In VS Code, open MCP server output logs and confirm tool calls are executed.

If users only see plain chat text with no tool activity, MCP is not connected.

## What Changes for the User

- before: "ask and hope" workflow
- after: route, validate, execute, and log workflow

This turns AI support into an operational loop instead of a one-off prompt.

## Typical Use Cases

- Route software tasks by domain (backend, devops, docs, orchestrator)
- Standardize AI behavior in multi-team repositories
- Reduce prompt sprawl and context noise
- Build MCP-ready orchestration for coding assistants

## Why It Stands Out

- It treats routing as product infrastructure, not prompt decoration.
- It keeps decisions visible enough to debug, tune, and trust.
- It bridges local CLI workflows and MCP-native tool calling in the same system.
- It is designed for teams that want sharper assistant behavior without losing control.

## Good Fit If

- your team uses multiple coding assistants and wants consistent behavior
- you have recurring task categories that should hit different expert contexts
- you want routing decisions to stay transparent instead of heuristic black boxes
- you need a bridge between local CLI workflows and MCP-native assistant tooling

## Open-Core Direction

AgentPilot Orchestrator is moving to an open-core model:

- Public core: routing engine, MCP baseline, docs, examples
- Private extensions: advanced governance, premium integrations, proprietary playbooks

This is the part we want public: the routing engine, the contracts, the operational discipline, and the idea that AI workflows can be engineered instead of improvised.

## Security and Know-How Protection

- No hardcoded credentials in public assets
- Redacted infrastructure examples and placeholders only
- Release checklist includes know-how exposure review

## Contributing

Contributions are welcome.

Before opening a PR:

- run tests
- keep docs and plans aligned
- avoid exposing environment-specific operational details


