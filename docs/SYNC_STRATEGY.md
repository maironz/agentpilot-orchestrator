# Copilot Instructions Sync Strategy

## Overview

The AgentPilot Orchestrator uses an **explicit override zone strategy** to safely sync auto-generated content while preserving local customizations.

## Override Zones

The file `.github/copilot-instructions.md` uses explicit boundary markers to separate auto-generated content from local customizations.

### Generated Content (can be overwritten)

Content between these markers is auto-generated from `core/copilot-instructions.md` and may be overwritten during sync:

```markdown
<!-- start AgentPilot Rules -->
⚠️ **WARNING**: Content between these markers is auto-generated and may be 
overwritten by the sync process. Do not add local customizations here.

## DISPATCHER
[Router rules, protocols, bootstrap procedures]

## PROJECT
[Project stack description]
...
<!-- end AgentPilot Rules -->
```

### Local Content (always preserved)

Anything **outside** these markers is local and will survive automatic syncs:

```markdown
<!-- end AgentPilot Rules -->

## 📍 ESSENTIALS
[Project-specific context: paths, credentials, quick start]

## 🛑 CRITICAL CONSTRAINTS
[Production rules: Let's Encrypt, backups, sync policies]

## 📊 PROJECT PROGRESS
[Timeline, phases, milestones]
```

## How Sync Works

### Command

```bash
python .github/active_option_sync.py --apply
```

### Logic

For `copilot-instructions.md` (special handling):
1. Extract override zone from `core/copilot-instructions.md`
2. Locate same override zone in `.github/copilot-instructions.md`
3. Replace ONLY the override zone section
4. Preserve everything outside the markers

For all other files:
- Flat copy (standard behavior)

### Safety Features

**Fallback Protection**: If either file is missing override zone markers:
- ❌ Sync is **skipped** (not applied)
- ⚠️ File listed in `files_skipped` with reason
- This prevents accidental data loss

**Drift Detection**: If markers are missing:
```json
{
  "files_skipped": [
    ".github/copilot-instructions.md (no override zones, skipped)"
  ],
  "message": "Active option updated for 11 files. (1 files skipped due to missing override zones)"
}
```

## Adding Local Content

### Step 1: Add your customizations outside the override zone

```markdown
<!-- end AgentPilot Rules -->

## Local Section Title
Your custom content here.
```

### Step 2: Keep the markers intact

Never remove or edit the `<!-- start AgentPilot Rules -->` and `<!-- end AgentPilot Rules -->` lines.

### Step 3: Next sync

On next `python .github/active_option_sync.py --apply`:
- The override zone is updated with latest from `core/`
- Your local content remains unchanged

## Example Structure

```markdown
# AgentPilot Orchestrator -- AI Dispatcher

<!-- start AgentPilot Rules -->
⚠️ **WARNING**: Content between these markers is auto-generated...

## DISPATCHER
### Session bootstrap (obbligatorio)
...

## PROJECT
**AgentPilot Orchestrator** | Stack: python, fastapi, ...

## Tracciatura discussioni
...
<!-- end AgentPilot Rules -->

## 📍 ESSENTIALS - Project-Specific
### What is This?
Stack Docker for CMS + Gestionale Casse...

### Quick Status
- ✅ VM 192.168.2.253: Production live
- ✅ Let's Encrypt: Auto-renewal active
...

## 🛑 CRITICAL CONSTRAINTS
### Let's Encrypt Must Stay Alive
...

## 📊 PROJECT PROGRESS
### Completed ✅
...
```

## Implementation Details

### File: `core/copilot-instructions.md`

- Source of truth for generated content
- Must have complete `<!-- start AgentPilot Rules -->...<!-- end AgentPilot Rules -->` markers
- Updated when improving the routing system

### File: `.github/copilot-instructions.md`

- Runtime file loaded by VS Code
- Contains merged content (auto-generated + local)
- Local sections outside markers are preserved on sync

### Script: `.github/active_option_sync.py`

Function: `_sync_with_override_zones(src, dest)`

- Checks if source has override zone markers
- If markers exist in dest, replaces only the zone
- If markers missing anywhere, skips the file (safety)
- Supports smart merge for `copilot-instructions.md` only

## Migration Notes

### For Existing Installations

If you have an older `.github/copilot-instructions.md` without markers:

1. **Option A (Recommended)**: Add markers to both files

   ```bash
   # In core/copilot-instructions.md: wrap DISPATCHER through Policy exploration in markers
   # In .github/copilot-instructions.md: add same markers
   ```

2. **Option B**: Let sync remain as flat copy (no smart merge)

   - Next sync will replace entire file
   - If you have local customizations, back them up first

## Troubleshooting

### "No override zones, skipped" in sync output

**Cause**: Markers are missing in source or dest

**Fix**:
1. Verify `core/copilot-instructions.md` has both markers (lines 3–142 approx)
2. Verify `.github/copilot-instructions.md` has both markers
3. If one is missing, add them (see "Adding Local Content" section)

### Local content was lost after sync

**Cause**: Local content was placed inside override zone markers

**Fix**:
1. Check `.github/copilot-instructions.md`
2. Move local content to **after** `<!-- end AgentPilot Rules -->`
3. Next sync will preserve it

### Sync always shows "up-to-date" but I want to update

**Check**:
- Compare SHA256 hashes: `python .github/active_option_sync.py`
- If no drift files, core and .github are in sync
- If you modified core, drift should appear on next check
