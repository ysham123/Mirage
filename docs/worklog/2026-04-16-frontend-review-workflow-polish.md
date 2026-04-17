# 2026-04-16 Frontend Review Workflow Polish

## Goal

Tighten the Mirage action review console around real engineer workflows instead of more general UI polish.

This pass focused on three concrete improvements:

- deep-linking directly to a selected run
- faster queue review through outcome filters
- explicit run actions inside the drilldown view

## What Changed

### Run Deep-Linking

- The selected run now syncs to the URL with `?run_id=...`
- The queue filter also syncs to the URL with `?filter=...`
- On page load and browser navigation, the UI restores that state

### Queue Review Controls

- Added queue outcome filters:
  - `All`
  - `Risky`
  - `Allowed`
  - `Unmatched`
- Kept text search, but made the queue render from filtered data instead of hiding DOM rows after render
- Updated keyboard navigation so it follows the visible filtered queue, not the unfiltered underlying list

### Run Actions

- Added explicit run actions in the drilldown:
  - copy run id
  - copy trace path
  - open raw trace
  - jump to the next risky action
- Risky event cards now have stable anchors so the jump action can move through failing events cleanly

## Files Changed

- `demo_ui/index.html`
- `tests/test_demo_ui.py`

## Why

The UI already looked good enough for demos. The more important gap was practical review behavior for engineers:

- opening a specific run from CI or a shared link
- shrinking the review queue to the outcomes that matter
- moving quickly from a selected run to the exact risky action inside it

These changes make the console more useful as a review tool without expanding the product surface.

## Verification

- `pytest -q tests/test_demo_ui.py`
- `pytest -q tests`

## Open Risks

- The UI still does not deep-link to a specific detail view like `timeline` or `trace`
- `copy` actions rely on browser clipboard support
- The queue filter is intentionally simple and not yet persisted beyond the current URL state
