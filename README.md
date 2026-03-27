# Mirage

Mirage is CI for agent side effects.

It sits between an agent and external APIs, intercepts outbound HTTP actions, evaluates them against policy, returns safe mocked responses, and writes deterministic traces for tests and CI.

## What Mirage Does Today

Mirage currently gives a Python-first developer workflow for:

- config-driven HTTP mocks
- config-driven policy checks
- deterministic run-scoped traces
- clear request outcomes for debugging and CI
- an `httpx` helper for agent integrations
- local, test, and container-friendly execution

Mirage currently reports one of four outcomes for every intercepted request:

- `allowed`
- `policy_violation`
- `unmatched_route`
- `config_error`

## Quickstart

Install dependencies:

```bash
make install
```

Run the primary procurement harness onboarding flow:

```bash
make proxy-procurement
```

In a second terminal, run the safe procurement demo:

```bash
make procurement-demo-safe
```

Run the procurement harness tests:

```bash
make test-procurement
```

Run with Docker:

```bash
docker compose up --build
```

That Docker path now starts the Mirage proxy with the procurement harness config on `http://localhost:8000`.

## `httpx` Integration

Mirage now includes a lightweight `httpx` entry point for Python agent tests:

```python
from src.httpx_client import (
    assert_mirage_response_safe,
    create_mirage_client,
    mirage_response_report,
)

with create_mirage_client(run_id="demo-run") as client:
    response = client.post(
        "/v1/submit_bid",
        json={"contract_id": "STANDARD-7", "bid_amount": 7500},
    )
    report = mirage_response_report(response)
    assert_mirage_response_safe(response)
    print(report.trace_path)
```

Mirage adds response metadata headers so tests and agents can inspect what happened without changing the mocked response body:

- `X-Mirage-Outcome`
- `X-Mirage-Policy-Passed`
- `X-Mirage-Trace-Path`
- `X-Mirage-Decision-Summary`

## Config

The primary onboarding config now lives in:

- [`examples/procurement_harness/mocks.yaml`](examples/procurement_harness/mocks.yaml)
- [`examples/procurement_harness/policies.yaml`](examples/procurement_harness/policies.yaml)

The repo-root [`mocks.yaml`](mocks.yaml) and [`policies.yaml`](policies.yaml) remain as the engine's default fallback config when no harness-specific paths are provided.

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

Optional environment variables:

- `MIRAGE_PROXY_URL`
- `MIRAGE_RUN_ID`
- `MIRAGE_MOCKS_PATH`
- `MIRAGE_POLICIES_PATH`
- `MIRAGE_ARTIFACT_ROOT`

## Procurement Harness

The default onboarding path now lives in [`examples/procurement_harness/`](examples/procurement_harness).

It gives one coherent workflow instead of isolated request demos:

- look up an approved supplier
- submit a compliant or risky bid
- inspect Mirage outcomes and trace paths

Primary commands:

```bash
make proxy-procurement
make procurement-demo-safe
make procurement-demo-risky
make procurement-demo-unmatched
make test-procurement
```

Harness docs:

- [`examples/procurement_harness/README.md`](examples/procurement_harness/README.md)

## Demo UI

The founder demo UI is a thin layer over the same procurement harness flow. It runs the scenarios through Mirage's FastAPI proxy boundary and shows the request, Mirage outcome, mocked response, and trace.

Start it with:

```bash
make demo-ui
```

Then open `http://127.0.0.1:5100`. Override the port with `PORT=5101 make demo-ui` if needed.

## Example Scenarios

This repo now includes three canonical example flows:

- [`examples/procurement_harness/`](examples/procurement_harness): realistic private-alpha procurement harness
- [`examples/safe_agent.py`](examples/safe_agent.py): safe request passes policy checks
- [`examples/rogue_agent.py`](examples/rogue_agent.py): unsafe request is flagged while control flow continues
- [`examples/unmatched_route.py`](examples/unmatched_route.py): unmatched route fails clearly

## Worklog

Create a new implementation review entry with:

```bash
make worklog TITLE="Short Task Title"
```

The template and index live in [`docs/worklog/`](docs/worklog).

## Repo Structure

- [`examples/procurement_harness/`](examples/procurement_harness): primary private-alpha onboarding harness
- [`demo_ui/`](demo_ui): founder demo UI over the procurement harness
- [`src/engine.py`](src/engine.py): core request handling, outcomes, and trace writes
- [`src/proxy.py`](src/proxy.py): FastAPI proxy boundary and Mirage response headers
- [`src/httpx_client.py`](src/httpx_client.py): Python `httpx` helper and response assertions
- [`tests/`](tests): engine, proxy, and `httpx` helper coverage
- [`docs/worklog/`](docs/worklog): per-task review log for agentic development

## Supporting Docs

- [`PROBLEM_STATEMENT.md`](PROBLEM_STATEMENT.md): concise founder-facing problem and solution framing
- [`PROJECT_NOTES.md`](PROJECT_NOTES.md): product thesis and implementation notes
- [`MIRAGE_90_DAY_PLAN.md`](MIRAGE_90_DAY_PLAN.md): current 90-day product and distribution plan
