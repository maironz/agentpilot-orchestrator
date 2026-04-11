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
[![Tests](https://img.shields.io/badge/tests-227%2F227-brightgreen?logo=pytest&logoColor=white)](tests/)
[![Dependencies](https://img.shields.io/badge/core-stdlib%20only%20%2B%20rich-orange)](pyproject.toml)
[![Works with](https://img.shields.io/badge/works%20with-Copilot%20%7C%20Claude%20%7C%20Cursor-blueviolet)](README.md)

</div>
</div>

---

# AgentPilot Orchestrator

Production-ready AI routing and orchestration for multi-agent workflows.

AgentPilot Orchestrator helps teams route each request to the right specialist context, reduce token waste, and keep AI outputs consistent across engineering domains.

> Built for teams that want explainable routing, cleaner prompts, and an MCP-ready interface without building orchestration glue from scratch.

**From an internal routing experiment to a reusable orchestration layer for AI-heavy engineering workflows.**

## At a Glance

| You need | AgentPilot Orchestrator gives you |
|---|---|
| Better request-to-expert matching | Scenario-based routing with confidence and priority |
| Less prompt sprawl | Targeted context loading instead of generic mega-prompts |
| Traceable assistant behavior | Auditable routing decisions and intervention history |
| Assistant ecosystem integration | MCP tools for routing, memory, and coverage checks |

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

## Practical Tips

- Start with `python .github/router.py --stats` before changing routing rules.
- Use `--direct` queries as smoke tests whenever you edit scenarios or keywords.
- Keep `knowledge_base` generic in public snapshots and move operational playbooks to private space.
- Run `rgen --suggest-scenarios` only after collecting enough intervention history, otherwise the signal is weak.
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

> Tip: use the MCP server when you want assistants to call routing and memory as tools; use the CLI when you are iterating locally on patterns and scenarios.

```bash
pip install "mcp[cli]>=1.0.0"
python .github/mcp_server.py
```

Current MCP tools:

- `route_query`
- `search_history`
- `log_intervention`
- `get_stats`
- `audit_coverage`

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


