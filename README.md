# Mirage

Mirage is CI for agent side effects.

It sits between an agent and external APIs, intercepts outbound HTTP actions, evaluates them against policy, returns safe mocked responses, and writes deterministic traces for tests and CI.

## Problem Statement

AI agents are starting to do more than generate text. They can call APIs, submit transactions, update systems, and trigger operational workflows.

That creates a testing gap. Teams need a reliable way to test what an agent attempted to do before those actions hit production.

Existing tools do not fully solve that problem:

- eval tools mostly focus on output quality
- runtime security tools focus on production-time defense
- ordinary mocks do not capture policy decisions or produce useful traces for agent behavior

Mirage focuses on the missing layer: pre-production validation of agent actions.

## What Mirage Does

Mirage gives engineering teams a developer-native way to:

- intercept outbound HTTP actions from an agent
- evaluate those actions against configurable policies
- return schema-valid mocked responses without breaking control flow
- write deterministic traces for local debugging and CI
- fail tests when an agent would have taken an unsafe or out-of-bounds action

## Proof In This Repo

This repository already proves the first useful product loop:

1. an agent request is intercepted
2. a mock route is matched
3. a policy is evaluated against the payload
4. a mocked response is returned
5. a run-scoped trace is written
6. the result is asserted in `pytest`

Current proof points:

- config-driven engine in `src/engine.py`
- config loading and validation in `src/config.py`
- FastAPI proxy boundary in `src/proxy.py`
- deterministic trace artifacts in `src/trace.py`
- end-to-end tests in `tests/test_agent_safety.py`

## Current MVP

Mirage currently supports:

- Python-first local engine
- config-driven HTTP mocks
- config-driven policy checks
- deterministic run-scoped traces
- `pytest`-friendly validation

Current example flow:

1. An agent sends `POST /v1/submit_bid`
2. Mirage intercepts the request
3. Mirage evaluates `bid_amount <= 10000`
4. Mirage returns a mocked success response
5. Mirage writes a trace artifact for assertions and CI

Mirage currently does not try to be:

- a broad AI safety platform
- a generic observability platform
- a runtime security product
- a full enterprise governance suite

## Quickstart

Install dependencies:

```bash
make install
```

Run the proxy:

```bash
make proxy
```

Run the example agent:

```bash
make agent
```

Run tests:

```bash
make test
```

## Config

Mocks are defined in [`mocks.yaml`](mocks.yaml) and policies are defined in [`policies.yaml`](policies.yaml).

Example policy:

```yaml
policies:
  - name: enforce_bid_limit
    method: POST
    path: /v1/submit_bid
    field: bid_amount
    operator: lte
    value: 10000
    message: Agents cannot submit bids above the approved threshold.
```

## Repo Structure

- [`src/engine.py`](src/engine.py): core request handling and policy evaluation
- [`src/proxy.py`](src/proxy.py): FastAPI proxy boundary
- [`src/config.py`](src/config.py): config loading and schema validation
- [`src/trace.py`](src/trace.py): run-scoped trace artifacts
- [`tests/test_agent_safety.py`](tests/test_agent_safety.py): end-to-end MVP validation

## Supporting Docs

- [`PROBLEM_STATEMENT.md`](PROBLEM_STATEMENT.md): concise founder-facing problem and solution framing
- [`PROJECT_NOTES.md`](PROJECT_NOTES.md): product thesis and implementation notes
- [`MIRAGE_90_DAY_PLAN.md`](MIRAGE_90_DAY_PLAN.md): current 90-day product and distribution plan
