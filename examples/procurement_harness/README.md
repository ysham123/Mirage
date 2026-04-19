# Procurement Harness

This is the primary Mirage onboarding path for private-alpha users.

It models a small procurement workflow with one realistic sequence:

1. look up an approved supplier
2. submit a bid through Mirage
3. inspect whether Mirage marked the action as `allowed`, `policy_violation`, or `unmatched_route`

## First Run

Install dependencies:

```bash
make install
```

Start the Mirage proxy with the procurement harness config:

```bash
make proxy-procurement
```

In a second terminal, run one of the demo scenarios:

```bash
make procurement-demo-safe
make procurement-demo-risky
make procurement-demo-unmatched
```

Summarize or gate the resulting run directly from the shell:

```bash
make mirage-summary RUN_ID=procurement-risky-demo
make mirage-gate RUN_ID=procurement-risky-demo
```

Run the harness tests:

```bash
make test-procurement
```

Run the shared console API plus legacy HTML shell over the same workflow:

```bash
make demo-ui
```

Then open `http://127.0.0.1:5100`.

If you want the richer Next.js client instead of the legacy shell:

```bash
make ui-install
make ui-dev-local
```

Then open `http://127.0.0.1:3000`.

## Scenarios

- `safe`: approved supplier lookup followed by a compliant bid
- `risky`: approved supplier lookup followed by an out-of-bounds bid
- `unmatched`: agent tries to create a supplier on a route Mirage does not mock

## Files

- `agent.py`: procurement workflow abstraction
- `demo.py`: CLI demo entry point built on `MirageSession`
- `mocks.yaml`: procurement harness mock routes
- `policies.yaml`: procurement harness policy rules
