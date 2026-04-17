# 2026-04-17 Private Alpha Readiness

## Task Goal

Close the "integration-grade private alpha" gate from
[`docs/MIRAGE_PRODUCT_SPEC.md`](../MIRAGE_PRODUCT_SPEC.md): an external Python
engineer can integrate Mirage into an existing `httpx` agent in under 30 minutes
without founder hand-holding, and run Mirage in CI on a real workflow.

## Implementation Summary

Tightened the onboarding seams along the full integration path: friendlier
config errors, per-outcome next-step hints on run summaries, a dedicated pytest
fixture for run-level assertions, plus two new docs (FIRST_INTEGRATION,
CI_INTEGRATION) and a reordered README that leads with "integrate your own
agent" instead of the bundled procurement demo.

## Decisions Made

- Subclass `MirageConfigError` from `ValueError` so the engine's existing
  `config_error` path catches it with no change to `src/engine.py`.
- Sanitize newlines out of the `X-Mirage-Message` / `X-Mirage-Decision-Summary`
  HTTP headers (first line only). Multi-line context still lives in trace JSON
  and in the `summarize-run` CLI output.
- Shipped the pytest fixture as an importable module (`src/pytest_plugin.py`)
  rather than a doc snippet, so adopters write `from src.pytest_plugin import
  mirage_session` instead of copy-pasting ten lines into `conftest.py`.
- Left the demo UI untouched. Product spec flags UI expansion as a non-goal for
  this milestone.

## Files Touched

- `src/config.py` — `MirageConfigError` with file/entry/field-level context and
  inline example snippets.
- `src/httpx_client.py` — per-outcome remediation hints in
  `MirageRunSummary.to_text()`.
- `src/proxy.py` — strip newlines from Mirage response headers.
- `src/pytest_plugin.py` — new `mirage_session` pytest fixture.
- `docs/FIRST_INTEGRATION.md` — new 30-minute walkthrough.
- `docs/CI_INTEGRATION.md` — new pytest + GitHub Actions gating recipes.
- `README.md` — reorder Quickstart to lead with the canonical API; link new docs.
- `tests/test_config_errors.py` — new error-path coverage.
- `docs/worklog/INDEX.md` — index entry.

## Verification Performed

- `make test` (including new `tests/test_config_errors.py`).
- Smoke: broke `operator` in `examples/procurement_harness/policies.yaml` and
  confirmed the new error surfaces file, entry index, name, and a valid example.

## Open Risks

- The FIRST_INTEGRATION walkthrough assumes an `httpx`-based agent; engineers
  on the `requests` library still need a workaround (explicitly deferred per
  the product spec).
- The pytest fixture's `assert_clean()` teardown will surface as a teardown
  error rather than a regular test failure; good enough for a build gate but
  may confuse users expecting a standard `assert` failure line.

## Next Recommended Step

Run the walkthrough end-to-end against a scratch agent (not the procurement
harness) and time it. If it's longer than 30 minutes from cold checkout, the
weakest step becomes the next target.
