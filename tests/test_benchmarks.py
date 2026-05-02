"""Tests for the benchmark harness.

These exercise the runner end-to-end against the bundled scenarios so
that a future change that breaks the harness (incompatible scenario
shape, regression in containment scoring, mismatch with the policy
files) fails CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.run_benchmark import run_scenario, BenchmarkResult


SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "scenarios"


@pytest.mark.parametrize(
    "scenario_filename",
    [
        "pii_leak_scenario.yaml",
        "prompt_injection_scenario.yaml",
        "cost_runaway_scenario.yaml",
    ],
)
def test_each_scenario_runs_and_scores_perfectly(scenario_filename, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_scenario(SCENARIOS_DIR / scenario_filename)
    assert isinstance(result, BenchmarkResult)
    assert result.total_actions == 100
    assert result.containment_rate == 1.0
    assert result.false_positive_rate == 0.0
    assert result.precision == 1.0


def test_pii_leak_scenario_has_expected_split():
    from benchmarks.run_benchmark import _load_scenario

    scenario = _load_scenario(SCENARIOS_DIR / "pii_leak_scenario.yaml")
    bad_count = sum(1 for action in scenario["actions"] if action.get("is_violation"))
    assert bad_count == 30


def test_prompt_injection_scenario_has_expected_split():
    from benchmarks.run_benchmark import _load_scenario

    scenario = _load_scenario(SCENARIOS_DIR / "prompt_injection_scenario.yaml")
    bad_count = sum(1 for action in scenario["actions"] if action.get("is_violation"))
    assert bad_count == 25


def test_cost_runaway_scenario_has_expected_split():
    from benchmarks.run_benchmark import _load_scenario

    scenario = _load_scenario(SCENARIOS_DIR / "cost_runaway_scenario.yaml")
    bad_count = sum(1 for action in scenario["actions"] if action.get("is_violation"))
    assert bad_count == 15
