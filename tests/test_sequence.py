"""Tests for sequence-rule operators (`count_lte`, `rate_lte`).

Covers `SequenceTracker` directly, `SequenceEvaluator` against a
synthetic config, config-error paths, and end-to-end gateway flow with
a sequence policy that fires after the limit is exceeded.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from mirage.config import (
    MirageConfig,
    MirageConfigError,
    PolicyConfig,
    load_mirage_config,
)
from mirage.gateway import MirageGateway
from mirage.sequence import (
    SEQUENCE_OPERATORS,
    SequenceEvaluator,
    SequenceTracker,
)


def _policy(**overrides) -> PolicyConfig:
    base = {
        "name": "test_sequence",
        "field": "",
        "operator": "count_lte",
        "value": 3,
        "message": "limit exceeded",
    }
    base.update(overrides)
    return PolicyConfig(**base)


def _config(policies: list[PolicyConfig]) -> MirageConfig:
    return MirageConfig(mocks=[], policies=policies)


def test_sequence_operators_set_is_explicit():
    assert SEQUENCE_OPERATORS == frozenset({"count_lte", "rate_lte"})


def test_count_lte_passes_until_limit_exceeded():
    tracker = SequenceTracker()
    config = _config([_policy(operator="count_lte", value=3)])
    evaluator = SequenceEvaluator(config, tracker)

    for _ in range(3):
        decisions = evaluator.evaluate(method="POST", path="/x", payload={}, run_id="r")
        assert decisions[0].passed is True

    decisions = evaluator.evaluate(method="POST", path="/x", payload={}, run_id="r")
    assert decisions[0].passed is False
    assert decisions[0].actual == 4
    assert decisions[0].expected == 3


def test_count_lte_keys_are_per_run():
    tracker = SequenceTracker()
    config = _config([_policy(operator="count_lte", value=2)])
    evaluator = SequenceEvaluator(config, tracker)

    for run_id in ("run-a", "run-b"):
        for _ in range(2):
            decisions = evaluator.evaluate(method="POST", path="/x", payload={}, run_id=run_id)
            assert decisions[0].passed is True


def test_count_lte_filters_by_method_and_path():
    tracker = SequenceTracker()
    config = _config(
        [_policy(operator="count_lte", value=1, method="POST", path="/v1/submit_bid")]
    )
    evaluator = SequenceEvaluator(config, tracker)

    # Different path -> not counted, no decision.
    decisions = evaluator.evaluate(method="POST", path="/other", payload={}, run_id="r")
    assert decisions == []

    decisions = evaluator.evaluate(method="POST", path="/v1/submit_bid", payload={}, run_id="r")
    assert decisions[0].passed is True

    decisions = evaluator.evaluate(method="POST", path="/v1/submit_bid", payload={}, run_id="r")
    assert decisions[0].passed is False


def test_count_lte_field_filter_only_counts_when_present():
    tracker = SequenceTracker()
    config = _config([_policy(operator="count_lte", value=2, field="bid_amount")])
    evaluator = SequenceEvaluator(config, tracker)

    # Field absent -> not counted.
    decisions = evaluator.evaluate(method="POST", path="/x", payload={}, run_id="r")
    assert decisions == []

    decisions = evaluator.evaluate(
        method="POST", path="/x", payload={"bid_amount": 5}, run_id="r"
    )
    assert decisions[0].passed is True


def test_rate_lte_window_sliding_correctly():
    tracker = SequenceTracker()
    config = _config(
        [
            _policy(
                operator="rate_lte",
                value={"limit": 2, "window_seconds": 10},
            )
        ]
    )
    evaluator = SequenceEvaluator(config, tracker)

    # 2 within window: passes
    evaluator.evaluate(method="POST", path="/x", payload={}, run_id="r", now=100.0)
    decisions = evaluator.evaluate(
        method="POST", path="/x", payload={}, run_id="r", now=101.0
    )
    assert decisions[0].passed is True

    # 3rd within window: fails
    decisions = evaluator.evaluate(
        method="POST", path="/x", payload={}, run_id="r", now=102.0
    )
    assert decisions[0].passed is False

    # 11s later (outside window): passes again
    decisions = evaluator.evaluate(
        method="POST", path="/x", payload={}, run_id="r", now=120.0
    )
    assert decisions[0].passed is True


def test_count_lte_rejects_negative_value_at_config_load(tmp_path):
    mocks = tmp_path / "mocks.yaml"
    policies = tmp_path / "policies.yaml"
    mocks.write_text("mocks: []\n", encoding="utf-8")
    policies.write_text(
        "policies:\n"
        "  - name: bad_count\n"
        "    field: ''\n"
        "    operator: count_lte\n"
        "    value: -1\n"
        "    message: bad\n",
        encoding="utf-8",
    )
    with pytest.raises(MirageConfigError) as exc_info:
        load_mirage_config(mocks, policies)
    assert "count_lte" in str(exc_info.value)


def test_rate_lte_rejects_non_mapping_value_at_config_load(tmp_path):
    mocks = tmp_path / "mocks.yaml"
    policies = tmp_path / "policies.yaml"
    mocks.write_text("mocks: []\n", encoding="utf-8")
    policies.write_text(
        "policies:\n"
        "  - name: bad_rate\n"
        "    field: ''\n"
        "    operator: rate_lte\n"
        "    value: 10\n"
        "    message: bad\n",
        encoding="utf-8",
    )
    with pytest.raises(MirageConfigError) as exc_info:
        load_mirage_config(mocks, policies)
    assert "rate_lte" in str(exc_info.value)


def test_rate_lte_rejects_zero_window_at_config_load(tmp_path):
    mocks = tmp_path / "mocks.yaml"
    policies = tmp_path / "policies.yaml"
    mocks.write_text("mocks: []\n", encoding="utf-8")
    policies.write_text(
        "policies:\n"
        "  - name: bad_window\n"
        "    field: ''\n"
        "    operator: rate_lte\n"
        "    value:\n"
        "      limit: 5\n"
        "      window_seconds: 0\n"
        "    message: bad\n",
        encoding="utf-8",
    )
    with pytest.raises(MirageConfigError) as exc_info:
        load_mirage_config(mocks, policies)
    assert "rate_lte" in str(exc_info.value)


def test_sequence_tracker_reset_drops_one_run_only():
    tracker = SequenceTracker()
    tracker.record(run_id="r1", policy_name="p")
    tracker.record(run_id="r2", policy_name="p")
    tracker.reset(run_id="r1")
    assert tracker.count(run_id="r1", policy_name="p") == 0
    assert tracker.count(run_id="r2", policy_name="p") == 1


def test_gateway_sequence_policy_blocks_after_limit_in_enforce_mode(tmp_path):
    mocks = tmp_path / "mocks.yaml"
    policies = tmp_path / "policies.yaml"
    mocks.write_text("mocks: []\n", encoding="utf-8")
    policies.write_text(
        "policies:\n"
        "  - name: cap_calls\n"
        "    field: ''\n"
        "    operator: count_lte\n"
        "    value: 2\n"
        "    method: POST\n"
        "    path: /v1/anything\n"
        "    message: Too many calls per run.\n",
        encoding="utf-8",
    )

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"status": "ok"})
    )
    upstream = httpx.Client(transport=transport, base_url="https://upstream")

    gateway = MirageGateway(
        upstream_url="https://upstream",
        mode="enforce",
        policies_path=policies,
        artifact_root=tmp_path / "artifacts" / "traces",
        upstream_client=upstream,
    )
    try:
        for index in range(2):
            result = gateway.handle_request(
                method="POST", path="/v1/anything", payload={}, run_id="seq-run"
            )
            assert result.outcome == "allowed", f"call {index + 1}"

        result = gateway.handle_request(
            method="POST", path="/v1/anything", payload={}, run_id="seq-run"
        )
        assert result.outcome == "blocked"
        assert "cap_calls" in result.body["message"]
    finally:
        gateway.close()
