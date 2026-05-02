# Mirage benchmarks

Mirage ships a reproducible benchmark harness so the headline numbers
the README and pitch deck reference are grounded in measured runs, not
vibes. Run `make bench` from a checkout to reproduce them.

## Quick numbers

These are the current scores on the bundled synthetic scenarios. Run
`make bench` to regenerate.

| Scenario | Containment | False positive rate | Precision | Decision latency p50 / p95 / p99 (us) | Time-to-decide p50 (us) |
| --- | --- | --- | --- | --- | --- |
| `pii_leak` | 1.000 | 0.000 | 1.000 | 2 / 4 / 6 | ~1100 |
| `prompt_injection` | 1.000 | 0.000 | 1.000 | 4 / 7 / 7 | ~530 |
| `cost_runaway` | 1.000 | 0.000 | 1.000 | 1 / 2 / 4 | ~920 |

The exact numbers vary slightly run-to-run (microsecond timing on a
laptop is noisy at this scale), but the shape is stable: 100%
containment, 0% false positives, sub-10us per-policy decision latency,
sub-millisecond gateway-internal time-to-decide on synthetic traffic.

## Methodology

Each scenario is a YAML file under
[`benchmarks/scenarios/`](benchmarks/scenarios) describing 100
synthetic agent actions. A subset of those actions are deliberately
labelled `is_violation: true`; the rest are clean.

The runner ([`benchmarks/run_benchmark.py`](benchmarks/run_benchmark.py))
spins up a `MirageGateway` instance in `enforce` mode against an in-
process stub upstream (no real network), replays each action through
the gateway, and records:

- the gateway's outcome (`blocked` vs other), compared to the action's
  ground-truth label
- per-policy decision latency, captured by `PolicyEvaluator` via
  `time.perf_counter_ns()`
- gateway-internal time-to-decide, captured by `MirageGateway` from
  request entry to allow/block decision (before upstream forwarding)

Reported numbers:

- **Containment** = TP / (TP + FN). Of the actions Mirage *should*
  block (ground-truth bad), what share did it actually block?
- **False positive rate** = FP / (FP + TN). Of the clean actions, what
  share did Mirage incorrectly block?
- **Precision** = TP / (TP + FP). Of the actions Mirage blocked, what
  share were correctly blocked?
- **Decision latency p50 / p95 / p99**: per-policy evaluation cost.
  This is the cost of running one policy against one payload field,
  not the end-to-end gateway round-trip.
- **Time-to-decide p50 / p95 / p99**: gateway-internal cost from
  request entry to allow/block decision (before upstream forwarding).
  This is the latency budget the gateway adds on top of the upstream.

The baseline runner
([`benchmarks/baseline_runner.py`](benchmarks/baseline_runner.py))
replays the same scenarios directly against the stub upstream with no
gateway in the path, so the latency overhead Mirage adds can be
isolated. Run with `make bench-baseline`.

## Scenarios

| Scenario | Policy file | Actions | Bad actions |
| --- | --- | --- | --- |
| `pii_leak` | [`examples/policies/pii_redaction.yaml`](examples/policies/pii_redaction.yaml) | 100 | 30 (SSN-shaped strings in payload text) |
| `prompt_injection` | [`examples/policies/prompt_injection.yaml`](examples/policies/prompt_injection.yaml) | 100 | 25 (prompt-injection markers in payload text) |
| `cost_runaway` | [`examples/policies/cost_guard.yaml`](examples/policies/cost_guard.yaml) | 100 | 15 (monetary fields above caps) |

Each scenario YAML is seed-stable: regenerating the bundled scenarios
from the same seed produces byte-identical files. To reproduce a
scenario from scratch with a different seed, edit the generator and
run it.

## How to run

```bash
make bench           # all three scenarios + summary table
make bench-baseline  # no-gateway upstream baseline for latency context
```

Equivalent direct commands:

```bash
python -m benchmarks.run_benchmark
python -m benchmarks.run_benchmark --scenario pii_leak
python -m benchmarks.baseline_runner
```

JSON reports land under `benchmarks/results/`:

- `benchmarks/results/<scenario>.json`: the full benchmark result
- `benchmarks/results/<scenario>_baseline.json`: the no-gateway baseline
- `benchmarks/results/_traces/`: gateway trace events used to derive
  the latency percentiles (also useful for debugging)

## Limitations

These benchmarks are synthetic and intentionally simple. They establish
a reproducible methodology and a current scoring floor. Real-world
numbers against production traffic are forthcoming as design partners
begin pilots in May 2026.

Specific limits to be aware of:

- **Synthetic data.** Bad actions are constructed to match the
  policies. A scenario with a regex-shaped SSN will be caught by a
  regex-shaped policy. The benchmark does not measure how Mirage
  performs against adversarial inputs that look bad but pass current
  patterns, or against benign inputs that look bad and trip false
  positives. Adversarial benchmarks are the next milestone.
- **No false-negative measurement on the gateway path.** Mirage cannot
  label actions it never saw. For runtime measurement,
  `compute_containment_metrics` is honest about this and only reports
  the share of policy-violating actions the gateway prevented from
  reaching the upstream. The benchmark harness, in contrast, has
  ground-truth labels for every action, so it can report true
  false-negative numbers; that is why the benchmark is the right
  number to cite for accuracy.
- **In-process stub upstream.** Real upstreams will add their own
  network and processing latency. The Mirage-only overhead is what
  shows up here; total agent-observed latency in production will be
  Mirage overhead plus upstream cost.
- **Single-process, single-machine.** No measurement of throughput
  under concurrent load yet. The gateway is single-process FastAPI;
  horizontal scale is the operator's responsibility.
- **Each request reloads the policy file from disk.** The gateway is
  conservative: it re-reads `policies.yaml` on every request so an
  operator editing the policy file mid-run sees the change without
  restarting. That re-read shows up in the time-to-decide percentile.
  Caching with a file-mtime check is on the v0.3 roadmap.
- **No SLA assertions.** The benchmark reports numbers; it does not
  fail on regression. CI gating on benchmark thresholds is on the
  v0.3 roadmap.

## Design partners and real numbers

If you are running an agent platform and want the real-traffic version
of these numbers (containment rate against your own action stream,
false-positive rate against your own payloads), open an issue at
[github.com/ysham123/Mirage/issues](https://github.com/ysham123/Mirage/issues)
and we will get a pilot scoped.
