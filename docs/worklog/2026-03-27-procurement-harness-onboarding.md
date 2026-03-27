# 2026-03-27 Procurement Harness Onboarding

## Task Goal

Implement the strongest next Phase 2 step: make Mirage easier for an outside Python engineer to understand and try through one realistic procurement harness.

## Implementation Summary

Added a self-contained procurement example harness with its own Mirage config, injected client-based agent workflow, CLI demo path, and end-to-end tests. Updated the repo onboarding flow so the procurement harness is the primary first-run path, added Make targets for the harness, and tightened Mirage’s safe-flow messaging so demo output reads cleanly.

## Decisions Made

- Chose onboarding depth over broader feature expansion
- Kept the domain in procurement/bidding because it already matched the repo’s current language
- Defined the example agent around an injected `get`/`post` client so tests can run in-process while demos still use the `httpx` Mirage client
- Kept core API changes minimal and only adjusted success messaging where the live demo exposed confusion

## Files Touched

- `examples/procurement_harness/__init__.py`
- `examples/procurement_harness/agent.py`
- `examples/procurement_harness/demo.py`
- `examples/procurement_harness/mocks.yaml`
- `examples/procurement_harness/policies.yaml`
- `examples/procurement_harness/README.md`
- `tests/test_procurement_harness.py`
- `tests/conftest.py`
- `Makefile`
- `README.md`
- `src/engine.py`

## Verification Performed

- `pytest tests/test_procurement_harness.py -v -s` passed
- `pytest tests/ -v -s` passed with 14 tests
- `python -m compileall src tests examples scripts` passed
- `python -m examples.procurement_harness.demo --help` passed
- live proxy verification passed for `python -m examples.procurement_harness.demo safe` against `uvicorn src.proxy:app` with the procurement harness config

## Open Risks

- Live demo verification was completed for the safe flow after the safe-output fix; the risky and unmatched flows were verified before that message cleanup but not rerun afterward
- Docker packaging for the procurement harness was not rechecked locally in this round

## Next Recommended Step

Use the procurement harness in videos and design-partner outreach, then collect friction from real users before expanding policy or mock capabilities.
