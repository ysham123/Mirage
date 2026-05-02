# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

Phase 2 work. See `docs/releases/v0.2.0.md` for what shipped in 0.2.0.

## [0.2.0] - 2026-05-03

Production runtime release. Mirage repositions from "CI for agent side
effects" to the open-source policy gateway for AI agents in
production. The same YAML policy file enforces a runtime gateway and
gates the CI build pre-merge. No LLM in the decision loop.

Release notes: [docs/releases/v0.2.0.md](docs/releases/v0.2.0.md)

### Added

- `mirage.policy`: `PolicyEvaluator` extracted as a pure, mock-free
  evaluator. Shared by both CI mode (`MirageEngine`) and the new
  gateway mode.
- `mirage.gateway`: production runtime gateway. Same policy file as
  CI, evaluated against real upstream traffic.
  - `passthrough` mode forwards every request to the upstream and logs
    policy decisions without blocking. The right starting mode for a
    new deployment.
  - `enforce` mode forwards when policy passes, blocks with HTTP 403
    when it fails. Same policy file, now load-bearing for production.
  - Unified outcome taxonomy across modes:
    `allowed` / `flagged` / `blocked` / `error`.
  - Trace events carry a `mode` discriminator so downstream tooling can
    distinguish gateway events from legacy CI events.
- `mirage gateway` CLI subcommand (`--upstream`, `--mode`,
  `--policies-path`, `--host`, `--port`, `--artifact-root`).
- Eleven new policy operators that express real production risks:
  `regex_match`, `not_regex_match`, `contains`, `not_contains`,
  `starts_with`, `not_starts_with`, `ends_with`, `length_lte`,
  `length_gte`, `host_in`, `host_not_in`. Config-load validation
  rejects bad regex strings, non-string starts/ends prefixes, negative
  length values, and empty host lists. Type mismatches at runtime
  return `passed=False` gracefully without raising.
- `examples/policies/`: five real-world example policies (PII
  redaction, prompt injection, outbound URL allowlist, cost guard,
  output length cap) plus a directory README explaining each and the
  load command.
- `mirage.integrations.openai_agents.wrap_with_mirage`: thin adapter
  for the OpenAI Agents SDK that routes tool calls through a Mirage
  gateway for a policy decision before the underlying tool runs.
  Lazy import; available via `pip install mirage-ci[openai-agents]`.
  Documented in `docs/INTEGRATIONS_OPENAI_AGENTS_SDK.md`.
- `mirage.metrics.ContainmentMetrics` plus
  `compute_containment_metrics` and `get_run_containment`. Surfaces
  containment rate (formula:
  `blocked / max(1, blocked + policy_violation_count + flagged)`),
  decision-latency p50/p95/p99 (per-policy evaluation), and
  time-to-decide p50/p95/p99 (gateway-internal request entry to
  decision). `OverviewSummary` gains a fleet-wide `containment_rate`.
- `PolicyDecision.decision_latency_us` captured by `PolicyEvaluator`
  using `time.perf_counter_ns()`. Gateway trace events now carry
  `time_to_decide_us`.
- `GET /api/runs/{run_id}/containment` console endpoint returning the
  `ContainmentMetrics` dataclass JSON.
- Containment row in the Next.js console run-detail stats bar
  (`Containment: 96.2%` or `Containment: not applicable`).
- Reproducible benchmark harness under `benchmarks/`. Three synthetic
  scenarios paired with the example policies (PII leak, prompt
  injection, cost runaway), JSON output reports, and a
  `bench` Makefile target. `BENCHMARKS.md` documents methodology and
  current numbers honestly.
- Console metrics `RunSummary`, `OverviewSummary`, and
  `EndpointSummary` expose `blocked_count` / `flagged_count` /
  `error_count` so dashboards surface gateway runs honestly.
- TypeScript types: `RunOutcome` union extended with `blocked` /
  `flagged` / `error`; `OverviewSummary` and `ConsoleRun` gain the new
  fields; sidebar + run-detail badges color the new outcomes
  correctly.
- `tests/test_gateway.py`, `tests/test_policy_operators.py`,
  `tests/test_example_policies.py`, `tests/test_metrics.py`,
  `tests/test_integration_openai_agents.py`, and
  `tests/test_benchmarks.py` add coverage of every new surface.
- `mirage.__version__` exposed as a top-level attribute.

### Changed

- `MirageEngine` delegates policy evaluation to `PolicyEvaluator`.
  Public API unchanged.
- `mirage.config.load_policies_only()` helper added; the gateway uses it
  instead of double-loading the policies file as both mocks and policies.
