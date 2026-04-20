# Integration Patterns

Mirage is strongest when your agent's side effects cross an HTTP boundary you
control.

That boundary does not need to be your whole orchestration stack. Mirage only
needs the outbound action path, especially the risky mutation paths, to route
through the local proxy.

## Choose Your Path

- Your agent already uses `httpx` directly: use [`MirageSession`](../README.md#miragesession).
- Your SDK or client lets you override `base_url`, `transport`, or the HTTP
  client: point that boundary at Mirage.
- Your framework hides the transport details: wrap the side-effecting calls in
  your own gateway layer and test that layer with Mirage.

## Pattern 1: Direct `httpx`

This is the cleanest integration path today.

```python
from mirage import MirageSession

with MirageSession(run_id="demo-run") as mirage:
    response = mirage.post("/v1/orders", json={"total_amount": 50})
    summary = mirage.assert_clean()
    print(summary.to_text())
```

## Pattern 2: You Can Override A Base URL Or HTTP Client

If your SDK or wrapper lets you choose the target base URL or inject an HTTP
client, route that boundary through Mirage instead of the real API.

```python
import httpx

from mirage import MirageSession


class OrdersGateway:
    def __init__(self, client: httpx.Client):
        self.client = client

    def create_order(self, payload: dict) -> httpx.Response:
        return self.client.post("/v1/orders", json=payload)


with MirageSession(run_id="orders-pr-128") as mirage:
    gateway = OrdersGateway(mirage.client)
    gateway.create_order({"total_amount": 50})
    mirage.assert_clean()
```

If your SDK accepts a `base_url` but not a raw client, point it at
`http://127.0.0.1:8000` while Mirage is running.

## Pattern 3: Your Framework Hides HTTP

Do not start by trying to retrofit Mirage into every layer of the framework.
Wrap the mutation boundary you care about and route that through Mirage.

```python
import httpx

from mirage import MirageSession


class BillingActions:
    def __init__(self, client: httpx.Client):
        self.client = client

    def create_invoice(self, amount: int) -> httpx.Response:
        return self.client.post("/v1/invoices", json={"amount": amount})


class AgentWorkflow:
    def __init__(self, billing: BillingActions):
        self.billing = billing

    def run(self) -> None:
        self.billing.create_invoice(amount=500)


with MirageSession(run_id="invoice-flow") as mirage:
    workflow = AgentWorkflow(BillingActions(mirage.client))
    workflow.run()
    mirage.assert_clean()
```

That pattern is often the right starting point for agent frameworks that handle
planning and tool orchestration internally but still call out to real APIs for
the dangerous work.

## Start Narrow

- Intercept writes before reads.
- Focus on one risky workflow first, not your whole agent.
- Get one clean CI gate working before you broaden the coverage.

## What Mirage Needs From You

- A stable `run_id`
- A client boundary that can be pointed at Mirage
- Mock and policy config for the external actions you care about
- A gate in tests or CI that fails on risky actions

## Next Steps

- Direct `httpx` path: [FIRST_INTEGRATION.md](FIRST_INTEGRATION.md)
- CI wiring: [CI_INTEGRATION.md](CI_INTEGRATION.md)
- Bundled example harness: [../examples/procurement_harness/README.md](../examples/procurement_harness/README.md)
