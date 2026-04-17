# Action Review Console

## Goal

Turn Mirage from a single-run demo surface into a lightweight action review console built on top of the existing trace artifacts.

## Why This Work Was Needed

- Mirage already had interception, policy decisions, mocked responses, and traces.
- The next product step was to answer not just "what happened in this run?" but "what are my agents doing across runs?"
- The existing founder demo UI was useful for explanation, but not yet a credible V1 product surface for action metrics.

## Implementation Summary

- Added a trace aggregation backend in `src/metrics.py`.
- Added metrics endpoints for overview and per-run drilldown in `demo_ui/server.py`.
- Evolved the UI into an action review console with:
  - summary metrics
  - recent risky runs
  - top endpoints
  - top policy failures
  - run drilldown
- Kept the existing demo scenarios and wired them to refresh the metrics console.
- Added endpoint-level tests for the new metrics surface.

## Files Changed

- `src/metrics.py`
- `demo_ui/server.py`
- `demo_ui/index.html`
- `tests/test_metrics.py`
- `tests/test_demo_ui.py`
- `README.md`

## Verification

- `pytest tests -q`
- `python -m compileall src tests demo_ui`

## Open Risks

- Trace files are still the storage layer, which is right for V1 but not the long-term persistence model.
- Cleanup completed after verification:
  - stopped local Mirage proxy and UI servers
  - removed stray duplicate file `demo_ui/index 2.html`
