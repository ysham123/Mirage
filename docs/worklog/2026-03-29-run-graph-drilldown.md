# 2026-03-29 Run Graph Drilldown

## Goal

Add a graph visualization to the Action Review Console without changing Mirage's primary product shape.

## Summary

The UI now includes a per-run `Run Graph` view inside `Run Drilldown`. The graph is secondary to the existing metrics overview and timeline. It visualizes each intercepted action as a simple decision path:

- request
- policy gate
- Mirage outcome
- sandbox artifact

This keeps the current V1 structure intact while making individual runs easier to explain in demos and review sessions.

## Why

- The metrics overview answers what is happening across runs.
- The timeline answers what happened step by step inside one run.
- The graph now answers how Mirage reached the outcome for a specific action flow.

That makes the UI more legible for live demos without turning Mirage into a graph-first product.

## Files Changed

- `demo_ui/index.html`
- `tests/test_demo_ui.py`
- `README.md`
- `docs/worklog/INDEX.md`

## Verification

- `pytest tests/test_demo_ui.py -q`
- `pytest tests -q`
- `python -m compileall demo_ui tests`

## Risks

- The graph is intentionally lightweight and HTML/CSS based. It is optimized for clarity, not for rendering large or highly branching workflows.
- If run structures become more complex later, this view may need to move to SVG or a richer graph renderer.

## Next Step

If the graph proves useful, the next refinement should be syncing it to a selected terminal run or adding node-level hover details. It should remain a per-run drilldown, not the primary homepage surface.
