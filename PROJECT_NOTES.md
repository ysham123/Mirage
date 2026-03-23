# Mirage Project Notes

## Positioning Memo

### Market Context

The market is moving toward agent adoption, but still early enough that trust and control are major blockers.

The relevant pattern is:

- more teams are experimenting with agents
- fewer teams are confidently scaling them in production
- risk increases once agents can trigger real side effects
- most current tooling is stronger at evals, observability, or runtime defense than pre-production action testing

That means Mirage should not try to be a broad "AI platform."

The sharper opportunity is:

`test what the agent tried to do before it hits production`

### One-Sentence Positioning

`Mirage is CI for agent side effects: it intercepts agent API actions, applies policy checks, returns safe mocked responses, and produces deterministic traces before those actions reach production.`

### Who It's For

- engineering teams building agents that call APIs or trigger side effects
- Python-first teams already using `pytest`, mocks, and CI
- teams in operational workflows where bad actions have real cost
- internal tooling, ops automation, support, procurement, fintech, and similar use cases

### Who It's Not For

- teams building read-only chat experiences
- buyers looking for a full enterprise AI governance suite
- teams whose primary problem is response quality evals
- teams primarily looking for runtime SOC or security monitoring

### Problem Statement

Teams are moving from read-only copilots to agents that can take actions, but they still lack a reliable way to test those actions before production.

Existing eval products mostly focus on output quality.
Existing security products mostly focus on runtime protection.

What is missing is a developer-native test layer that lets teams:

- simulate agent actions
- enforce business rules and safety policies
- preserve agent control flow with realistic mocked responses
- fail CI when an agent would have taken an unsafe or out-of-bounds action

### Product Wedge

The wedge should stay narrow and concrete:

- outbound HTTP interception
- policy checks on request payloads
- schema-valid mocked responses
- deterministic run-scoped traces
- `pytest` and CI-friendly pass/fail behavior

This wedge matters because it maps to engineering workflows teams already understand.

### Words To Use

- CI for agent side effects
- test before production
- action-taking agents
- pre-production validation
- policy-gated simulation
- deterministic traces
- agent action testing
- safe replay

### Words To Avoid

- AI safety platform
- trust layer
- observability platform
- runtime security platform
- governance suite
- guardrails platform

Those terms either imply a broader product than Mirage currently is or push Mirage into crowded categories where the repo does not yet support the claim.

### 30-Second Founder Pitch

AI agents are starting to do more than answer questions. They can call APIs, update systems, and trigger real actions. The problem is that teams still do not have a good way to test those actions before production. Mirage is CI for agent side effects: it sits between the agent and external APIs, enforces policy, returns realistic mocked responses, and generates deterministic traces so teams can catch unsafe behavior in tests instead of in production.

## Product Thesis

Mirage should not try to solve "AI safety" in the abstract.

The stronger and more practical wedge is:

- agents are moving from read-only copilots to systems that trigger real side effects
- teams need a safe way to test those side effects before production
- Mirage should sit between the agent and external APIs
- Mirage should intercept outbound requests, evaluate them against policy, return schema-valid mocked responses, and produce deterministic traces for CI

The positioning from the PDF is strong:

`Mirage is CI for agent side effects.`

That is the right framing for the MVP.

## Why We Scoped Down

Trying to build a broad enterprise platform immediately would be a mistake.

The first version should prove one narrow loop well:

1. a developer defines a mocked endpoint
2. a developer defines a safety rule
3. an agent attempts an outbound HTTP action
4. Mirage intercepts it
5. Mirage evaluates policy
6. Mirage returns a safe synthetic response
7. Mirage writes a deterministic trace artifact for CI

This is the smallest version that is both useful and aligned with the product thesis.

We explicitly deprioritized for now:

- dashboards
- approvals workflows
- hosted replay
- team features
- multi-language support
- semantic grading as a core moat
- complex stateful simulation
- full OpenAPI ingestion

Those may matter later, but they are not required to validate the wedge.

## What The Original Repo Was

Before the refactor, the codebase was a proof of concept, not yet the product described in the PDF.

