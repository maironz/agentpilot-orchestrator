# Repo Cutover Checklist — AgentPilot Orchestrator

## Goal

Move from current repository to the new public repository with open-core boundaries enforced.

## Preconditions

- [x] MCP smoke tests green
- [x] Router regression subset green
- [x] Open-core boundary draft available
- [x] README in English aligned with new branding

## Cutover Steps

1. Create new repository (public)
- [x] Create repo `agentpilot-orchestrator`
- [x] Initialize default branch policy (`main` + protected rules)
- [x] Add repo description and topics

2. Prepare migration branch in current workspace
- [ ] Create branch `cutover/agentpilot-orchestrator`
- [x] Remove or redact private-only assets based on boundary policy
- [x] Verify `.gitignore` includes local/private operational artifacts
- [x] Prepare dry-run manifest command for public snapshot filtering

3. Push initial open-core snapshot
- [ ] Add new remote `origin-new`
- [ ] Push migration branch to new repo
- [ ] Open/merge initial PR to `main` (direct bootstrap commit used)

4. Validate public-facing experience
- [x] Fresh clone quickstart works
- [x] MCP quickstart verified in clean venv
- [x] Basic commands verified (`--stats`, `--direct`, `--audit`)

5. Finalize old repository strategy
- [ ] Set old repo to private or archive mode
- [ ] Add redirect note in old README (if temporarily public)
- [ ] Freeze old repo branch policy after cutover

## Verification Commands

```bash
# test bundle used before cutover
pytest -q tests/test_mcp_server_smoke.py tests/test_router_runtime.py tests/test_self_checker.py

# dry-run public snapshot manifest
python -m rgen.cutover --root . --output artifacts/cutover-manifest.json

# runtime sanity
python .github/router.py --stats
python .github/router.py --direct "smoke routing"
python .github/router.py --audit
```

## Notes

- Keep migration atomic: first public snapshot should already follow open-core boundaries.
- Avoid rewriting old history unless strictly required for secret remediation.
