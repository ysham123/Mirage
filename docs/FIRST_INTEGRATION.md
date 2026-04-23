# First Integration

This is the zero-to-clean-run path for a Python engineer who can route outbound
HTTP through a client boundary and wants to put Mirage in front of it. Budget:
30 minutes.

If you just want to watch Mirage work on a pre-built harness, run the
procurement demo from the top-level [README](../README.md) instead.

If your agent does not already use `httpx` directly, start with
[INTEGRATION_PATTERNS.md](INTEGRATION_PATTERNS.md) first. Mirage only needs the
outbound action path to cross a client boundary you control.

## Prereqs

- Python 3.11+
- An existing agent, SDK wrapper, or gateway layer that makes outbound HTTP
  calls you can route through a client boundary
- A shell with two tabs free (one for the proxy, one for the agent)

## 1. Install

Install Mirage from PyPI into the same environment as your agent:

```bash
pip install mirage-ci
```

The distribution name is `mirage-ci`; the import name is `mirage`. You do not
need to clone this repository to integrate Mirage into your own agent.

## 2. Write a mocks file for the external API your agent calls

Create `my_mocks.yaml`. Mirage returns the `response.json` body for any request
that matches the given method and path.

```yaml
mocks:
  - name: get_customer
    method: GET
    path: /v1/customers/CUST-001
    response:
      status_code: 200
      json:
        customer_id: CUST-001
        status: active

  - name: create_order
    method: POST
    path: /v1/orders
    response:
      status_code: 201
      json:
        order_id: ORD-123
        status: pending
```

See [examples/procurement_harness/mocks.yaml](../examples/procurement_harness/mocks.yaml)
for a larger reference.

## 3. Write a policies file

Create `my_policies.yaml`. One rule is enough to start. Each rule extracts a
field from the request body and checks it against an operator.

```yaml
policies:
  - name: enforce_order_limit
    method: POST
    path: /v1/orders
    field: total_amount
    operator: lte
    value: 1000
    message: Agents cannot place orders above $1000 without review.
```

Supported operators: `exists`, `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `in`,
`not_in`. See [examples/procurement_harness/policies.yaml](../examples/procurement_harness/policies.yaml).

## 4. Validate config before you start the proxy

Run:

```bash
python -m mirage.cli validate-config \
  --mocks-path ./my_mocks.yaml \
  --policies-path ./my_policies.yaml
```

You should see:

```
Mirage config valid.
Mocks: 2 from my_mocks.yaml
Policies: 1 from my_policies.yaml
```

If this fails, Mirage names the file, entry index, and field before you even
boot the proxy.

## 5. Start the Mirage proxy with your config

In one terminal:

```bash
MIRAGE_MOCKS_PATH=./my_mocks.yaml \
MIRAGE_POLICIES_PATH=./my_policies.yaml \
python -m uvicorn mirage.proxy:app --reload
```

Mirage now listens on `http://localhost:8000`.

## 6. Swap your agent's HTTP client for `MirageSession`

Before:

```python
import httpx

with httpx.Client(base_url="https://api.example.com") as client:
    agent.run(client)
```

After:

```python
from mirage import MirageSession

with MirageSession(run_id="first-run") as mirage:
    agent.run(mirage.client)  # mirage.client is an httpx.Client
    summary = mirage.assert_clean()
```

If your agent has its own method wrappers (`client.get(...)`), `MirageSession`
also exposes `get`, `post`, `put`, `patch`, `delete` directly — no client passthrough
needed.

## 7. Run once and read the summary

In a second terminal:

```bash
python your_agent.py
python -m mirage.cli summarize-run --run-id first-run
```

A clean run looks like:

```
Mirage run: first-run
Trace path: artifacts/traces/first-run.json
Summary: 2 action(s), 2 safe, 0 risky
Result: clean run
```

## 8. Break a policy on purpose

Make the agent send `total_amount: 9999`. Rerun steps 6. You should see:

```
Mirage run: first-run
Trace path: artifacts/traces/first-run.json
Summary: 1 action(s), 0 safe, 1 risky
Risky actions:
- [policy_violation] POST /v1/orders (event 1, mock=create_order): enforce_order_limit: Agents cannot place orders above $1000 without review. (field 'total_amount' must satisfy lte 1000 but got 9999)
  Next: Tighten the agent or relax this policy in policies.yaml.
```

That `Next:` line tells you exactly where to look. If you see
`[unmatched_route]`, the agent called a route you didn't mock. If you see
`[config_error]`, the error message names the file, entry index, and field
that's wrong, plus an example of a correct entry.

## 9. Wire it into pytest

In your repo's `conftest.py`:

```python
from mirage.pytest_plugin import mirage_session  # re-export as fixture
```

Then in any test:

```python
def test_agent_places_valid_order(mirage_session):
    agent = MyAgent(mirage_session.client)
    agent.place_order(total_amount=50)
    # teardown auto-asserts clean; no extra call needed
```

The fixture derives a stable run_id from the test's nodeid and calls
`assert_clean()` on teardown, so any risky action fails the test with a
human-readable summary.

If you need to point tests at a non-default proxy URL, artifact root, or a
negative test that intentionally keeps a risky run, add an options fixture in
that same `conftest.py`:

```python
import pytest

from mirage.pytest_plugin import mirage_session


@pytest.fixture
def mirage_session_options(tmp_path):
    return {
        "base_url": "http://127.0.0.1:8000",
        "artifact_root": tmp_path / "artifacts" / "traces",
        "auto_assert": False,
    }
```

`auto_assert=False` is useful for tests that intentionally inspect a
`policy_violation` or `unmatched_route` instead of failing in fixture teardown.

## 10. Next: CI

See [CI_INTEGRATION.md](CI_INTEGRATION.md) for the GitHub Actions and script-level
gating patterns.

## Common failure modes

| Symptom | What it means | Fix |
|---|---|---|
| `httpx.ConnectError: Connection refused` on localhost:8000 | The proxy isn't running | Start it with the command in step 4 |
| `[unmatched_route]` in the summary | Agent hit a route you didn't mock | Add a mock entry for that `method` + `path` |
| `[config_error]` with a file/field pointer | YAML schema mismatch | The message tells you the entry index and field — fix and rerun |
| `has no trace at ...` in the summary | Agent ran but never talked to Mirage | Confirm the agent's client uses `MirageSession.client` (or pass `base_url=MIRAGE_PROXY_URL`) |