It had:

- one hard-coded endpoint in `src/proxy.py`
- one hard-coded bid flow
- one SQLite table in `src/state.py`
- one JSON audit log in `examples/audit_log.json`
- one pytest rule that read the log after the fact

That was useful as a toy demo, but it had two important problems:

1. It was not config-driven, so it could not act like a reusable developer tool.
2. The test flow was not deterministic because it depended on shared persisted log state.

## Why The Refactor Was The Right First Move

The product needs to be config-driven and deterministic before it needs to be broad.

The main reasoning behind the refactor:

- hard-coded logic proves an idea, but config proves a product direction
- run-scoped traces are more important than generic "logging" because trace artifacts are what CI and debugging actually need
- pytest-native pass/fail behavior is central to the wedge
- adoption ergonomics like richer interception helpers should come after the core loop works cleanly

So the goal was not "add more features."

The goal was to convert the demo into the first real vertical slice of Mirage.

## What Was Implemented

### Core Engine

Added a config-driven execution engine in `src/engine.py`.

It now:

- loads mocks and policies from config files
- matches requests by method and path
- evaluates policies against request payloads
- returns configured mock responses
- writes structured trace events for each run

### Config Layer

Added `src/config.py` plus:

- `mocks.yaml`
- `policies.yaml`

This is the first step from hard-coded demo logic toward a reusable product.

Current default example:

- `POST /v1/submit_bid`
- mock success response
- policy enforcing `bid_amount <= 10000`

### Trace Storage

Added `src/trace.py`.

This replaces the old shared audit log model with run-scoped trace files under:

- `artifacts/traces/`

That makes testing much more deterministic and much closer to how CI artifacts should work.

### Proxy

Updated `src/proxy.py`.

Instead of exposing one hard-coded endpoint handler, the FastAPI app now routes incoming requests through the Mirage engine. This is a much cleaner product boundary.

### Example Agent

Updated `examples/rogue_agent.py`.

It now sends a Mirage run ID header so its activity can be isolated into a specific trace file.

### Tests

Rewrote tests in `tests/test_agent_safety.py` and simplified fixtures in `tests/conftest.py`.

The tests now verify the real product loop:

- policy violations are recorded
- mocked responses still preserve agent control flow
- traces are isolated by run ID

## Validation

The updated test suite passes:

- `pytest -q`
- result: `3 passed`

That means the current repo now supports a credible first product loop instead of a stale-log demo.

## Current MVP Boundary

Mirage currently supports:

- Python-first local engine
- HTTP request handling
- declarative mocks
- declarative policy checks
- run-scoped traces
- deterministic pytest validation

This is the right MVP boundary.

It is intentionally narrower than the full startup vision, but much more defensible.

## What Comes Next

The next good milestones are:

1. Better policy language

- nested field selectors
- reusable predicates
- richer path and method filtering
- clearer failure summaries

2. Better interception ergonomics

- low-friction helpers for `httpx`
- low-friction helpers for `requests`
- easier test integration for existing Python agent stacks

3. Stronger mock realism

- parameterized responses
- request-aware mock bodies
- basic stateful flows for create/read/update sequences

4. OpenAPI ingestion

- generate mocks from API specs
- generate validators from API specs
- reduce manual config burden

## Strategic Note

The strongest early Mirage story is not:

"we make AI safer."

It is:

"we let teams test what their agents tried to do before those actions hit production."

That is more concrete, more measurable, and easier to sell into engineering teams.

## Files Changed In This Refactor

- `src/config.py`
- `src/engine.py`
- `src/trace.py`
- `src/proxy.py`
- `src/__init__.py`
- `mocks.yaml`
- `policies.yaml`
- `examples/rogue_agent.py`
- `tests/conftest.py`
- `tests/test_agent_safety.py`
- `requirements.txt`

## Closing View

The key decision we made was correct:

do not build the million-dollar ARR startup all at once.

Build the narrowest loop that proves the wedge, produces deterministic evidence, and fits naturally into developer workflows.

That is what the current version now does more honestly than the original toy implementation.
