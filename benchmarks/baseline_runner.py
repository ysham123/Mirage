"""Baseline (no-gateway) runner for the Mirage benchmark scenarios.

Replays each scenario's actions directly against a stub upstream
without going through the Mirage gateway. Reports time-to-respond
percentiles. Subtracted from the gateway run, this gives the latency
overhead Mirage adds.

Usage:
  python -m benchmarks.baseline_runner
  python -m benchmarks.baseline_runner --scenario pii_leak
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIOS_DIR = REPO_ROOT / "benchmarks" / "scenarios"
DEFAULT_RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"


@dataclass(frozen=True)
class BaselineResult:
    scenario: str
    total_actions: int
    upstream_p50_us: int | None
    upstream_p95_us: int | None
    upstream_p99_us: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_baseline(scenario_path: Path) -> BaselineResult:
    payload = _load_scenario(scenario_path)
    actions = payload["actions"]

    transport = httpx.MockTransport(_stub_upstream)
    client = httpx.Client(transport=transport, base_url="https://upstream.benchmark")

    durations: list[int] = []
    try:
        for action in actions:
            t0 = time.perf_counter_ns()
            client.request(
                action["method"],
                action["path"],
                json=action["payload"] if action["payload"] is not None else None,
            )
            durations.append(max(0, (time.perf_counter_ns() - t0) // 1000))
    finally:
        client.close()

    return BaselineResult(
        scenario=payload["name"],
        total_actions=len(actions),
        upstream_p50_us=_percentile(durations, 50),
        upstream_p95_us=_percentile(durations, 95),
        upstream_p99_us=_percentile(durations, 99),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios-dir", type=Path, default=DEFAULT_SCENARIOS_DIR)
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    args = parser.parse_args(argv)

    args.results_dir.mkdir(parents=True, exist_ok=True)
    scenario_paths = _scenario_paths(args.scenarios_dir, args.scenario)
    if not scenario_paths:
        print(f"No scenarios found in {args.scenarios_dir}.")
        return 1

    print("scenario".ljust(20), "p50_us".rjust(8), "p95_us".rjust(8), "p99_us".rjust(8))
    print("-" * 50)
    for path in scenario_paths:
        result = run_baseline(path)
        out = args.results_dir / f"{result.scenario}_baseline.json"
        out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(
            result.scenario.ljust(20),
            _fmt_int(result.upstream_p50_us).rjust(8),
            _fmt_int(result.upstream_p95_us).rjust(8),
            _fmt_int(result.upstream_p99_us).rjust(8),
        )
    return 0


def _stub_upstream(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"status": "ok"})


def _load_scenario(scenario_path: Path) -> dict[str, Any]:
    data = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "scenario" not in data:
        raise ValueError(f"{scenario_path}: scenario file must define a 'scenario' top-level key.")
    return data["scenario"]


def _scenario_paths(scenarios_dir: Path, scenario_name: str | None) -> list[Path]:
    if scenario_name:
        match = scenarios_dir / f"{scenario_name}_scenario.yaml"
        return [match] if match.exists() else []
    return sorted(scenarios_dir.glob("*_scenario.yaml"))


def _percentile(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (percentile / 100) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = rank - lower
    interpolated = sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])
    return int(round(interpolated))


def _fmt_int(value: int | None) -> str:
    return "n/a" if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
