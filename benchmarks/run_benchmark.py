"""Run Mirage benchmark scenarios against a Mirage gateway in enforce mode.

Each scenario YAML (under `benchmarks/scenarios/`) declares a sequence
of synthetic agent actions and a `policy_file` to evaluate them
against. The runner spins up a `MirageGateway` instance, replays each
action through it, and compares the gateway's outcome to the scenario's
ground-truth `is_violation` label.

Reported numbers:

  containment_rate     TP / (TP + FN)  recall on policy-violating actions
  false_positive_rate  FP / (FP + TN)  share of clean actions wrongly blocked
  precision            TP / (TP + FP)  share of blocks that were correct
  decision_latency     p50/p95/p99 in microseconds, per-policy evaluation

Outputs a JSON report to `benchmarks/results/<scenario>.json` and a
human-readable summary table on stdout.

Usage:
  python -m benchmarks.run_benchmark
  python -m benchmarks.run_benchmark --scenario pii_leak
  python -m benchmarks.run_benchmark --scenarios-dir benchmarks/scenarios
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml

from mirage.gateway import MirageGateway
from mirage.metrics import compute_containment_metrics, get_run_metrics

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIOS_DIR = REPO_ROOT / "benchmarks" / "scenarios"
DEFAULT_RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"


@dataclass(frozen=True)
class BenchmarkResult:
    scenario: str
    policy_file: str
    total_actions: int
    bad_actions: int
    good_actions: int
    true_positives: int
    false_negatives: int
    true_negatives: int
    false_positives: int
    containment_rate: float
    false_positive_rate: float
    precision: float
    decision_latency_p50_us: int | None
    decision_latency_p95_us: int | None
    decision_latency_p99_us: int | None
    time_to_decide_p50_us: int | None
    time_to_decide_p95_us: int | None
    time_to_decide_p99_us: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_scenario(scenario_path: Path) -> BenchmarkResult:
    payload = _load_scenario(scenario_path)
    actions = payload["actions"]
    policy_path = (REPO_ROOT / payload["policy_file"]).resolve()

    transport = httpx.MockTransport(_stub_upstream)
    upstream = httpx.Client(transport=transport, base_url="https://upstream.benchmark")
    artifact_root = DEFAULT_RESULTS_DIR / "_traces" / payload["name"]
    run_id = f"bench-{payload['name']}"
    gateway = MirageGateway(
        upstream_url="https://upstream.benchmark",
        mode="enforce",
        policies_path=policy_path,
        artifact_root=artifact_root,
        upstream_client=upstream,
    )

    tp = fn = tn = fp = 0
    try:
        for action in actions:
            result = gateway.handle_request(
                method=action["method"],
                path=action["path"],
                payload=action["payload"],
                run_id=run_id,
            )
            blocked = result.outcome == "blocked"
            label = bool(action.get("is_violation", False))
            if label and blocked:
                tp += 1
            elif label and not blocked:
                fn += 1
            elif not label and not blocked:
                tn += 1
            else:
                fp += 1
    finally:
        gateway.close()

    bad = tp + fn
    good = tn + fp
    containment = tp / bad if bad > 0 else 1.0
    fpr = fp / good if good > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0

    detail = get_run_metrics(artifact_root, run_id)
    if detail is not None:
        metrics = compute_containment_metrics(detail.events, run_id=run_id)
    else:
        metrics = None

    return BenchmarkResult(
        scenario=payload["name"],
        policy_file=payload["policy_file"],
        total_actions=len(actions),
        bad_actions=bad,
        good_actions=good,
        true_positives=tp,
        false_negatives=fn,
        true_negatives=tn,
        false_positives=fp,
        containment_rate=containment,
        false_positive_rate=fpr,
        precision=precision,
        decision_latency_p50_us=metrics.decision_latency_p50_us if metrics else None,
        decision_latency_p95_us=metrics.decision_latency_p95_us if metrics else None,
        decision_latency_p99_us=metrics.decision_latency_p99_us if metrics else None,
        time_to_decide_p50_us=metrics.time_to_decide_p50_us if metrics else None,
        time_to_decide_p95_us=metrics.time_to_decide_p95_us if metrics else None,
        time_to_decide_p99_us=metrics.time_to_decide_p99_us if metrics else None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        default=DEFAULT_SCENARIOS_DIR,
        help="Directory containing scenario YAML files.",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Single scenario name to run (e.g. 'pii_leak'). Default: all.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory for JSON output reports.",
    )
    args = parser.parse_args(argv)

    args.results_dir.mkdir(parents=True, exist_ok=True)
    scenario_paths = _scenario_paths(args.scenarios_dir, args.scenario)
    if not scenario_paths:
        print(f"No scenarios found in {args.scenarios_dir}.")
        return 1

    print(_table_header())
    for path in scenario_paths:
        result = run_scenario(path)
        out = args.results_dir / f"{result.scenario}.json"
        out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(_table_row(result))

    return 0


def _stub_upstream(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"status": "ok"})


def _load_scenario(scenario_path: Path) -> dict[str, Any]:
    raw = scenario_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict) or "scenario" not in data:
        raise ValueError(f"{scenario_path}: scenario file must define a 'scenario' top-level key.")
    return data["scenario"]


def _scenario_paths(scenarios_dir: Path, scenario_name: str | None) -> list[Path]:
    if scenario_name:
        match = scenarios_dir / f"{scenario_name}_scenario.yaml"
        return [match] if match.exists() else []
    return sorted(scenarios_dir.glob("*_scenario.yaml"))


def _table_header() -> str:
    cols = [
        "scenario".ljust(20),
        "containment".rjust(13),
        "fpr".rjust(8),
        "precision".rjust(11),
        "lat p50 us".rjust(11),
        "lat p95 us".rjust(11),
        "lat p99 us".rjust(11),
        "ttd p50 us".rjust(11),
    ]
    bar = "-" * (sum(len(col) for col in cols) + 2 * (len(cols) - 1))
    return "  ".join(cols) + "\n" + bar


def _table_row(result: BenchmarkResult) -> str:
    return "  ".join(
        [
            result.scenario.ljust(20),
            f"{result.containment_rate:.3f}".rjust(13),
            f"{result.false_positive_rate:.3f}".rjust(8),
            f"{result.precision:.3f}".rjust(11),
            _fmt_int(result.decision_latency_p50_us).rjust(11),
            _fmt_int(result.decision_latency_p95_us).rjust(11),
            _fmt_int(result.decision_latency_p99_us).rjust(11),
            _fmt_int(result.time_to_decide_p50_us).rjust(11),
        ]
    )


def _fmt_int(value: int | None) -> str:
    return "n/a" if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
