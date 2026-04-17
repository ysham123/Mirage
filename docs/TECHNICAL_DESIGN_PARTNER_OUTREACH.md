# Technical Design Partner Outreach

## Goal

Find 1 to 2 external engineers willing to try Mirage on a real action-taking workflow and give direct product feedback.

These are not designers. They are early engineer users.

## Who To Target

The best early candidates are engineers who already have agents or workflow automation touching real APIs.

Priority profiles:

- Python engineers shipping internal agents
- engineers automating support, procurement, CRM, or ops workflows
- teams where a mistaken API call creates real cost, data drift, or customer impact
- builders already using `pytest`, `httpx`, FastAPI, or simple API-based tool execution

Avoid for now:

- chatbot-only products with no real side effects
- teams asking for broad governance or enterprise procurement features first
- users who need non-Python support immediately

## The Pitch

Lead with the problem, not the company vision.

Recommended positioning:

"Mirage helps engineers test agent actions before they hit real systems. It intercepts outbound API calls, evaluates them against policy, returns safe mocked responses, and writes deterministic traces for local dev and CI."

Keep the ask narrow:

- one short call to validate the workflow
- one real action-taking flow to test
- optional private-alpha trial if the workflow is a fit

## What To Ask For

Ask for:

- a 20 to 30 minute call
- one concrete workflow where an agent takes real HTTP actions
- a chance to test Mirage on that workflow in a lightweight private alpha

Do not ask for:

- long strategy meetings
- broad product ideation
- enterprise commitments

## Outreach Templates

### Short DM

Hi [Name] — I’m building Mirage, a pre-production testing layer for agent actions. It sits between an agent and external APIs, evaluates outbound actions against policy, returns safe mocked responses, and writes deterministic traces for local dev and CI. If you’re working on agents that trigger real side effects, I’d like to compare notes and see if one workflow would be a fit for a small private alpha.

### Slightly Longer Email

Subject: testing agent actions before they hit production

Hi [Name],

I’m building Mirage for a narrow problem: teams have evals for outputs, but not a clean way to test what agents try to do before those actions hit real systems.

Mirage is a Python-first pre-production layer that intercepts outbound HTTP actions, checks them against policy, returns safe mocked responses, and writes deterministic traces for local dev and CI.

I’m looking for 1 to 2 engineers who already have action-taking agents and would be open to a short conversation or a lightweight private-alpha trial on one real workflow.

If that sounds relevant, I’d like to show you the current flow and learn how you handle risky agent actions today.

### Follow-Up

Following up in case this is relevant. I’m not trying to replace your agent stack. I’m trying to make the "test agent actions before production" workflow concrete for Python teams. If you have one workflow where mistaken API calls are painful, that is exactly the use case I want to learn from.

## Discovery Questions

Use the call to understand the workflow, not to pitch features.

Questions:

- What real actions do your agents take today?
- Which actions feel risky or expensive if they go wrong?
- How are you testing those actions now?
- Do you think about this problem as tests, mocks, guardrails, approvals, or something else?
- What would need to happen for you to run a tool like this in CI?
- Which HTTP client or framework are you using today?
- What would make traces or run summaries genuinely useful to you?

## Pilot Structure

Keep the pilot narrow and engineer-friendly.

Suggested structure:

- one workflow only
- one Python HTTP integration path
- one local-dev run
- one CI gating pass
- one follow-up conversation after they try it

Success is not broad feature adoption. Success is a real engineer saying:

"This fits how I already test or ship agent workflows."

## Qualification Checklist

Good fit if most are true:

- they already run action-taking agents
- they use Python or can tolerate a Python-first integration
- their agent talks to HTTP APIs
- a bad action has real cost
- they are willing to try a private-alpha developer tool

Bad fit if most are true:

- they only care about prompt quality
- they need hosted SaaS first
- they need multi-language support immediately
- they want human approvals more than testing infrastructure

## What To Learn

The outreach should answer these product questions:

- Is the action-testing problem painful enough to matter now?
- Does Mirage feel like testing infrastructure or something else?
- Is the HTTP interception model natural or awkward?
- Is the CI gate the most important workflow, or is local debugging more urgent?
- Which integrations and policy abstractions matter first?

## Exit Criteria

This outreach pass is working if:

- you get 3 to 5 real conversations
- 1 to 2 engineers agree to try Mirage on a real workflow
- the feedback sharpens the integration path rather than pushing you toward generic analytics or broad platform work
