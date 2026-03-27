# Demo UI Alignment

## Goal

Align the new founder demo UI with Mirage's actual procurement onboarding path and remove review findings around drift, missing coverage, and inconsistent docs.

## Why This Work Was Needed

- The UI was calling `MirageEngine` directly instead of using the same proxy-backed workflow the procurement harness demonstrates.
- The UI had no automated coverage, so demo regressions would not be caught in CI.
- The Docker path and config docs still reflected the old root-config flow instead of the procurement harness.
- The UI used a Pydantic-v2-only serialization call even though the repo keeps Pydantic unpinned.

## Implementation Summary

- Added a shared procurement scenario runner in `examples/procurement_harness/scenarios.py`.
- Updated the CLI demo to use the shared scenario runner.
- Refactored `demo_ui/server.py` to run scenarios through Mirage's FastAPI proxy boundary using `ProcurementAgent` instead of calling the engine directly.
- Removed the UI's direct dependency on Pydantic model serialization.
- Made the demo UI port configurable through `PORT`.
- Added a UI smoke test file.
- Updated the main README, procurement harness README, and Docker Compose path to match the procurement onboarding flow.

## Files Changed

- `demo_ui/server.py`
- `docker-compose.yml`
- `README.md`
- `examples/procurement_harness/README.md`
- `examples/procurement_harness/demo.py`
- `examples/procurement_harness/scenarios.py`
- `tests/test_demo_ui.py`

## Verification

- `pytest tests/ -q`
- `python -m compileall src tests examples demo_ui`

## Open Risks

- The UI still presents a demo-focused view model, so future procurement workflow changes should keep the shared scenario layer as the integration boundary.
- Docker Compose was aligned config-wise, but container runtime should still be rechecked on a machine with a running Docker daemon.
