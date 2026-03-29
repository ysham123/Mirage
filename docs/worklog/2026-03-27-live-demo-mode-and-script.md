# Live Demo Mode And Script

## Goal

Make the Mirage founder demo stronger for live use by adding a step-by-step playback mode to the UI and writing an exact live-demo script.

## Why This Work Was Needed

- Outside review converged on the same issue: the UI was clear, but too results-first to be the strongest live proof.
- The UI also was not surfacing the policy decision detail it already implied visually.
- The repo needed a reusable demo script so live narration is consistent and not improvised.

## Implementation Summary

- Enriched the demo UI API payload with summary metadata, trace-backed decision arrays, and trace event details.
- Added a live playback mode to the founder demo UI so steps reveal progressively instead of appearing only as a completed state.
- Kept instant mode available as a fallback for recordings or time-constrained demos.
- Added a three-minute live demo script in `docs/live-demo-script.md`.

## Files Changed

- `demo_ui/server.py`
- `demo_ui/index.html`
- `tests/test_demo_ui.py`
- `README.md`
- `docs/live-demo-script.md`

## Verification

- `pytest tests/ -q`
- `python -m compileall src tests examples demo_ui`

## Open Risks

- Playback mode improves legibility, but the strongest credibility signal is still a real terminal run before the UI.
- The UI is still a founder demo surface, not a product dashboard.
