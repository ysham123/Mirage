# Mirage Problem Statement

## The Problem

AI agents are moving from read-only copilots to systems that can call APIs, update records, submit transactions, and trigger operational workflows.

Once that happens, the problem is no longer just answer quality. The problem becomes action safety.

Engineering teams need a reliable way to test what an agent attempted to do before those actions reach production systems.

Today, that gap is poorly served:

- eval tools mostly focus on output quality
- runtime security tools focus on production-time defense
- ordinary mocks do not capture policy decisions or generate useful agent-side traces

The missing layer is pre-production testing for agent side effects.

## Why It Matters

When an agent can take actions, failures become expensive:

- unauthorized purchases
- unsafe workflow updates
- destructive API calls
- business-rule violations that still look like valid requests

Without a dedicated testing layer, teams either rely on fragile staging setups or discover these failures in production.

## Mirage's Approach

Mirage is CI for agent side effects.

It sits between the agent and external APIs, intercepts outbound HTTP actions, evaluates them against policy, returns safe mocked responses, and writes deterministic traces for tests and CI.

That gives teams a developer-native way to:

- simulate agent actions before production
- enforce safety and business rules during test execution
- preserve agent control flow with realistic responses
- inspect exactly what the agent tried to do
- fail CI when the action was unsafe or out of bounds

## What The Current Repository Proves

This repository already demonstrates the first working product loop:

1. a request is intercepted
2. a mock is matched
3. a policy is evaluated
4. a schema-valid response is returned
5. a deterministic trace is written
6. the behavior is asserted in `pytest`

This is the narrow but credible MVP wedge.

## What Mirage Is Not

Mirage is not currently:

- a broad AI safety platform
- a generic observability platform
- a runtime security system
- a full enterprise governance suite

It is a pre-production testing layer for action-taking agents.

