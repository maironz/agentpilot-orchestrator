# Open-Core Boundary — AgentPilot Orchestrator

## Purpose

Define which assets remain public (open core) and which assets move to private development.

## Boundary Matrix

| Area | Asset Type | Scope | Rationale |
|---|---|---|---|
| Routing Engine | core routing logic, scoring, confidence, fallback | Public | Product trust and adoption depend on transparent behavior |
| MCP Baseline | MCP server core tools and schemas | Public | Integration is a key adoption lever |
| Documentation | README, quickstart, architecture overview | Public | Lowers onboarding friction |
| Tests | core unit/integration tests for routing and MCP contracts | Public | Reliability proof and contribution quality |
| Knowledge Base (generic) | general experts/templates not environment-specific | Public | Reusable value for community |
| Knowledge Base (sensitive ops) | environment-specific runbooks and operational playbooks | Private | Protect operational know-how and internal procedures |
| Commercial Governance | advanced policy packs, premium controls, proprietary scoring extensions | Private | Competitive moat and monetization path |
| Go-to-market Assets | campaign experiments, acquisition playbooks, private positioning docs | Private | Strategic confidentiality |

## Public-by-default Criteria

An asset can be public when all conditions are true:
- no credentials, secrets, or environment-specific endpoints
- no internal-only operational topology details
- reproducible in a clean environment
- useful to external users without private context

## Private-by-default Criteria

An asset should be private when any condition is true:
- contains proprietary operational procedures
- includes infrastructure fingerprints or sensitive architecture details
- provides business-sensitive differentiation logic
- exposes internal growth experiments or strategic positioning details

## Release Gate (Before Public Push)

- [ ] Secret scan completed on staged changes
- [ ] Know-how exposure review completed
- [ ] README and quickstart validated in clean environment
- [ ] MCP contract compatibility checked
- [ ] Boundary review signed off (owner)

## Operational Safeguards

- Keep proprietary code only under `.private-packages/` (already gitignored).
- Reference private logic from public code only via explicit loaders:
	- `rgen/premium_pricing_loader.py`
	- `rgen/premium_runtime_loader.py`
	- `rgen/premium_policy_loader.py`
- Do not import `agentpilot_intelligence.*` directly outside loader boundaries.
- Run boundary guard tests before push:
	- `pytest -q tests/test_private_boundary_guard.py`
- If a private path appears in `git status` tracked files, stop and remove it from index before publishing.

## Notes

This file is a living policy document and should be reviewed at each minor release.
