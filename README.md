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
[![CI](https://github.com/maironz/agentpilot-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/maironz/agentpilot-orchestrator/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-392-brightgreen)](tests)
[![Dependencies](https://img.shields.io/badge/core-stdlib%20only-orange)](pyproject.toml)
[![Works with](https://img.shields.io/badge/works%20with-Copilot%20%7C%20Claude%20%7C%20Cursor-blueviolet)](README.md)

</div>
</div>

---

# AgentPilot

AI Task Router for Developers.

Routes developer tasks to the best AI agent using context, certainty, and cost signals.

> Built for teams that want faster technical triage, consistent AI execution, and traceable routing decisions.

Current release is tracked in `VERSION` (synced from `pyproject.toml` on push to `main`).
See `docs/RELEASE_NOTES.md` for release history and migration context.
User-facing guides are in `docs/`; references to `.github/` in command examples point to runtime scripts, not documentation files.

**From an internal routing experiment to a reusable orchestration layer for AI-heavy engineering workflows.**

## What Problem It Solves

When teams use multiple AI models and agents for software work, three problems appear fast:

- too much manual triage before doing real work
- inconsistent handling of similar requests
- low visibility on why one route was chosen over another

AgentPilot automates that triage.

## What It Does

Given a technical request, AgentPilot:

- classifies the task type (bug fix, refactor, code generation, docs)
- selects the most suitable agent path
- applies fallback logic when certainty is low
- returns the result with a traceable decision record

In short: it behaves like a load balancer, but for AI agents.

## Demo First

Input:

```bash
python .github/router.py --direct "fix failing test in auth service"
```

Typical route output:

```text
task_type: bug_fix
agent: backend
fallback: orchestratore
certainty: 0.82
```

Then execute the task with the routed context and track the intervention.

## Supported Task Types

- Bug fixing
- Refactoring
- Code generation
- Documentation

## Project Origin

AgentPilot Orchestrator started as a practical response to a familiar problem: once multiple assistants, prompt styles, and specialist contexts enter the same engineering workflow, quality becomes inconsistent fast.

The project was originally shaped to solve that operational gap with something more rigorous than a folder of prompts and more lightweight than a fully custom platform: a routing layer that can decide which context should answer, explain why, and improve over time.

What began as an internal orchestration system for structured engineering support evolved into a reusable open-core toolkit for teams that want assistant workflows to feel deliberate, inspectable, and production-aware.

## Why AgentPilot

- Route each request to the right agent context
- Reduce irrelevant context and token usage
- Keep routing decisions explainable (`task_type`, `certainty`, `priority`)
- Add MCP-native integration for assistant ecosystems
- Track interventions and improve routing over time
- Turn ad-hoc prompting into a repeatable engineering capability

## Core Capabilities

- Semantic scenario routing (`direct`, `follow-up`, `subagent`)
- Confidence scoring and ambiguity handling
- Agent-specific context loading
- Persistent intervention memory with session enrichment and full-text search
- MCP server tools for native assistant integration
- Scenario suggestion workflow from historical interventions
- Post-generation quality gate (`--check`) with 8 structural checks
- Git-aware update checks (fetch, branch detection, manual-only update policy)

### Capability Snapshot (Exact, Honest)

| Capability axis | Status | How to verify |
|---|---|---|
| Parallel orchestration | Yes (planning hint) | Routing output includes `complexity.suggest_parallel_subagents` for long tasks |
| Guards / quality checks | Yes | `python -m rgen.cli --check --target ./my-app` |
| Memory / state | Yes (persistent + session enrichment) | `route_query` returns `prior_interventions`; `search_history` queries SQLite memory |
| Observability / monitoring | Yes | `python .github/router.py --stats`, `python .github/router.py --audit`, MCP `get_stats` / `audit_coverage` |
| Multi-channel / deploy | Yes (CLI + MCP + PyPI) | `python -m rgen.cli`, `agentpilot-mcp`, `pip install agentpilot-orchestrator` |
| Tool integration | Yes (MCP tools) | `route_query`, `search_history`, `log_intervention`, `get_update_status`, `manual_update` |
| Coding / Git support | Partial (git-aware updates, no repo janitor) | `get_update_status` uses fetch + branch detection; no automatic merge/worktree operations |
| Sandbox execution | N/A by design | Routing layer only; does not run workloads in Docker/VM sandboxes |

### Presence / Absence Matrix (Gate 0)

This section uses benchmark-style labels to reduce ambiguity for external analyzers.

| Benchmark label | Status | Notes |
|---|---|---|
| Dynamic / intent-based routing | Present | Semantic scenario routing with confidence and fallback (`direct`, `follow-up`, `subagent`) |
| Flexible orchestration (parallel / hierarchical) | Partial | Parallelism is a planning hint (`suggest_parallel_subagents`), not autonomous multi-agent runtime execution |
| Error recovery (retry / abort / human-in-loop) | Partial | Fallback and governance modes are present; structured retry/backoff/circuit-breaker are not yet implemented |
| Persistent memory / session state | Present (partial for session lifecycle) | Persistent SQLite + FTS memory is present; explicit TTL-based session lifecycle is planned |
| Scalability / observability | Present | Health stats, audit coverage, MCP status, update status, runtime metrics (fallback_rate, confidence buckets, latency) are available |
| Multi-channel deployment | Present | CLI + MCP server + Python package modes |
| Tool / code integration | Present | MCP tools for routing, memory, stats, coverage, update checks |
| Git integration (advanced) | Partial | Git-aware update checks only; no worktree/merge janitor |

## Feature Highlights

### Multi-Language Support

Generate outputs with an explicit language or let the pipeline auto-detect.

```bash
python -m rgen.cli --direct --pattern python_api --name my-app --target ./my-app --language it
python -m rgen.cli --direct --pattern python_api --name my-app --target ./my-app --language en
```

Language support details and per-pattern layout are documented in:

- `knowledge_base/python_api/i18n/README.md`
- `knowledge_base/node_ts/i18n/README.md`
- `knowledge_base/psm_stack/i18n/README.md`

See `docs/i18n-GUIDE.md` for migration notes and i18n conventions.

### Cost Estimator

Estimate the monthly token cost per routing scenario from intervention history.

```bash
python -m rgen.cli --cost-report --target ./my-app
python -m rgen.cli --cost-report --target ./my-app --cost-model gpt-4o --cost-monthly-queries 5000
python -m rgen.cli --cost-report --target ./my-app --cost-format text
python -m rgen.cli --cost-report --target ./my-app --cost-output artifacts/cost.json
```

Note: `artifacts/cost.json` is generated by the command when `--cost-output` is provided.

Output: JSON report with per-scenario cost, token estimates, and consolidation hints.
Pricing registry is versionable via `--pricing-db`. Accuracy: +/- 10% on known fixtures.
Caveat: estimates use a ~1 token/4 chars heuristic; use provider dashboards for billing accuracy.

### Quality Gate (`--check`)

Run 8 structural checks on any generated project directory — usable as a manual gate before a deploy or in CI pipelines.

```bash
python -m rgen.cli --check --target ./my-app
```

Example output:

```text
Self-check su: ./my-app
  [OK] required_files
  [OK] routing_map
  [OK] expert_files
  [OK] agent_registry
  [OK] copilot_instructions
  [OK] template_vars
  [OK] core_files
  [OK] router_stats

Risultato: OK — 8 pass, 0 warn, 0 errori
```

Checks cover: required file presence, routing-map validity, expert file completeness, agent registry alignment, leftover template placeholders, and router health. Exit code is non-zero on failure, suitable for CI integration.

> Design note: AgentPilot is a routing layer, not an execution sandbox. It routes tasks to the right agent context (including infra/Docker scenarios) but does not execute or isolate workloads. The `--check` command is the built-in quality gate for generated assets.

### Observability & Monitoring

Use these checks to monitor routing quality and detect drift early:

```bash
python .github/router.py --stats
python .github/router.py --audit
python .github/mcp_status.py
python .github/update_report.py --output .github/UPDATE_STATUS.md
```

MCP equivalents are available via `get_stats`, `audit_coverage`, and `get_update_status`.

**Runtime metrics** (Milestone 1 — available since v0.x):

```bash
# Via MCP tool (returns JSON):
# get_runtime_metrics(window=50)
# → fallback_rate, confidence_buckets (0-25/25-50/50-75/75-100%), error_rate, scenario_usage

# Via Python API:
python -c "from rgen.metrics_collector import RouterMetricsCollector; import json; c = RouterMetricsCollector(); print(json.dumps(c.fallback_rate(), indent=2)); c.close()"
```

Each `route_query()` call now captures `routing_latency_ms` in the result for latency tracking.

### ROI Benchmark (Live Demo)

Run a fast, repeatable comparison across three modes:

- no routing baseline
- free/open-core routing
- paid/premium routing policy

```bash
python -m rgen.cli --roi-benchmark
python -m rgen.cli --roi-benchmark --roi-format text
python -m rgen.cli --roi-benchmark --roi-scale 3
python -m rgen.cli --roi-benchmark --roi-output artifacts/roi-benchmark.json
```

Note: `artifacts/roi-benchmark.json` is generated by the command when `--roi-output` is provided.

Output includes per-strategy LLM cost, operational cost, total cost, and savings deltas.
The command is safe for public docs: it demonstrates behavior and ROI deltas without exposing proprietary policy internals.

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
2. Router evaluates candidate task types using keyword sets, priorities, and certainty scoring.
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

New to the CLI? Start with the beginner-safe guide:

- `docs/CLI_NOOB_GUIDE.md` (step-by-step, path-safe flow, `python -m` explanation)
- `docs/CLI_OPTIONS_MATRIX.md` (option -> behavior -> file impact matrix)

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

# Optional: bootstrap Anthropic skills (only if missing)
bash .github/skills.sh setup-anthropic-skills

# Optional: force refresh skills
bash .github/skills.sh setup-anthropic-skills --force
```

Prerequisiti bootstrap skill:

- `bash`
- `npx` (path preferito) oppure `git` (fallback)

Variabili supportate:

- `ANTHROPIC_SKILLS_SLUG` (default: `anthropics/skills`, GitHub slug not a local path)
- `ANTHROPIC_SKILLS_REPO` (default: `https://github.com/anthropics/skills.git`)
- `ANTHROPIC_SKILLS_REF` (tag/branch per fallback git)
- `ANTHROPIC_SKILLS_CLI_TIMEOUT` (secondi, default: `90`)

Troubleshooting rapido:

- Se `npx` non installa nulla, lo script passa automaticamente al fallback git.
- Se il bootstrap resta lento in rete instabile, riduci timeout: `ANTHROPIC_SKILLS_CLI_TIMEOUT=30`.

### Fast path

```bash
python .github/router.py --stats
python .github/router.py --direct "debug Python API timeout"
```

For a quick developer-focused flow:

```bash
python .github/router.py --direct "fix failing test in auth service"
python .github/router.py --direct "refactor payment service retries"
python .github/router.py --direct "write docs for rate-limit middleware"
```

CLI note: prefer `python -m rgen.cli ...` during development to avoid PATH drift between installed entrypoints and local source.

### 2) Generate routing assets

```bash
python -m rgen.cli --direct --pattern python_api --name my-app --target ./my-app
```

### 3) Run router checks

```bash
python .github/router.py --stats
python .github/router.py --audit
```

### 4) Suggest new scenarios from history

```bash
python -m rgen.cli --suggest-scenarios --target ./my-app --suggest-format text
```

### 5) Inspect generation history and rollback safely

```bash
python -m rgen.cli --history --target ./my-app
python -m rgen.cli --history --show-diffs --history-format json --target ./my-app
python -m rgen.cli --rollback --to 20260411_103000 --target ./my-app
```

### 6) Marketplace MVP (local + remote)

```bash
python -m rgen.cli --search-patterns python
python -m rgen.cli --download ./pattern-pack --install-dir ./knowledge_base
python -m rgen.cli --download file:///C:/tmp/pattern-pack.zip --install-dir ./knowledge_base
python -m rgen.cli --download owner/repo:v1.0.0 --install-dir ./knowledge_base
```

## Practical Tips

- Start with `python .github/router.py --stats` before changing routing rules.
- Use `--direct` queries as smoke tests whenever you edit scenarios or keywords.
- Keep `knowledge_base` generic in public snapshots and move operational playbooks to private space.
- Run `python -m rgen.cli --suggest-scenarios` only after collecting enough intervention history, otherwise the signal is weak.
- Use `python -m rgen.cli --history --show-diffs` before a rollback when you need to verify which files are still unchanged since generation.
- For marketplace downloads, validate pack contents locally first and keep trusted sources in a curated registry.
- Install MCP extras only when you need the server runtime; the generator itself stays lightweight.

## Example Flow

```bash
# 1. Generate assets for a target repository
python -m rgen.cli --direct --pattern python_api --name payments-api --target ./payments-api

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

Route output notes:

- `route_query` can include a `policy` object with open-core decision metadata (complexity, fallback strategy, governance mode).
- When a private policy provider is installed, the same field is preserved and resolved through the policy boundary.

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

## Deployment Options

AgentPilot runs in three modes, with no external runtime dependencies for the core:

| Mode | Command | Use case |
|---|---|---|
| CLI | `python -m rgen.cli` / `python .github/router.py` | Local development, CI pipelines |
| MCP server | `agentpilot-mcp` (stdio transport) | VS Code, Claude, Cursor assistant integration |
| PyPI package | `pip install agentpilot-orchestrator` | Embedding in existing Python projects |

The core depends on stdlib only. MCP extras are opt-in (`pip install -e ".[mcp]"`).

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
- It ships a built-in quality gate (`--check`) for generated assets, integrable in CI pipelines.
- It is git-aware: update checks use fetch and branch detection without automatic writes.
- By design, it is a routing layer — not an execution sandbox. It routes infra tasks to the right context rather than running workloads, keeping the core stdlib-only.

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


