# Mirage 90-Day Plan

## Summary

Mirage is already beyond Stage 1. The current implementation covers the core interception loop, basic policy evaluation, and run-scoped traces, which puts the product around Stage 3 with a thin slice of Stage 4.

The strongest path now is not a broad public launch. It is a design-partner-driven private alpha supported by public technical content on X and short demo videos.

The next 90 days should optimize for three outcomes:

1. Turn the current demo into a repeatable developer workflow.
2. Earn 3 to 5 design-partner conversations with engineers building action-taking agents.
3. Define a clear private-alpha gate and a later public-MVP gate.

## Product Focus

- Treat Mirage as `CI for agent side effects`, not as a broad AI safety or observability product.
- Keep the initial ICP narrow: Python-first engineers building agents that call APIs or trigger real system changes.
- Optimize for private-alpha readiness before broad self-serve launch.
- Use X plus short demo videos as the main public distribution loop.

## Phase 1: Clarify the Wedge and Tighten the Demo

Timeline: Weeks 1-2

### Goals

- Standardize the Mirage story across all public materials.
- Make the product legible through a few concrete scenarios.
- Produce a short demo flow that explains the product in under 60 seconds.

### Work

- Align all messaging around:
  - what Mirage is
  - who it is for
  - what it is not
  - what the current MVP actually does today
- Produce 3 canonical scenarios:
  - safe request passes
  - unsafe request is flagged but control flow continues
  - unmatched route or bad config produces a clear failure path
- Tighten the live demo so it shows:
  - agent request
  - policy decision
  - mocked response
  - trace artifact

### Deliverables

- One clean product narrative
- Three demo scenarios
- One short live demo flow

## Phase 2: Build to Private-Alpha Readiness

Timeline: Weeks 3-6

### Goals

- Move from a technical demo to a usable developer workflow.
- Close the main gap between Stage 3 and Stage 4.

### Priorities

1. Add low-friction developer entry points for `httpx` and/or `requests`.
2. Make setup simple enough that a Python engineer can try Mirage in under 15 minutes.
3. Improve failure output so policy violations and unmatched routes are easy to understand.
4. Expand tests from the current narrow path to a few more realistic workflows.
5. Add one example repo or example directory that feels like a real agent test harness.

### Private-Alpha Gate

Mirage is private-alpha ready when:

- install and run path is simple and documented
- one Python HTTP client integration works cleanly
- traces are readable and useful without explanation
- at least 3 example scenarios exist
- a new user can run the product without you pairing on every step

## Phase 3: Start Design-Partner Outreach While Building

Timeline: Weeks 3-8

### Target Profiles

- engineers building internal agent tools
- ops automation teams
- support or procurement workflows with real side effects
- fintech or enterprise teams where mistaken actions have real cost

### Outreach Motion

- identify 30 to 50 relevant engineers or founders
- reach out to 5 to 10 per week
- lead with the problem, not the company vision
- ask whether they currently have a safe way to test agent-triggered actions before production

### Conversation Goals

- validate whether the pain is real
- learn which actions matter most
- learn whether they think in terms of tests, mocks, policies, or approvals
- see whether Mirage fits their workflow naturally

### Success Criteria

- 3 to 5 serious conversations
- 1 to 3 teams willing to try a private alpha
- repeated user language that sharpens the pitch

## Phase 4: Build in Public with X Plus Video

Timeline: Start now and continue weekly

### Channel Strategy

Use `X + video`.

Reason:

- X is the fastest place to iterate on messaging and find technical users.
- Short videos make the product legible much faster than text alone.
- Video clips can be reused inside X posts.

### Publishing Cadence

- X: 4 posts per week
- short demo video: every 1 to 2 weeks
- longer walkthrough: once per month if bandwidth allows

### Content Rules

- post concrete engineering demos, not abstract AI-safety thoughts
- show the exact request, policy decision, mock response, and trace
- frame Mirage as a testing tool for action-taking agents
- avoid overclaiming the product as a full platform

### Best Early Themes

- how to test AI agents with `pytest`
- why agent actions need CI before production
- demo of a risky request being caught without breaking the agent loop
- what makes agent testing different from normal evals
- what you learned building a proxy for agent side effects

### Bandwidth Rule

If bandwidth becomes a problem:

- keep X as the always-on channel
- keep video lightweight and demo-driven
- do not aim for polished creator content yet

## Phase 5: Run a Private Alpha Before Broad Release

Timeline: Weeks 7-10

### Private Alpha Means

- small number of users
- tight feedback loop
- direct support from you
- emphasis on learning, not scale

### What to Learn

- where setup is confusing
- whether the policy model is intuitive
- whether traces are actually useful in debugging
- which integrations matter first
- whether users think of Mirage as testing infrastructure or something else

### Private-Alpha Success Criteria

- at least 2 outside teams can run Mirage end to end
- they can configure a realistic scenario without custom founder intervention at every step
- they find the trace and failure output useful enough to keep using it
- they ask for richer mocks, more policies, or better integrations instead of questioning the product premise

## Phase 6: Public MVP Launch Only After the Product Is Self-Serve Enough

Timeline: Weeks 10-12 or later

### Rule

Do not define `full MVP` as `more features`.

Define it as:

`an outside engineer can adopt it without you`

### Public-MVP Gate

- clear quickstart that works reliably
- one strong Python integration path
- 3 to 5 realistic examples
- clean docs and repo consistency
- understandable trace artifacts and policy failures
- enough reliability that first users do not bounce immediately
- a public message that matches the actual product surface

### Public Launch Message

- Mirage is a pre-production testing layer for agent side effects
- it helps teams test risky agent actions before production
- it fits into Python and `pytest` workflows
- it is for action-taking agents, not generic chatbots

## What to Build Next

Most important product work, in order:

1. developer-native integration with `httpx` and/or `requests`
2. stronger examples beyond the bid demo
3. clearer policy failure summaries
4. better onboarding and quickstart
5. richer policies and request-aware mocks
6. OpenAPI-assisted config generation later, after the core loop is sticky

Do not prioritize yet:

- dashboards
- approvals workflows
- hosted control planes
- broad multi-language support
- generic enterprise governance messaging

## Blind Spots to Address Early

- Packaging: decide whether Mirage is primarily a library, proxy, CLI, or a combination.
- Entry point: define the exact first-run experience for a new user.
- ICP: narrow down which workflow has the strongest pain first.
- Policy model: make `unsafe` concrete and not philosophical.
- Success metric: define whether success means CI gating, debugging clarity, or fewer production mistakes.
- Example depth: build multiple realistic workflows, not one toy path.
- Error handling: define behavior for unmatched routes, malformed config, bad payloads, and non-JSON requests.
- Distribution assets: keep repo, docs, posts, and demos saying the same thing.
- Release model: decide whether the early motion is OSS-first, private alpha, or hybrid.

## Acceptance Criteria

This plan is working if, by the end of the 90-day window:

- Mirage clearly presents as Stage 4 and no longer feels like a thin Stage 3 demo
- you have 3 to 5 real user conversations
- you have at least 1 to 3 private-alpha users
- you are posting regularly on X and have reusable demo clips
- you have a clear decision on whether to push toward broader public launch or continue iterating privately

## Assumptions

- default path chosen: design-partner-driven private alpha, not broad public launch
- default distribution path chosen: X plus short demo videos
- default ICP: Python-first engineers building action-taking agents with real side effects
- current implementation status: beyond Stage 1, roughly Stage 3 with partial Stage 4 readiness
