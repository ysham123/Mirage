# Mirage

Mirage is CI for agent side effects.

It sits between an agent and external APIs, intercepts outbound HTTP actions, evaluates them against policy, returns safe mocked responses, and writes deterministic traces for tests and CI.

## What Mirage Does Today

Mirage currently gives a Python-first developer workflow for:

- config-driven HTTP mocks
- config-driven policy checks
- deterministic run-scoped traces
- clear request outcomes for debugging and CI
- an action review console over trace artifacts
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

### Integrate your own agent

The canonical Mirage integration is `MirageSession`. One run ID, an `httpx`
client surface the agent uses directly, one assertion point for CI.

```python
from src import MirageSession

with MirageSession(run_id="demo-run") as mirage:
    response = mirage.post(
        "/v1/submit_bid",
        json={"contract_id": "STANDARD-7", "bid_amount": 7500},
    )
    summary = mirage.assert_clean()
    print(summary.trace_path)
```

For the full 30-minute walkthrough of pointing Mirage at your own agent, see
[`docs/FIRST_INTEGRATION.md`](docs/FIRST_INTEGRATION.md). For CI gating
recipes (pytest and GitHub Actions), see
[`docs/CI_INTEGRATION.md`](docs/CI_INTEGRATION.md).

### Try the bundled procurement harness

If you want to see Mirage working on a realistic pre-built workflow before
integrating your own agent:

```bash
make proxy-procurement
```

In a second terminal:

```bash
make procurement-demo-safe
make test-procurement
```

Run with Docker:

```bash
docker compose up --build
```

That Docker path starts the Mirage proxy with the procurement harness config on `http://localhost:8000`.

## MirageSession

MirageSession is the recommended path for:

- local developer runs
- `pytest` integration tests
- CI gates on risky actions

For agent code that already expects a client-like object:

```python
from examples.procurement_harness.agent import ProcurementAgent
from src import MirageSession

with MirageSession(run_id="procurement-safe") as mirage:
    agent = ProcurementAgent(mirage)
    result = agent.run_compliant_bid_workflow()
    summary = mirage.assert_clean()
    print(result.action.mirage.outcome)
    print(summary.to_text())
```

### Alternative: per-response primitives

If you want per-response access instead of a run-level session, the lower-level
`httpx` primitives remain available:

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

## CI Gating

Mirage now has a run-level CLI for CI or shell workflows:

```bash
make mirage-summary RUN_ID=procurement-risky-demo
make mirage-gate RUN_ID=procurement-risky-demo
```

Equivalent direct commands:

```bash
python -m src.cli summarize-run --run-id procurement-risky-demo
python -m src.cli gate-run --run-id procurement-risky-demo
```

`gate-run` exits non-zero when the run is risky or missing, so it can fail CI directly.

For complete GitHub Actions and pytest recipes, see
[`docs/CI_INTEGRATION.md`](docs/CI_INTEGRATION.md).

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

## Action Review Console

The demo UI now doubles as a lightweight action review console. It reads Mirage trace artifacts, shows aggregate action metrics, surfaces recent risky runs, and lets you drill into one run at a time.

It still supports the scenario launcher for founder demos, but the primary value of the UI is now:

- aggregate action counts across runs
- review queue for recent runs that need attention
- top endpoints by action volume
- top policy failures
- overview-first run detail with request, outcome, policy reasoning, and trace
- per-run graph view for decision flow review

Start it with:

```bash
make demo-ui
```

Then open `http://127.0.0.1:5100`. Override the port with `PORT=5101 make demo-ui` if needed.

For live demos, use the terminal-first script in [`docs/live-demo-script.md`](docs/live-demo-script.md).

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

- [`docs/FIRST_INTEGRATION.md`](docs/FIRST_INTEGRATION.md): 30-minute walkthrough for integrating your own `httpx` agent
- [`docs/CI_INTEGRATION.md`](docs/CI_INTEGRATION.md): pytest and GitHub Actions gating recipes
- [`PROBLEM_STATEMENT.md`](PROBLEM_STATEMENT.md): concise founder-facing problem and solution framing
- [`PROJECT_NOTES.md`](PROJECT_NOTES.md): product thesis and implementation notes
- [`MIRAGE_90_DAY_PLAN.md`](MIRAGE_90_DAY_PLAN.md): current 90-day product and distribution plan
- [`docs/live-demo-script.md`](docs/live-demo-script.md): recommended founder live demo flow
