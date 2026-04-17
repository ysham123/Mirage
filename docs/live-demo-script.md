# Mirage Live Demo Script

## Goal

Show that Mirage is real infrastructure, not a canned simulator.

The strongest live flow is:

1. terminal first for credibility
2. UI second for clarity

Use the `risky` procurement scenario as the main story.

## Preflight

Open three panes or windows:

1. Mirage proxy
2. procurement harness terminal
3. founder demo UI in browser

Commands:

```bash
make proxy-procurement
```

```bash
make demo-ui
```

Optional if `5100` is busy:

```bash
PORT=5101 make demo-ui
```

## Three-Minute Script

### 0:00 to 0:20

Say:

> Mirage sits between an agent and the outside world. It intercepts outbound actions, evaluates them against policy, returns a safe mocked response, and writes a deterministic trace.

Show:

- proxy terminal already running
- demo UI open but untouched

### 0:20 to 1:10

Run:

```bash
make procurement-demo-risky
```

Say:

> Here the agent is doing a normal procurement workflow. It first looks up an approved supplier, then tries to submit a bid that is above the allowed threshold.

As the command runs, call out:

- supplier lookup succeeds
- bid submission is flagged by Mirage
- workflow still continues with a mocked response instead of leaking a real side effect

Pause on:

- Mirage outcome
- decision summary
- trace path

### 1:10 to 2:00

Switch to the UI and click `Risky`.

Say:

> The UI is not the source of truth. It is the explainer layer over the same run shape. You can see the exact request, the policy evaluation, the mocked response, and the trace Mirage produced.

Show:

- live playback mode
- final outcome
- policy decision row
- trace path
- raw trace

### 2:00 to 2:30

Click `Safe`.

Say:

> Same workflow, compliant input. Mirage keeps it green.

Show:

- same route pattern
- allowed outcome
- policy passes

### 2:30 to 2:50

Optionally click `Unmatched`.

Say:

> If the agent hits an unconfigured route, Mirage fails clearly instead of silently letting a side effect through.

Use this only for technical audiences or if there is time.

### 2:50 to 3:00

Close with:

> The point of Mirage is not to build a nicer mock server. The point is to give agent teams a CI boundary for side effects, with policy decisions and traces they can actually inspect.

## Demo Notes

- Lead with `risky`. It has the clearest value signal.
- Keep the UI as the second layer, not the first proof.
- If the audience is less technical, invert the order:
  - click `Risky` in the UI first
  - then run the terminal command to prove it is real
- Keep the trace collapsed until you need the credibility reveal.

## Backup Plan

If live playback feels slow or fragile, turn off `Live playback mode` in the UI and use instant render.
