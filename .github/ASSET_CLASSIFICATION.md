# Asset Classification — AgentPilot Orchestrator

## Purpose

Repository-level classification of assets into public, internal, and private scopes for open-core cutover.

## Public

- core/ (generic runtime templates)
- rgen/ (core generator package)
- tests/ (unit/integration tests excluding private fixtures)
- README.md
- .github/router.py
- .github/router_planner.py
- .github/router_audit.py
- .github/interventions.py
- .github/requirements.txt
- .github/mcp_server.py
- .github/routing-map.json
- .github/esperti/
- .github/MCP_CONTRACT.md
- .github/OPEN_CORE_BOUNDARY.md
- .github/workflows/ci.yml
- agentpilot-orchestrator.code-workspace
- knowledge_base/node_ts/
- knowledge_base/python_api/
- pyproject.toml
- requirements-dev.txt

## Internal

- README_AGENTPILOT_ORCHESTRATOR_EN.md
- .github/ASSET_CLASSIFICATION.md
- .github/BRANCH_HYGIENE_POLICY.md
- .github/copilot-instructions.md
- .github/ROADMAP.md
- .github/RELEASE_NOTES.md
- .github/decision-priority.md
- .github/token-budget-allocation.md
- .github/versioning-strategy.md
- .github/AGENT_REGISTRY.md
- .github/KNOWHOW_EXPOSURE_AUDIT_2026-04-11.md
- .github/kpi/
- .github/plans/
- .github/standard/
- .github/skills.sh
- .github/subagent-brief.md

## Private

- artifacts/
- knowledge_base/psm_stack/
- knowledge_base/psm_stack/esperti/ (operational know-how)
- .github/interventions.db
- .github/.rgen-backups/
- .claude/
- .continue/
- .continuerules
- .discussioni/
- .github/plans-local/
- .vscode/settings.json
- *.db / *.sqlite runtime artifacts

## Notes

- If a file contains environment-specific topology or operational runbooks, it is private by default.
- Public snapshots must exclude private paths during new-repo migration.
