# Contributing to Mirage

Thanks for your interest in contributing. This doc covers the local dev loop
and what to expect when you open a PR.

Please also read:

- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- [`SECURITY.md`](SECURITY.md)
- [`CHANGELOG.md`](CHANGELOG.md)

## Local Dev

Install Python deps:

```bash
make install
```

Run the test suite:

```bash
make test
```

Run the proxy with the bundled procurement harness config:

```bash
make proxy-procurement
```

In another terminal, drive the demo:

```bash
make procurement-demo-safe
make procurement-demo-risky
```

For the Next.js console (optional):

```bash
make ui-install
make ui-dev
```

## Code Style

- Python: match the existing style. Type hints on public functions, no
  docstrings unless the behavior is non-obvious.
- TypeScript/React: follow the existing component structure under `ui/`.
- Config: `mocks.yaml` and `policies.yaml` entries should include a `name` and
  a `message` — they show up in traces and error output.

## Tests

- Every behavior change needs a test. Put Python tests under `tests/` and UI
  tests under `ui/tests/`.
- `make test` must pass before you open a PR.

## Commits and PRs

- Keep commits focused. One logical change per commit is preferred.
- PR descriptions should explain the *why* — the *what* is visible in the diff.
- Link related issues.

## Reporting Bugs

Open an issue with:

- What you ran (command, config, inputs)
- What you expected
- What happened (include the trace file and the `summarize-run` output if a
  run is involved)

## Security

If you find a security vulnerability, do not open a public issue. Follow
[`SECURITY.md`](SECURITY.md) instead.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
