# 2026-03-26 Phase 2 Detailed Review

## Why This Work Was Done

This work implemented the Mirage Phase 2 plan: move the repo from a narrow proof-of-concept into a more usable private-alpha developer workflow.

The main goals were:

- make Mirage easier to integrate from Python agent code
- make failures easier to understand in tests and CI
- fix packaging gaps so local and container runs behave the same way
- expand the example and test surface beyond one demo flow
- create a persistent review artifact so agentic work can be audited later

## What Changed And Why

### 1. Core engine behavior

Files:

- `src/engine.py`

Changes:

- Added explicit Mirage outcomes: `allowed`, `policy_violation`, `unmatched_route`, `config_error`
- Added clearer result metadata: `run_id`, `message`, failed-decision helpers, decision summaries
- Added config error handling so missing or invalid config becomes a traceable Mirage result instead of a raw crash
- Added environment variable support for config and artifact paths
- Added richer trace events with `run_id`, `outcome`, and `message`

Why:

- The original repo could record whether policy passed, but it did not give a clean outcome model for CI or downstream tooling
- Config failures needed to become explicit product behavior rather than implicit exceptions
- A Phase 2 tool needs machine-readable and human-readable outcomes, not just internal booleans

### 2. FastAPI proxy boundary

Files:

- `src/proxy.py`

Changes:

- Added `create_app()` so the proxy can be instantiated cleanly in tests
- Added Mirage response headers such as:
  - `X-Mirage-Outcome`
  - `X-Mirage-Policy-Passed`
  - `X-Mirage-Trace-Path`
  - `X-Mirage-Decision-Summary`
- Preserved existing mocked response bodies while surfacing Mirage metadata through headers

Why:

- The proxy needed a stable external contract for tests and agent integrations
- Headers are the least disruptive way to expose Mirage behavior without changing the mocked API response shape
- App-factory structure makes proxy-level tests straightforward and isolated

### 3. Python `httpx` integration

Files:

- `src/httpx_client.py`
- `src/__init__.py`

Changes:

- Added `create_mirage_client()` for a low-friction Python entry point
- Added `mirage_response_report()` to parse Mirage metadata headers into a structured report
- Added `assert_mirage_response_safe()` to make unsafe requests fail clearly in test code
- Re-exported the new integration helpers from `src/__init__.py`

Why:

- The 90-day plan called for a low-friction developer entry point for `httpx` and/or `requests`
- `httpx` was chosen as the first supported client because it keeps the surface narrow and useful
- A simple helper/API is necessary if Mirage is going to feel like developer tooling instead of a raw proxy demo

### 4. Tests and fixtures

Files:

- `tests/conftest.py`
- `tests/test_agent_safety.py`
- `tests/test_proxy_routes.py`
- `tests/test_httpx_client.py`

Changes:

- Reworked test fixtures so they create temporary Mirage config per test run
- Expanded engine tests to cover:
  - safe request
  - unsafe request
  - unmatched route
  - missing config
- Added proxy tests for metadata headers, non-JSON payload handling, and config errors
- Added tests for the new `httpx` helper defaults and header behavior

Why:

- The previous test surface only covered the narrow engine path
- Hermetic fixtures are necessary if packaging and config resolution are part of the product promise
- Phase 2 requires coverage for the external developer workflow, not just internal engine behavior

### 5. Example scenarios

Files:

- `examples/rogue_agent.py`
- `examples/safe_agent.py`
- `examples/unmatched_route.py`
- `Makefile`

Changes:

- Updated the existing rogue agent example to use the new Mirage `httpx` helper and print Mirage outcome details
- Added a safe example flow
- Added an unmatched route example flow
- Added `make agent-safe` and `make agent-unmatched`

Why:

- The 90-day plan explicitly called for three canonical scenarios
- The examples now reflect the actual intended Phase 2 workflow instead of bypassing the new integration helpers
- Example diversity matters for demos, onboarding, and design-partner conversations

### 6. Config and runtime packaging

Files:

- `mocks.yaml`
- `policies.yaml`
- `Dockerfile`
- `docker-compose.yml`

Changes:

- Converted root config files into cleaner YAML instead of JSON-shaped content in `.yaml` files
- Updated Docker to include config files, examples, and an artifact directory
- Updated Compose to mount config, examples, and artifacts alongside source

Why:

- The original packaging path was broken: containerized Mirage would not reliably find `mocks.yaml` and `policies.yaml`
- Phase 2 needs local, test, and container runs to follow the same mental model
- Using actual YAML improves legibility for configuration-driven usage

### 7. Repo documentation

Files:

- `README.md`

Changes:

- Rewrote the README around the implemented Phase 2 workflow
- Documented the four Mirage outcomes
- Added the `httpx` integration example
- Documented environment variables
- Added the three example flows
- Updated the repo structure section to include the new integration and worklog artifacts

Why:

- The README needed to describe what Mirage actually does now, not just the original Phase 1 shape
- A private-alpha repo needs a usable quickstart, not only product framing

### 8. CI and reviewability

Files:

- `.github/workflows/ci.yml`
- `docs/worklog/INDEX.md`
- `docs/worklog/2026-03-26-phase-2-foundation.md`
- `docs/worklog/2026-03-26-phase-2-detailed-review.md`

Changes:

- Added GitHub Actions CI for test execution and Docker build/smoke checks
- Added a markdown worklog index
- Added a concise implementation log
- Added this detailed review log

Why:

- Mirage is positioned as CI for agent side effects, so the repo needed real CI wiring
- You asked for a durable way to review agentic work by task, explanation, and file list
- Markdown is the simplest high-signal artifact for human review across sessions

## Files Added

- `.github/workflows/ci.yml`
- `docs/worklog/2026-03-26-phase-2-detailed-review.md`
- `docs/worklog/2026-03-26-phase-2-foundation.md`
- `docs/worklog/INDEX.md`
- `examples/safe_agent.py`
- `examples/unmatched_route.py`
- `src/httpx_client.py`
- `tests/test_httpx_client.py`
- `tests/test_proxy_routes.py`

## Files Updated

- `Dockerfile`
- `Makefile`
- `README.md`
- `docker-compose.yml`
- `examples/rogue_agent.py`
- `mocks.yaml`
- `policies.yaml`
- `src/__init__.py`
- `src/engine.py`
- `src/proxy.py`
- `tests/conftest.py`
- `tests/test_agent_safety.py`

## Verification

Verified successfully:

- `pytest tests/ -v -s`
- `python -m compileall src tests examples`
- local engine smoke test for an allowed request and trace write

Not fully verified locally:

- Docker build and runtime smoke

Reason:

- the local Docker daemon was not running on the machine, so the packaging fixes could not be validated end to end here

## Remaining Risk

- Docker behavior is still partially unverified locally even though the file-level packaging issue was addressed
- Mirage metadata headers are useful now, but they are not yet a versioned public integration contract

## Recommended Use Of This File

Use this file as the “what Codex changed and why” artifact for this implementation round.

If you want to review future work quickly, the intended path is:

1. open `docs/worklog/INDEX.md`
2. open the task entry
3. review the goal, decisions, files, verification, and open risks
