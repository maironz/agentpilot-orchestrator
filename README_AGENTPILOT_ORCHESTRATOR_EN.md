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
[![Tests](https://img.shields.io/badge/tests-223%2F223-brightgreen?logo=pytest&logoColor=white)](tests/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies](https://img.shields.io/badge/core-stdlib%20only%20%2B%20rich-orange)](pyproject.toml)
[![Works with](https://img.shields.io/badge/works%20with-Copilot%20%7C%20Claude%20%7C%20Cursor-blueviolet)](README.md)

</div>
</div>

---

# AgentPilot Orchestrator

Production-ready AI routing and orchestration for multi-agent workflows.

AgentPilot Orchestrator helps teams route each request to the right specialist context, reduce token waste, and keep AI outputs consistent across engineering domains.

## Why AgentPilot Orchestrator

- Route each request to the right agent context
- Reduce irrelevant context and token usage
- Keep routing decisions explainable (`scenario`, `confidence`, `priority`)
- Add MCP-native integration for assistant ecosystems
- Track interventions and improve routing over time

## Core Capabilities

- Semantic scenario routing (`direct`, `follow-up`, `subagent`)
- Confidence scoring and ambiguity handling
- Agent-specific context loading
- Intervention memory with searchable history
- MCP server tools for native assistant integration
- Scenario suggestion workflow from historical interventions

## Architecture at a Glance

- Router engine: scenario scoring, confidence, fallback, ambiguity
- Knowledge base: domain scenarios, keywords, expert profiles
- Memory layer: SQLite/FTS-based intervention history
- MCP layer: tool interface for assistants and orchestrators

## Quick Start

### 1) Clone and install

```bash
git clone https://github.com/<your-org>/agentpilot-orchestrator.git
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

# Optional: bootstrap Anthropic skills (only if missing)
bash .github/skills.sh setup-anthropic-skills

# Optional: force refresh skills
bash .github/skills.sh setup-anthropic-skills --force
```

Bootstrap prerequisites:

- `bash`
- `npx` (preferred) or `git` (fallback)

Supported variables:

- `ANTHROPIC_SKILLS_SLUG` (default: `anthropics/skills`)
- `ANTHROPIC_SKILLS_REPO` (default: `https://github.com/anthropics/skills.git`)
- `ANTHROPIC_SKILLS_REF` (tag/branch for git fallback)
- `ANTHROPIC_SKILLS_CLI_TIMEOUT` (seconds, default: `90`)

Quick troubleshooting:

- If `npx` does not install skills, the script automatically falls back to git.
- On unstable networks, reduce timeout: `ANTHROPIC_SKILLS_CLI_TIMEOUT=30`.

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

## MCP Integration

AgentPilot Orchestrator includes an MCP server to expose routing and memory as native tools.

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

## Roadmap Focus

Short term:

- MCP runtime hardening and contract tests
- Open-core boundary definition (public vs private assets)
- Historical audit trail and selective rollback

Mid term:

- Cost estimator by scenario and model profile
- Pattern marketplace and secure pattern distribution

## Open-Core Direction

AgentPilot Orchestrator is moving to an open-core model:

- Public core: routing engine, MCP baseline, docs, examples
- Private extensions: advanced governance, premium integrations, proprietary playbooks

## Security and Know-How Protection

- No hardcoded credentials in public assets
- Redacted infrastructure examples and placeholders only
- Release checklist includes know-how exposure review

## Launch Checklist (Before First Post)

- [ ] README finalized in English
- [ ] Product name and repository naming aligned
- [ ] MCP quickstart verified in a clean environment
- [ ] Public/private asset boundary documented
- [ ] Minimal demo and screenshots ready
- [ ] First technical post links to reproducible quickstart

## Contributing

Contributions are welcome.

Before opening a PR:

- run tests
- keep docs and plans aligned
- avoid exposing environment-specific operational details

## License

MIT
