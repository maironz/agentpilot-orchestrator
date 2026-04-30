# Update Status Report

Generated at: 2026-04-30T20:21:35.841059+00:00

## Summary
- Banner label: Need Update
- Banner value: [Need Update](.github/UPDATE_STATUS.md)
- Source: active-option
- Status: outdated
- Compared files: 11
- Drift files: 3
- Drift list: .github/interventions.py, .github/mcp_server.py, .github/router.py
- Suggested manual command: python .github/active_option_sync.py --apply

## Remote Version Check
- Local version: 0.4.0
- Remote version: 0.4.0
- Up to date with remote.

## Manual Update
- Run this command to update without enabling auto mode:
  - `python .github/active_option_sync.py --apply`
- This updates the active option files under `.github/` from source files in `core/`.

## Auto Update
- Optional auto-update is available via: `python .github/update_report.py --auto`
- Auto mode calls active option sync and writes result in this report.

## Auto Update Result
- updated: True
- status: updated
- message: Active option updated for 3 files.

## Raw Status JSON
```json
{
  "checked_at": "2026-04-30T20:21:35.718046+00:00",
  "source": "active-option",
  "scope": "core->.github",
  "status": "outdated",
  "update_available": true,
  "compared_files": 11,
  "drift_files": [
    ".github/interventions.py",
    ".github/mcp_server.py",
    ".github/router.py"
  ],
  "drift_count": 3,
  "manual_update_command": "python .github/active_option_sync.py --apply"
}
```

## Raw Auto Result JSON
```json
{
  "updated": true,
  "status": "updated",
  "message": "Active option updated for 3 files.",
  "files_updated": [
    ".github/interventions.py",
    ".github/mcp_server.py",
    ".github/router.py"
  ],
  "details": {
    "checked_at": "2026-04-30T20:21:35.841059+00:00",
    "source": "active-option",
    "scope": "core->.github",
    "status": "up-to-date",
    "update_available": false,
    "compared_files": 11,
    "drift_files": [],
    "drift_count": 0,
    "manual_update_command": "python .github/active_option_sync.py --apply"
  }
}
```
