# Mirage Abstract

Mirage is a pre-production testing layer for action-taking AI agents. As AI systems move beyond read-only copilots and begin calling APIs, updating systems, and triggering external workflows, the engineering problem shifts from answer quality alone to action safety, control, and reliability. Teams need a practical way to test what an agent attempted to do before those actions reach live systems.

Mirage addresses this gap by sitting between an agent and external APIs. It intercepts outbound HTTP requests, evaluates them against configurable policies, returns safe mocked responses, and records deterministic traces for local development and CI. This allows developers to preserve agent control flow while validating whether an attempted action stayed within defined operational and safety boundaries.

The product is intentionally narrow. Mirage is not a general AI safety platform, a broad observability layer, or a runtime security product. Its initial wedge is clearer and more useful: CI for agent side effects. The goal is to give engineering teams a developer-native way to simulate agent actions, enforce policy before production, and fail tests when an agent would have taken an unsafe or out-of-bounds step.

This approach is especially well suited to Python-first teams that already rely on `pytest`, mocks, and deterministic testing workflows. By fitting into familiar engineering patterns, Mirage reduces adoption friction and frames agent safety as a concrete testing problem instead of an abstract governance promise.

In short, Mirage helps teams test agent behavior at the point where model output becomes real-world action.

## MVP Build Stages

### Stage 1: Core Interception Loop

Build the smallest useful loop:

1. Intercept outbound HTTP requests from an agent.
2. Match each request against a configured mock route.
3. Return a schema-valid mocked response.
4. Record the request and response in a deterministic trace.

Goal: prove Mirage can sit in the execution path without breaking agent control flow.

### Stage 2: Policy Evaluation

Add configurable rules that inspect request payloads before a mocked response is returned.

Examples:

- bid amount must stay below a threshold
- destination account must be on an allowlist
- destructive actions must include a required field

Goal: prove Mirage can detect unsafe or out-of-bounds actions during test execution.

### Stage 3: Run-Scoped Traces for CI

Make traces deterministic and isolated by run ID so each test run produces its own artifact.

This stage should include:

- stable trace file naming
- structured request, decision, and response records
- easy assertions in `pytest`

Goal: make Mirage useful inside normal developer workflows and CI pipelines.

### Stage 4: Developer-Native Test Integration

Improve usability so Mirage feels like a natural extension of existing testing workflows.

This stage should include:

- simple setup for Python teams
- low-friction integration with `pytest`
- helpers for common HTTP clients such as `httpx` and `requests`

Goal: reduce adoption friction and make the product feel familiar to engineers.

### Stage 5: Richer Policies and More Realistic Mocks

Expand beyond simple field checks and static responses.

This stage should include:

- nested field selectors
- reusable predicates
- better failure summaries
- parameterized responses
- basic request-aware or stateful mocks

Goal: make Mirage realistic enough for broader classes of agent workflows.

### Stage 6: Spec-Driven Configuration

Reduce manual setup by generating mocks and validators from API definitions.

This stage should include:

- OpenAPI-based mock generation
- request schema validation
- easier onboarding for new endpoints

Goal: move Mirage from hand-configured demo flows to repeatable team adoption.

### Stage 7: Broader Product Surface

Only after the core testing wedge is proven should Mirage expand into adjacent surfaces.

Possible later stages:

- replay tooling
- dashboards
- approvals workflows
- hosted team features
- multi-language support

Goal: expand from a strong wedge without losing the product's clarity.
