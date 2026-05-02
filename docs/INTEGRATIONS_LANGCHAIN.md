# LangChain integration

Mirage ships a thin adapter for LangChain at
`mirage.integrations.langchain`. The adapter routes every tool call a
LangChain agent makes through a Mirage gateway. The gateway evaluates
the call against the configured policies; if a policy fails, the
gateway returns HTTP 403 and the wrapped tool raises
`MiragePolicyBlockedError`. Otherwise the original tool runs as
written.

## Install

LangChain is an optional dependency.

```bash
pip install mirage-ci[langchain]
```

## Minimal example

```python
from langchain.agents import AgentExecutor, Tool
from mirage.integrations.langchain import (
    wrap_with_mirage,
    MiragePolicyBlockedError,
)


def submit_bid(bid_amount: float) -> dict:
    # Pretend this calls a real procurement API.
    return {"status": "submitted", "bid_amount": bid_amount}


tool = Tool.from_function(submit_bid, name="submit_bid", description="Submit a bid")
agent = AgentExecutor(agent=..., tools=[tool])  # any LangChain agent

# Point at a running `mirage gateway` instance.
wrapped = wrap_with_mirage(
    agent,
    gateway_url="http://127.0.0.1:8001",
    run_id="procurement-2026-05-02",
)

try:
    result = wrapped.tools[0].func(bid_amount=50000)
except MiragePolicyBlockedError as exc:
    print(f"Mirage blocked the bid: {exc}")
    for decision in exc.decisions:
        print(f"  policy {decision['name']} failed")
```

To run the gateway side of this:

```bash
mirage gateway \
  --upstream https://your-procurement-api.example.com \
  --mode enforce \
  --policies-path examples/policies/cost_guard.yaml
```

When the agent calls `submit_bid(bid_amount=50000)`, the wrapped tool
sends a `POST /v1/tools/submit_bid` to the gateway with payload
`{"tool": "submit_bid", "kwargs": {"bid_amount": 50000}, "bid_amount":
50000}`. The default payload mapper lifts kwarg names to the payload
root so `cost_guard.yaml` (which has `field: bid_amount`) matches
without a per-deployment custom mapper. The gateway sees
`bid_amount > 10000`, returns 403, and the wrapped tool raises
`MiragePolicyBlockedError`.

## Custom payload mapping

Pass a `payload_mapper` callable to control what JSON the adapter
sends to the gateway:

```python
def my_mapper(tool_name: str, args, kwargs) -> dict:
    return {
        "tool": tool_name,
        "operation": kwargs.get("op"),
        "amount":    kwargs.get("amount"),
    }


wrapped = wrap_with_mirage(
    agent,
    gateway_url="http://127.0.0.1:8001",
    payload_mapper=my_mapper,
)
```

This is the recommended pattern when your gateway policies expect a
specific payload shape that differs from the tool's call signature.

## Why does Mirage not wrap the model call?

Mirage is concerned with actions, not with what the model says. The
model can produce any text it wants; Mirage only cares about what the
agent tries to do. Wrapping the model call would put Mirage in the
output-quality scoring business (hallucination detection, helpfulness,
factuality), which is a separate concern with a different solution
shape and a different right answer per deployment. Mirage stays
narrow: deterministic policy decisions on actions, no LLM in the
decision loop.

## How this differs from LangChain's own callbacks

LangChain ships an extensive callback system (`on_tool_start`,
`on_tool_end`, `on_chain_*`, etc.). Those callbacks observe and react
to tool invocations but they do not provide a deterministic gate
between the model deciding to call a tool and the tool actually
running. They run after the call has already been decided. Custom
callback authors can raise exceptions but the contract is
observability, not enforcement.

Mirage's adapter inserts a gate before the tool runs, evaluates the
policy file deterministically, and either lets the tool run or
raises `MiragePolicyBlockedError`. The same `policies.yaml` evaluates
in both gateway mode (production) and CI mode (pre-merge).

## What gets sent to the gateway

By default the adapter sends:

```
POST {gateway_url}/v1/tools/{tool_name}
Content-Type: application/json
X-Mirage-Run-Id: {run_id}

{
  "tool":   "<tool_name>",
  "args":   [...positional args...],
  "kwargs": {...keyword args...},
  ...kwarg-name keys lifted to root for direct policy matching...
}
```

Pass `payload_mapper` to override this shape entirely.

A blocked call surfaces as `MiragePolicyBlockedError` with the failed
policy decisions on the `decisions` attribute, suitable for an agent's
error-handling chain to log or surface to the operator.

## Limits

- The adapter does not currently rewrite outbound HTTP requests made
  by tool implementations themselves; only tool entry is gated. To
  enforce policies on tool-internal HTTP, configure your tool's HTTP
  client to use the gateway as its base URL directly.
- Async tool surfaces (`coroutine`, `_arun`) are wrapped synchronously
  via the same payload-mapper / gateway-check path; the wrapped
  callable will block on the gateway request before invoking the
  underlying coroutine. Async-native gating is on the roadmap.
- Output-quality scoring is out of scope, by design (see above).
