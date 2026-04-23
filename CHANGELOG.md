# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
