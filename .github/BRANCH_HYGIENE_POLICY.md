# Branch Hygiene Policy — AgentPilot Orchestrator

## Purpose

Keep repository branches understandable, reviewable, and safe during the open-core cutover.

## Naming Rules

- `main` for the default stable branch
- `cutover/*` for repository migration and public snapshot work
- `feat/*` for user-facing features
- `fix/*` for bug fixes
- `docs/*` for documentation-only changes
- `chore/*` for maintenance and tooling

## Retention Rules

- merged feature branches should be deleted within 7 days
- stale non-default branches with no updates for 30 days should be reviewed
- stale non-default branches with no updates for 60 days should be deleted unless explicitly preserved
- cutover branches remain until public repository validation is complete

## Deletion Criteria

A remote branch can be deleted when all conditions are true:
- merge or replacement branch has been confirmed
- no open PR depends on the branch
- no release or rollback procedure references the branch
- owner has no explicit keep request

## Operational Routine

Weekly:
- `git fetch --prune origin`
- review `git branch -r --sort=-committerdate`
- inspect open PR references before deleting stale branches

Before cutover:
- freeze ad-hoc long-lived feature branches
- create `cutover/agentpilot-orchestrator`
- keep a single source branch for the public snapshot

## Notes

- Do not rewrite history unless required for secret remediation.
- Prefer archive decisions in the hosting platform over undocumented local exceptions.