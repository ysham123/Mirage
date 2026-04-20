# Mirage Product Spec

## Product Definition

Mirage is a pre-merge testing, CI, and review layer for agent actions.

It sits between an action-taking agent and external APIs, intercepts outbound HTTP requests, evaluates them against configured policy, returns safe mocked responses, and writes deterministic traces for local development and CI.

Mirage is not an LLM, an agent runtime, or a generic analytics platform. The product lives at the HTTP action boundary.

## Current Reality

Mirage already has a real technical wedge:

- HTTP interception through the local proxy
- config-driven mocks and policy checks
- deterministic run-scoped traces
- Python-first `httpx` integration primitives
- a lightweight review console over trace artifacts

Current console split:

- `demo_ui/` is the shared FastAPI console API and zero-dependency HTML shell
- `ui/` is the richer Next.js client over that same API

Current lead positioning:

- Mirage should be framed first as a testing and CI layer for outbound agent
  HTTP actions
- Mirage should not currently be framed first as a generic runtime guard for
  production traffic

Mirage is not yet a fully self-serve product:

- the integration path is still narrow
- policy authoring is still low-level
- CI gating is not yet the obvious default workflow
- onboarding still depends too much on founder context

## Ideal Customer Profile

The first user is a Python engineer building an agent that can trigger real side effects through HTTP APIs.

Strong early fits:

- procurement and vendor workflows
- support or ticket automation
- CRM or back-office write actions
- internal ops agents with real system mutation risk

## Core Problem

Teams are getting better tooling for model outputs, but not for agent actions.

Today, most teams can evaluate or inspect what an agent says. They still lack a deterministic, engineer-friendly way to test what an agent tries to do before those actions hit real systems.

The missing workflow is:

- run the agent locally or in CI
- intercept outbound actions
- evaluate them against policy
- let the workflow continue safely with mocked responses
- review exactly what happened
- fail builds when risky actions appear

## Product Promise

Mirage gives engineers a safe, testable boundary around agent actions before those actions become production side effects.

## Canonical Engineer Workflow

1. Start Mirage with the relevant mock and policy config.
2. Route the agent's outbound HTTP client through Mirage.
3. Run the agent workflow locally or in CI.
4. Mirage classifies each action as `allowed`, `policy_violation`, `unmatched_route`, or `config_error`.
5. Mirage writes a deterministic trace for the run.
6. The engineer reviews the run summary and fails the build if risky actions occurred.

## Integration API

### Current Live Primitive

Today Mirage is integrated by routing a Python `httpx` client through the local proxy and inspecting Mirage metadata headers on each response.

### Target Canonical API For The Next Milestone

The product should converge on one obvious run-level integration shape:

```python
from mirage import MirageSession

with MirageSession(run_id="procurement-pr-128") as mirage:
    agent = ProcurementAgent(client=mirage.client)
    agent.run()
    summary = mirage.assert_clean()
```

The important product behavior is:

- one run id for the workflow
- a Mirage-backed client for outbound HTTP
- one run-level summary for local dev and CI
- one clean assertion point for build gating

The exact API names can still change, but the workflow should not.

## Next Major Milestone

### Integration-Grade Private Alpha

Mirage reaches the next major milestone when one external Python engineer can:

- integrate Mirage into an existing action-taking agent in under 30 minutes
- route one real workflow through Mirage without founder hand-holding
- understand unsafe outcomes and unmatched routes from the run summary alone
- use Mirage in local development and in CI
- get enough value from traces and gating to keep it in their workflow

## What Must Be True At This Milestone

- one Python integration path is canonical and documented
- quickstart is reliable and maps to a real workflow, not just a founder demo
- CI gating is a first-class part of the story
- traces are readable without opening raw JSON first
- the console story is explicit: one shared backend, multiple review clients
- at least one realistic example harness feels close to production usage
- 1 to 2 external engineer teams agree to try it and give workflow feedback

## Non-Goals For This Milestone

- broad multi-language support
- hosted control plane or team accounts
- approvals workflows
- generic executive analytics
- dashboard expansion as the primary product work

## Success Metrics

- 2 external engineer pilots started
- first successful integration completed in under 30 minutes
- at least 1 team runs Mirage in CI on a real workflow
- users ask for richer policies, integrations, or config generation instead of questioning the core premise

## Immediate Build Priorities

1. Lock the canonical Python integration API.
2. Add clear run-level CI gating and human-readable failure summaries.
3. Tighten quickstart and onboarding around one real workflow.
4. Run technical design-partner outreach with engineers who already have action-taking agents.
