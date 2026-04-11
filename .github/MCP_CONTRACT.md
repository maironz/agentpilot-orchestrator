# MCP Contract — AgentPilot Orchestrator

## Version

- `mcp_contract_version`: `v1`
- compatibility policy: additive-first (avoid breaking field removals/renames in v1)

## Transport

- primary: `stdio`
- startup command: `python .github/mcp_server.py`

## Tools

### 1) route_query

Input:
- `query: str` (required)
- `mode: str` (optional, default: `direct`)
  - supported: `direct`, `follow_up`, `subagent`

Output:
- JSON string containing routing payload with fields such as:
  - `agent`, `files`, `context`, `priority`, `scenario`
  - optional: `confidence`, `routing_debug`, `repo_exploration`, `capability`, `capability_instructions`

### 2) search_history

Input:
- `query: str` (optional, default empty)
- `limit: int` (optional, default `10`)

Output:
- if `query` is non-empty: JSON array of intervention matches
- if `query` is empty: JSON stats object

### 3) log_intervention

Input:
- `agent: str` (required)
- `scenario: str` (required)
- `query: str` (required)
- `resolution: str` (optional)
- `files_touched: list[str] | None` (optional)
- `tags: list[str] | None` (optional)
- `duration_min: float | None` (optional)
- `outcome: str` (optional, default: `success`)

Output:
- JSON object: `{ "logged": true, "id": <int> }`

### 4) get_stats

Input:
- none

Output:
- JSON health metrics object from routing health evaluator

### 5) audit_coverage

Input:
- none

Output:
- JSON coverage object without internal keys prefixed by `_`

## Error Contract

- missing MCP dependency: process exits `1` with message:
  - `Missing dependency: mcp. Install with: pip install "mcp[cli]>=1.0.0"`
- runtime tool errors should return actionable messages while preserving non-zero status where relevant

## Backward Compatibility Policy (v1)

Allowed without version bump:
- adding optional fields in JSON outputs
- adding new tools

Requires version bump (`v2`):
- removing existing fields used by clients
- renaming tool names or required input fields
- changing default semantics of existing tools
