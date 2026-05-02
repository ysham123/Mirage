# Database integration pattern

Mirage's runtime gateway sits in front of HTTP calls. Most agent
actions cross that boundary today (tool calls, API requests, webhooks)
so the gateway is enough. But a non-trivial number of agent actions
land as **direct database writes** that never traverse an HTTP path
the gateway can intercept: ORM-driven inserts, batch jobs that bypass
the service layer, internal admin tooling, queue workers that write
straight to Postgres or DynamoDB.

This doc describes a pattern teams can use today to extend Mirage's
policy evaluation to those direct DB writes. **It is not a Mirage
feature.** There is no `mirage.integrations.database` module yet, and
shipping one is on the v0.4 roadmap, not v0.2. The pattern below uses
SQLAlchemy event hooks plus the existing `PolicyEvaluator` to give
teams a working stop-gap that uses the same `policies.yaml` as the
rest of the runtime.

## Why this matters

If an agent can write directly to your database without going through
your service tier, your gateway-only policy posture has a hole. A
policy that says "no agent shall update a customer's billing address
outside business hours" only enforces against HTTP requests that hit
the gateway. A direct `customers.update(...)` call from an agent's
Python code skips the gateway entirely.

The fix is to put a deterministic policy decision point on the DB
write path itself. SQLAlchemy's event system gives that hook for free.

## The pattern

```python
from sqlalchemy import event
from sqlalchemy.orm import Session

from mirage.config import load_policies_only
from mirage.policy import PolicyEvaluator, build_policy_violation_message
from mirage.runtime_paths import resolve_config_path
from myapp.models import Customer


# Load the same policies.yaml the runtime gateway evaluates. Reload
# on every event so an operator editing the file does not need to
# restart the worker. (Cache with mtime in production.)
def _evaluator() -> PolicyEvaluator:
    config = load_policies_only(
        resolve_config_path(
            explicit=None,
            env_var="MIRAGE_POLICIES_PATH",
            filename="policies.yaml",
        )
    )
    return PolicyEvaluator(config)


def _enforce(method: str, path: str, payload: dict) -> None:
    decisions = _evaluator().evaluate(method=method, path=path, payload=payload)
    failed = [d for d in decisions if not d.passed]
    if failed:
        raise ValueError(build_policy_violation_message(decisions))


@event.listens_for(Customer, "before_insert")
def _customer_before_insert(_mapper, _connection, target: Customer) -> None:
    payload = {column.name: getattr(target, column.name) for column in target.__table__.columns}
    _enforce(method="INSERT", path=f"/db/{target.__tablename__}", payload=payload)


@event.listens_for(Customer, "before_update")
def _customer_before_update(_mapper, _connection, target: Customer) -> None:
    payload = {column.name: getattr(target, column.name) for column in target.__table__.columns}
    _enforce(method="UPDATE", path=f"/db/{target.__tablename__}", payload=payload)
```

What you get:

- Policy decisions on direct DB writes, evaluated against the same
  `policies.yaml` the runtime gateway uses.
- A clear failure mode (`ValueError`) that surfaces in the agent's
  exception path the same way a 403 would surface from the gateway.
- No model-graded checks; every decision is rule-based and
  reproducible.

What you do NOT get (yet):

- A trace event in the Mirage trace store. The HTTP gateway writes
  trace events; this hook does not. To wire it up, use
  `MirageGateway.trace_store.append_event(run_id, event)` directly,
  or post the event to the gateway's `/api/runs/<run_id>/...`
  surface.
- A run id propagated automatically. Pass it through
  `request.state.mirage_run_id` (or your own equivalent) and include
  it in the payload the hook builds.
- Async support. SQLAlchemy 2.x async sessions emit events
  differently; the snippet above is the synchronous-API shape.

## Caveats

- **No async path yet.** SQLAlchemy 2.x async sessions emit a
  different set of events. The snippet covers sync sessions.
- **Per-event policy reload.** Reading the policy file every event
  has a measurable cost on hot tables. In production, cache the
  evaluator and refresh on file mtime change.
- **Schema coupling.** The policy field paths (`field: bid_amount`)
  must match the column names of the model. If your column is
  `bid_amount_cents`, your policy must reference that name.
- **No retry semantics.** A policy violation raises and aborts the
  transaction. If your worker retries automatically, you will retry
  the violating write until the agent gives up. Surface the error
  upstream and stop.

## When the official integration ships

When `mirage.integrations.database` ships, it will:

- Provide a `register_models(engine, models, run_id_lookup=...)`
  helper that wires `before_insert` / `before_update` /
  `before_delete` for every listed model.
- Cache the evaluator with file-mtime invalidation so per-event cost
  is nominal.
- Write trace events to the same trace store the gateway uses, so
  the console's existing aggregations include DB-write events
  without further work.
- Support SQLAlchemy 2.x async sessions.

Until then, the snippet above is the recommended shape. Send the
final policies.yaml line items you actually deploy to
[github.com/ysham123/Mirage/issues](https://github.com/ysham123/Mirage/issues)
so the official integration ships with the right defaults.
