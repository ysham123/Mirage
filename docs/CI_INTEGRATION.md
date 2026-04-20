# CI Integration

Mirage has two first-class CI patterns. Pick one.

## Pattern 1: pytest-native (recommended)

If your agent already has tests, this is the lowest-friction path. The
`mirage_session` fixture asserts a clean run on teardown, so a risky action
fails the test naturally.

In `conftest.py`:

```python
from mirage.pytest_plugin import mirage_session  # re-export
```

Optional override when CI needs a non-default proxy URL, artifact root, or a
negative test that should inspect risky output without failing in teardown:

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

In a test:

```python
def test_order_flow(mirage_session):
    agent = MyAgent(mirage_session.client)
    agent.place_order(total_amount=50)
```

No extra CI plumbing. Your existing `pytest` step fails the build.

## Pattern 2: script-level gate

Use this when the agent isn't driven from pytest (e.g., a CLI run, a notebook
export, a scheduled script). Run the agent, then gate the run.

```bash
MIRAGE_RUN_ID=nightly-$(date +%F) python my_agent.py
python -m mirage.cli gate-run --run-id nightly-$(date +%F)
```

`gate-run` exits non-zero when:

- the run has any `policy_violation`, `unmatched_route`, or `config_error` action
- the trace for the given run_id doesn't exist

See [src/cli.py](../src/cli.py) for the exact exit codes.

## GitHub Actions workflow

```yaml
name: mirage-gate
on: [pull_request]

jobs:
  mirage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install
        run: make install

      - name: Validate Mirage config
        run: |
          python -m mirage.cli validate-config \
            --mocks-path ./my_mocks.yaml \
            --policies-path ./my_policies.yaml

      - name: Start Mirage proxy
        run: |
          MIRAGE_MOCKS_PATH=./my_mocks.yaml \
          MIRAGE_POLICIES_PATH=./my_policies.yaml \
          nohup python -m uvicorn mirage.proxy:app --host 127.0.0.1 --port 8000 &
          for i in {1..20}; do
            curl -fsS http://127.0.0.1:8000/health && break
            sleep 0.5
          done

      - name: Run agent
        env:
          MIRAGE_RUN_ID: ci-${{ github.run_id }}
        run: python my_agent.py

      - name: Gate the run
        run: python -m mirage.cli gate-run --run-id ci-${{ github.run_id }}

      - name: Upload Mirage trace
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: mirage-trace-${{ github.run_id }}
          path: artifacts/traces/ci-${{ github.run_id }}.json
```

The `if: always()` on the upload step means you still get the trace on a failed
gate — which is usually exactly when you want to inspect it.

## Reading a failing run in CI logs

`gate-run` prints the same summary you'd see locally. A failing run looks like:

```
Mirage run: ci-1742391
Trace path: artifacts/traces/ci-1742391.json
Summary: 3 action(s), 2 safe, 1 risky
Risky actions:
- [policy_violation] POST /v1/orders (event 3, mock=create_order): enforce_order_limit: Agents cannot place orders above $1000 without review. (field 'total_amount' must satisfy lte 1000 but got 9999)
  Next: Tighten the agent or relax this policy in policies.yaml.
```

Each risky action includes:

- the outcome (`policy_violation`, `unmatched_route`, or `config_error`)
- the method, path, and matched mock (or `none` for unmatched)
- the specific policy that failed and what the value was
- a `Next:` hint with the concrete remediation

Pair that with the uploaded trace artifact and a reviewer can diagnose the
failure without rerunning the build.
