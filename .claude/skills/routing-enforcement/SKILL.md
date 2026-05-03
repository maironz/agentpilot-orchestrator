# Routing Enforcement Skill

**Description**: Validates that routing discipline is maintained in every substantial response involving code changes, multi-step work, or architecture decisions. Ensures AgentPilot router is used or valid exception is declared.

**Trigger conditions** (automatically check when):
- File edits (code, docs, config, markdown)
- Multi-step work (3+ steps or affecting multiple files)
- Architecture/design decisions
- Integration points or feature additions
- Any modification to routing-map.json or core files

**Validation logic**:

1. **Router Evidence Check**
   - Look for routing output: `python .github/router.py --direct "<query>"`
   - Verify presence of: `agent`, `scenario`, `confidence`, `priority` in response
   - Accept alternative: `python .github/router.py --stats` (health check)
   - Accept MCP: `route_query` tool call result

2. **Exception Declaration**
   - If no router output, verify exactly ONE of these is declared:
     - **Exception 1**: "Continuo dal summary precedente, agente: [X]" (context compression)
     - **Exception 2**: "Post-task documentation: [task name], agente: [X]" (same agent continuation)
     - **Exception 3**: "Orchestrazione: scelgo [scenario] perché [motivo]" (meta-router ambiguity)
   - If none declared and no router output: **INCOMPLETE**

3. **Agent Coherence Check**
   - Verify declared agent matches work performed:
     - `backend` → database/API/server changes ✓
     - `devops` → infrastructure/docker/deployment ✓
     - `documentazione` → docs/guides/examples ✓
     - `orchestratore` → routing decisions/architecture ✓
   - Mismatch = flag as "incoherent"

4. **File Conformance Check**
   - List files modified
   - Verify they align with declared scenario from routing
   - Check against routing-map.json context for agent
   - Files outside scope = flag as "drift"

5. **Coverage Audit Check**
   - Detect new Python classes, functions, CLI scripts, database tables, or modules
   - Verify they have corresponding keywords in routing-map.json or routing-map.local.json
   - Missing keywords = coverage gap, flag with: "New component `[name]` lacks routing keywords"

6. **Health Check (if routing-map modified)**
   - Run: `python .github/router.py --stats`
   - Verify status is [OK] or [WARN], not [CRIT]
   - Report changes in scenario count, overlap %, status

---

## Validation Summary Template

Use this format at end of response:

```
✅ Postflight Validation:
- Router used: YES ✅ (agent: [name])
  OR Exception: [name] ✅
- Agent coherent: [YES/NO] ✅
- File conformance: [n files] ✅
- Coverage audit: [status] ✅
  - [component1]: COVERED | MISSING (requires: [keywords])
- Health check: [OK/WARN/N/A] ✅

Status: [COMPLETE] or [INCOMPLETE — [reason]]
```

---

## When to Flag as Incomplete

Response is **INCOMPLETE** if ANY of these are true:

1. ❌ No router output AND no exception declared
2. ❌ Exception declared but does not match one of 3 documented cases
3. ❌ Agent claimed but does not match work performed
4. ❌ Files modified outside declared routing scope (drift)
5. ❌ New components added without routing keywords (coverage gap)
6. ❌ Router status is [CRIT] after changes
7. ❌ Response length is suspiciously short for claimed complexity

---

## Exception: When to Skip Routing

Only ONE of these 3 cases allows skipping routing. **Declare explicitly.**

### Exception 1: Conversation Summary Continuation
- **Condition**: VS Code compressed context with summary containing file list + agent + plan
- **Declaration**: "Continuo dal summary precedente, agente: [X]"
- **Verify**: Summary must include file list and agent name from prior session
- **Implication**: Router can be skipped if all continuation data already in summary

### Exception 2: Post-Task Documentation
- **Condition**: Extending work just completed by same agent (documentation, inline comments, guides)
- **Scope**: Limited to task just completed, no new features
- **Declaration**: "Post-task documentation: [completed task], agente: [X]"
- **Implication**: If task itself was routed, docs don't need separate routing

### Exception 3: Ambiguity Meta-Router
- **Condition**: Router returned multiple scenarios with confidence within 5% (ambiguous)
- **Role**: Orchestratore resolves via domain knowledge
- **Declaration**: "Orchestrazione: scelgo [scenario] perché [motivo]"
- **Implication**: Meta-routing is a valid bypass only for ambiguity resolution

---

## Non-Negotiable Rule

> **If you cannot explain which scenario should handle this task, the task is not ready.**  
> Route it first. Then execute. Then validate.

If unsure, always route. Routing is cheap (one CLI call). Mistakes are expensive (wrong agent, wrong context, wrong priority).
