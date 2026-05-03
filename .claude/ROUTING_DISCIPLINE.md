---
name: Routing Discipline
description: Enforce routing discipline for AgentPilot Orchestrator — every substantial response must include routing or declare exception
priority: 95
applyTo:
  - "**.py"
  - "**.md"
  - "**.json"
  - "**.ts"
  - "**.js"
  - "Makefile"
  - "**.sh"
---

# Routing Discipline — Core Instruction

This instruction applies to **ALL** work in the AgentPilot Orchestrator repository.

## Foundational Rule

**Every response involving substantial work must start with routing output.**

Substantial work = file edits, multi-step implementation, architecture decisions, feature additions, integrations.

## How to Route

**Before any substantial response:**

```bash
python .github/router.py --direct "<query>"
```

Output will include:
- `agent` — which agent domain (backend, devops, docs, orchestratore)
- `scenario` — specific routing scenario (e.g., database_optimization, api_endpoints)
- `confidence` — confidence score (0.0 - 1.0)
- `priority` — task priority (high, medium, low)

**Publish the routing output in the response header:**

```
🤖 Routing: agent=[name] | scenario=[name] | confidence=[score] | priority=[level]
```

## Routing Is Non-Optional

Unless ONE of the 3 Named Exceptions applies (see `/memories/routing-discipline.md`), routing is **not optional**.

If you skip routing without exception:
- Response is **incomplete**
- User will ask: "Where's the router output?"
- Task must be redone with routing

## The 3 Named Exceptions

**Only these bypass routing. All others are invalid.**

1. **Summary Continuation** — Context was compressed, summary has file list + agent  
   Declaration: `"Continuo dal summary precedente, agente: [X]"`

2. **Post-Task Documentation** — Documenting work just completed (same agent)  
   Declaration: `"Post-task documentation: [task], agente: [X]"`

3. **Meta-Router Ambiguity** — Router confidence was tied (2+ scenarios within 5%)  
   Declaration: `"Orchestrazione: scelgo [scenario] perché [motivo]"`

## Postflight Validation

At the **end of every substantial response**, include validation:

```
✅ Postflight Validation:
- Routing: YES (agent: [name])
- Agent coherent: YES
- File conformance: [n files] OK
- Coverage audit: [status]
- Health check: [OK/WARN]

Status: COMPLETE
```

If validation fails on any check, response is incomplete.

## What "Coherence" Means

Agent must match work:
- `backend` → database, API, server-side code, schemas
- `devops` → docker, CI/CD, deployment, infra, scripts
- `documentazione` → docs, guides, examples, READMEs, comments
- `orchestratore` → routing, architecture, governance, patterns

If you claim `backend` but modify docker files, that's **incoherent**. Fix it.

## File Scope Rules

Modified files must align with routing scenario:
- If scenario is "database_optimization", files should be in `backend/`
- If scenario is "docker_infra", files should be in `.github/` or `docker/`
- If files drift outside scope, flag it: "Drift detected: [file] outside scope"

## Coverage Audit Rules

If you create **new components** (classes, functions, scripts, tables, modules):
- They must have keywords in `routing-map.json`
- Or in `routing-map.local.json` (host-specific additions)
- Example: new class `PaymentRetry` needs keywords like "payment", "retry" in routing

Missing keywords = coverage gap. Flag it: `"New [type] [name] lacks keywords"`

## No Bypasses Without Explicit Permission

You cannot bypass this rule without:
1. Explicit user acknowledgment: `"routing waived for this response"`
2. OR a file created by user: `/memories/session/routing-waived-[date].md`

Creating a waiver file without user request is forbidden.

## Commands Reference

Quick routing checks:
```bash
python .github/router.py --direct "your query here"     # Route single query
python .github/router.py --stats                         # Health check
python .github/router.py --audit                         # Coverage audit
```

MCP equivalents (if available):
```
route_query(query="your query here")
get_stats()
audit_coverage()
```

## Implementation Checklist

Before submitting response:

- [ ] Routing output included (or exception declared)
- [ ] Agent name matches work type
- [ ] Files modified align with routing scope
- [ ] New components have routing keywords
- [ ] Postflight validation summary present
- [ ] Status is "COMPLETE" (not "incomplete")

All boxes must be checked.

## The Non-Negotiable Principle

> **If you cannot explain which scenario should handle this task, the task is not ready.**

Router is not a suggestion. It's your compass.

- Routing = clarity of scope, agent, priority
- Skipping routing = operating blind
- Routing takes 30 seconds
- Mistakes cost hours

**Use it every time. Be exact. Be traceable.**

---

## References

- Skill: See `.claude/skills/routing-enforcement/SKILL.md`
- Memory: See `/memories/routing-discipline.md`
- Routing map: See `core/routing-map.json`
- Router docs: See `.github/router.py --help`
