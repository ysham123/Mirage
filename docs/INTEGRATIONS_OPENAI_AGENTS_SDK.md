# OpenAI Agents SDK integration

Mirage ships a thin adapter for the OpenAI Agents SDK at
`mirage.integrations.openai_agents`. The adapter routes every tool
call an agent makes through a Mirage gateway. The gateway evaluates
the call against the configured policies; if a policy fails, the
gateway returns HTTP 403 and the wrapped tool raises
`MiragePolicyBlockedError`. Otherwise the original tool runs as
written.

## Install

The OpenAI Agents SDK is an optional dependency.

```bash
pip install mirage-ci[openai-agents]
```

## Minimal example

```python
from agents import Agent, Tool
from mirage.integrations.openai_agents import wrap_with_mirage, MiragePolicyBlockedError


def submit_bid(amount: float) -> dict:
    # Pretend this calls a real procurement API.
    return {"status": "submitted", "amount": amount}


agent = Agent(
    name="procurement-agent",
    model="gpt-4o-mini",
    tools=[Tool(name="submit_bid", func=submit_bid)],
)

# Point at a running `mirage gateway` instance.
wrapped = wrap_with_mirage(
    agent,
    gateway_url="http://127.0.0.1:8001",
    run_id="procurement-2026-05-02",
)

try:
    result = wrapped.tools[0].func(50000)
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

When the agent calls `submit_bid(50000)`, the wrapped tool first sends
a `POST /v1/tools/submit_bid` to the gateway with the call payload.
The gateway evaluates `cost_guard.yaml` against `{"args": [50000]}`,
sees that 50000 exceeds the `cap_bid_amount` threshold, and returns
403. The wrapped tool raises `MiragePolicyBlockedError`. The original
`submit_bid` function never runs.

## Why does Mirage not wrap the model call?

Mirage is concerned with actions, not with what the model says. The
model can produce any text it wants; Mirage only cares about what the
agent tries to do. Wrapping the model call would put Mirage in the
output-quality scoring business (hallucination detection, helpfulness,
factuality), which is a separate concern with a different solution
shape and a different right answer per deployment. Mirage stays
narrow: deterministic policy decisions on actions, no LLM in the
decision loop.

## How this differs from OpenAI's own agent guardrails

The OpenAI Agents SDK ships first-class `input_guardrail` and
`output_guardrail` callbacks. Those guardrails are model-graded: the
SDK invokes another LLM call to score whether an input or output
should pass. That model-graded approach is well-suited to fuzzy
correctness questions ("is this off-topic?", "does this contain a
harmful suggestion?") but it costs a model call per check and is
non-deterministic.

Mirage is rule-graded. The decision is a deterministic policy
evaluation against the YAML config in `policies.yaml`. Same input,
same output, every time. No model call per check. The wedge is
auditability and reproducibility for the actions a regulated team
actually has to defend in writing.

The two approaches compose: use OpenAI's input/output guardrails for
fuzzy checks, and use Mirage for the deterministic ones (PII
redaction, cost caps, outbound URL allowlists, output length caps).

## What gets sent to the gateway

For each wrapped tool call, the adapter sends:

```
POST {gateway_url}/v1/tools/{tool_name}
Content-Type: application/json
X-Mirage-Run-Id: {run_id}

{
  "args":   [...positional args...],
  "kwargs": {...keyword args...}
}
```

`run_id` defaults to `openai-agents-{uuid}` so multiple wrapped agents
in the same process group their tool calls into separate Mirage runs.
Pass an explicit `run_id` to opt into a stable run identifier.

A blocked call surfaces as `MiragePolicyBlockedError`. The
`decisions` attribute on the exception carries the failed policy
decisions returned by the gateway in its 403 body, suitable for the
agent to log or surface to the operator.

## Limits

- The adapter does not currently rewrite outbound HTTP requests made
  by tool implementations themselves; only tool entry is gated. To
  enforce policies on tool-internal HTTP, configure your tool's HTTP
  client to use the gateway as its base URL directly.
- The adapter does not stream policy decisions back to the agent for
  it to "see"; a blocked call is just an error from the agent's point
  of view. This is intentional. The gateway is in the decision loop;
  the model is not.
- Output-quality scoring is out of scope, by design (see above).