- README rewritten to lead with the production runtime gateway story.
  CI mode is now described as the safe-adoption pre-merge gate. Five
  new sections call out policy coverage, framework integrations,
  benchmarks, and an updated 'How Mirage is different' block.
- `pyproject.toml` description aligned with the new mission sentence;
  `openai-agents` extra added.

### Security

- README "Gateway forwarding behavior" section documenting which
  request headers Mirage strips, which it forwards, and the operator's
  responsibility to point `--upstream` at the right host. The gateway
  forwards `Authorization`, `Cookie`, and other application headers
  unchanged so upstream auth keeps working; pointing the gateway at an
  unintended host would forward those credentials with the request.

## [0.1.3] - 2026-04-26

Console redesign release. The Mirage review console (`ui/`) gets a full
visual rewrite to a precision-instrument aesthetic. Internal package
layout cleanup; no public API or behavior changes for `mirage-ci`
Python users since 0.1.2.

Release notes: [docs/releases/v0.1.3.md](docs/releases/v0.1.3.md)

### Changed

- Review console: redesigned with a precision-instrument visual language.
  Bricolage Grotesque + Geist + JetBrains Mono typography paired with a
  single NVIDIA-toned green accent. Tighter header chrome, sticky run
  context strip, denser stats bar, environment indicator in the top bar.
- `README.md` screenshot regenerated against the redesigned console.
- `README.md`: PyPI version and Python version badges added above the
  fold so visitors can see the published distribution at a glance.

### Removed

- `src/` package re-export shim. Tests, Dockerfile, and the CI smoke
  test now import from the `mirage` package directly. `pip install
  mirage-ci` has always exposed `mirage` as the public import path,
  so this is no user-facing change.

## [0.1.2] - 2026-04-23

First-run UX release. Also includes README, documentation, and CI recipe
updates that shipped after 0.1.1 to keep the install story consistent with
the published `mirage-ci` package.

Release notes: [docs/releases/v0.1.2.md](docs/releases/v0.1.2.md)

### Added

- `MirageProxyUnreachableError`, raised by `MirageSession` when the configured
  Mirage proxy is not reachable. The error message names the expected proxy
  URL and the exact `uvicorn` command to start it, so first-run users see an
  actionable hint instead of a raw `httpx.ConnectError` traceback.

### Changed

- `README.md` "See It In 60 Seconds" section rewritten as a pip-install-only
  demo that runs against the bundled default mocks and policies. The previous
  block depended on `make` targets that only existed in a repo checkout, which
  contradicted the quickstart right below it.
- `docs/FIRST_INTEGRATION.md` and `docs/CI_INTEGRATION.md` now install Mirage
  with `pip install mirage-ci` instead of `make install`. The CI recipe
  previously failed when copied into a user repo because there was no
  `Makefile` in their tree.
- `examples/procurement_harness/README.md` clarifies that the bundled demo
  requires a repo checkout, and points readers who only want to integrate
  Mirage at `docs/FIRST_INTEGRATION.md`.

## [0.1.1] - 2026-04-23

Documentation and packaging release. No behavior changes.

Release notes: [docs/releases/v0.1.1.md](docs/releases/v0.1.1.md)

### Fixed

- Quickstart install path. The previous
  `pip install --no-build-isolation -e '.[dev]'` line fails on a clean venv
  with `ModuleNotFoundError: setuptools`. The README now opens with
  `pip install mirage-ci` and states the Python 3.11+ requirement up front.
- Clarified that the PyPI distribution name is `mirage-ci` while the import
  name remains `mirage`.

### Added

- `Mirage vs. Adjacent Tools` section in the README, covering
  `pytest-httpx` / `respx`, `pytest-httpserver`, `VCR.py`, `responses`,
  `WireMock` / `mitmproxy`, and runtime LLM-judge guards, plus a
  `When not to use Mirage today` bullet list.
- `Source install` subsection under Contributing documenting the
  editable/from-source install for contributors.
- First PyPI release under the `mirage-ci` name.

### Changed

- `WORK_LOG_*.txt` added to `.gitignore`.

## [0.1.0] - 2026-04-19

Release notes: [docs/releases/v0.1.0.md](docs/releases/v0.1.0.md)

### Added

- Python-first `MirageSession` integration path for agent workflows
- Run-level CLI gating and summary commands
- Procurement harness onboarding flow
- Trace-backed action review console
- Next.js client over the shared console API
- Open-source repo hygiene: Code of Conduct, Security Policy, issue templates,
  pull request template, and Python package metadata.
- Public Python package surface under `mirage`, including `mirage.proxy`,
  `mirage.pytest_plugin`, and the `mirage` CLI entry point.

### Changed

- Mirage now resolves default trace output under the current working directory
  and falls back to bundled example configs outside the source tree.
