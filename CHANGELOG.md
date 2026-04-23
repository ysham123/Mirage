# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
