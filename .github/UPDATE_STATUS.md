# Update Status Report

Generated at: 2026-04-30T18:40:23.978543+00:00

## Summary
- Banner label: ok
- Banner value: ok
- Source: active-option
- Status: up-to-date
- Compared files: 11
- Drift files: 0
- Suggested manual command: python .github/active_option_sync.py --apply

## Remote Version Check
- Local version: 0.4.0
- Remote version: 0.4.0
- Up to date with remote.

## Manual Update
- Run this command to update without enabling auto mode:
  - `python .github/active_option_sync.py --apply`

## Auto Update
- Optional auto-update is available via: `python .github/update_report.py --auto`
- Auto mode calls active option sync and writes result in this report.

## Raw Status JSON
```json
{
  "checked_at": "2026-04-30T18:40:23.897209+00:00",
  "source": "active-option",
  "scope": "core->.github",
  "status": "up-to-date",
  "update_available": false,
  "compared_files": 11,
  "drift_files": [],
  "drift_count": 0,
  "manual_update_command": "python .github/active_option_sync.py --apply"
}
```
