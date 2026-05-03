# Update Status Report

Generated at: 2026-05-03T07:28:26.705395+00:00

## Summary
- Banner label: Need Update
- Banner value: [Need Update](.github/UPDATE_STATUS.md)
- Source: active-option
- Status: outdated
- Compared files: 12
- Drift files: 2
- Drift list: .github/copilot-instructions.md, .github/update_report.py
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

## Raw Status JSON
```json
{
  "checked_at": "2026-05-03T07:28:26.417979+00:00",
  "source": "active-option",
  "scope": "core->.github",
  "status": "outdated",
  "update_available": true,
  "compared_files": 12,
  "drift_files": [
    ".github/copilot-instructions.md",
    ".github/update_report.py"
  ],
  "drift_count": 2,
  "manual_update_command": "python .github/active_option_sync.py --apply"
}
```
