# KPI Methods and Verification

## Scope
This document defines how routing KPIs are computed and how to verify them.

## KPI Set
- scenario_count: unique scenarios in routing map
- keyword_count: total keywords across scenarios
- overlap_pct: percentage of keyword overlap across scenarios
- confidence_mean: average confidence returned by direct/follow-up routing
- ambiguity_rate: percentage of requests routed to _ambiguity_router
- active_option_drift_count: mismatched files between core/ and .github/

## Data Sources
- router stats: `python .github/router.py --stats`
- direct/follow-up routing output: `python .github/router.py --direct "<query>"`
- active option status: `python .github/active_option_sync.py`

## Verification Routine
1. Run `python .github/router.py --stats`
2. Run at least 10 representative direct queries and collect confidence
3. Count `_ambiguity_router` occurrences
4. Run `python .github/active_option_sync.py` and record drift_count
5. Regenerate report with `python .github/update_report.py --output .github/UPDATE_STATUS.md`

## Threshold Guidance
- overlap_pct: target < 15%
- ambiguity_rate: target < 20% on curated query set
- confidence_mean: target >= 0.55
- active_option_drift_count: target = 0 in stable state

## Notes
- Budget in header is priority-based (high/medium/low), not time-based.
- Routing metrics can vary as routing map and query mix change.
