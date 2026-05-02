# Real-world example policies

These five files are the starting point for any team adopting Mirage as
a runtime policy gateway. Each one targets a real production risk that
agents can create today: leaking PII into logs and third-party APIs,
acting on prompt-injection input, calling unapproved hosts, spending
unbounded amounts of money on a single action, and emitting unbounded
output that floods downstream systems.

| File | Risk addressed | Operator pattern |
| --- | --- | --- |
| `pii_redaction.yaml` | SSN, payment-card, and email leaks in payload text | `not_regex_match` |
| `prompt_injection.yaml` | Common prompt-injection markers in payload text | `not_regex_match` |
| `outbound_allowlist.yaml` | Outbound URL exfiltration to unknown hosts | `host_in` |
| `cost_guard.yaml` | Agents spending above approved limits per call | `lte` |
| `output_length_cap.yaml` | Runaway agent text generation | `length_lte` |

These examples are deliberately small. Treat them as templates: copy
one into your own policy file, narrow the `path` and `method` to your
endpoints, and tighten the regex or the host list to your domain.

## How to load one of these into your gateway

Start a Mirage gateway in passthrough mode against your real upstream,
pointing `--policies-path` at the example file. Passthrough logs every
policy decision but does not block, which is the right starting mode
for an existing service: see what the policy would catch before you
turn enforcement on.

```bash
mirage gateway \
  --upstream https://your-api.example.com \
  --mode passthrough \
  --policies-path examples/policies/pii_redaction.yaml
```

When the trace shows the right requests are being flagged, switch to
`--mode enforce` to start blocking.

```bash
mirage gateway \
  --upstream https://your-api.example.com \
  --mode enforce \
  --policies-path examples/policies/pii_redaction.yaml
```

## Validating a policy file

```bash
mirage validate-config --policies-path examples/policies/pii_redaction.yaml
```

This loads the file, checks every policy entry against the schema, and
prints a one-line summary on success or a precise file-and-field error
on failure.

## Combining example files

To enforce two example sets at once, concatenate them into a single
`policies.yaml`:

```bash
cat examples/policies/pii_redaction.yaml \
    examples/policies/cost_guard.yaml \
    > combined.yaml
# then edit `combined.yaml` to keep only one top-level `policies:` key
```

(Mirage policies are simply a list under a single top-level
`policies:` key. When merging, keep one such key and concatenate the
list entries beneath it.)
