"""Sequence-rule policy operators.

`PolicyEvaluator` is pure; it cannot count how many times a policy
has fired in a given run, or how recently. The sequence module owns
that state. It exposes two operators:

  count_lte    per-run cumulative call count must stay at or below the limit
  rate_lte     calls in a sliding window must stay at or below the limit

Both operators are evaluated by `SequenceEvaluator`, which maintains
an in-memory per-process counter dictionary keyed by
`(run_id, policy_name)`. Production deployments that need durable
rate limits will use the upcoming hosted control plane; the in-memory
tracker is the right shape for single-process gateway deployments and
the wrong shape for multi-process or restart-survives use cases.

Limits, called out explicitly:

  - In-memory only. Process restart wipes the state.
  - Single-process. Multi-worker gateway deployments do not share
    counters; each worker tracks its own. For accurate rate limiting
    across workers, run a single gateway process or pin agent traffic
    to one worker.
  - Per-policy-per-run. The counter key is
    `(run_id, policy_name)`. Same policy, different run id, different
    counter.

Sequence operators are handled outside `PolicyEvaluator` so the pure
evaluator's contract holds.
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Any, Deque

from .config import MirageConfig, PolicyConfig
from .policy import PolicyDecision, extract_field, path_matches


SEQUENCE_OPERATORS: frozenset[str] = frozenset({"rate_lte", "count_lte"})


class SequenceTracker:
    """In-memory, per-process tracker for sequence operators.

    Stores cumulative call counts and call timestamps keyed by
    `(run_id, policy_name)`. Thread-safe within a single process via
    an internal lock.
    """

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}
        self._timestamps: dict[tuple[str, str], Deque[float]] = {}
        self._lock = Lock()

    def record(
        self,
        *,
        run_id: str,
        policy_name: str,
        now: float | None = None,
    ) -> tuple[int, int]:
        """Record a call. Returns (new_count, current_window_count_unused).

        The second return value is reserved for window pruning callers
        that do not yet need it; rate evaluation prunes its own.
        """

        timestamp = now if now is not None else time.monotonic()
        key = (run_id, policy_name)
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + 1
            stamps = self._timestamps.setdefault(key, deque())
            stamps.append(timestamp)
            return self._counts[key], len(stamps)

    def count(self, *, run_id: str, policy_name: str) -> int:
        with self._lock:
            return self._counts.get((run_id, policy_name), 0)

    def count_in_window(
        self,
        *,
        run_id: str,
        policy_name: str,
        window_seconds: float,
        now: float | None = None,
    ) -> int:
        timestamp = now if now is not None else time.monotonic()
        cutoff = timestamp - window_seconds
        key = (run_id, policy_name)
        with self._lock:
            stamps = self._timestamps.get(key)
            if stamps is None:
                return 0
            while stamps and stamps[0] < cutoff:
                stamps.popleft()
            return len(stamps)

    def reset(self, *, run_id: str | None = None) -> None:
        """Drop counters. With `run_id`, only that run; without, all runs."""
        with self._lock:
            if run_id is None:
                self._counts.clear()
                self._timestamps.clear()
                return
            keys_to_remove = [key for key in self._counts if key[0] == run_id]
            for key in keys_to_remove:
                self._counts.pop(key, None)
                self._timestamps.pop(key, None)


class SequenceEvaluator:
    """Evaluates sequence-rule policies against a `SequenceTracker`.

    Policies whose operator is not in `SEQUENCE_OPERATORS` are
    skipped. Path and method filters apply identically to
    `PolicyEvaluator`, plus the `field` filter: if a policy declares a
    `field`, the call only counts when the field is present in the
    payload (use `field: ""` or omit `field` to count every call).
    """

    def __init__(self, config: MirageConfig, tracker: SequenceTracker):
        self._config = config
        self._tracker = tracker

    @property
    def tracker(self) -> SequenceTracker:
        return self._tracker

    def evaluate(
        self,
        *,
        method: str,
        path: str,
        payload: Any,
        run_id: str,
        now: float | None = None,
    ) -> list[PolicyDecision]:
        method_name = method.upper()
        decisions: list[PolicyDecision] = []
        timestamp = now if now is not None else time.monotonic()

        for policy in self._config.policies:
            if policy.operator not in SEQUENCE_OPERATORS:
                continue
            if policy.method and policy.method.upper() != method_name:
                continue
            if policy.path and not path_matches(policy.path, path):
                continue
            if policy.field:
                _, exists = extract_field(payload, policy.field)
                if not exists:
                    continue

            count, _ = self._tracker.record(
                run_id=run_id, policy_name=policy.name, now=timestamp
            )

            if policy.operator == "count_lte":
                limit = int(policy.value)
                passed = count <= limit
                actual: Any = count
                expected: Any = limit
            elif policy.operator == "rate_lte":
                limit, window_seconds = _parse_rate_value(policy.value)
                in_window = self._tracker.count_in_window(
                    run_id=run_id,
                    policy_name=policy.name,
                    window_seconds=window_seconds,
                    now=timestamp,
                )
                passed = in_window <= limit
                actual = {"in_window": in_window, "window_seconds": window_seconds}
                expected = {"limit": limit, "window_seconds": window_seconds}
            else:
                continue

            decisions.append(
                PolicyDecision(
                    name=policy.name,
                    passed=passed,
                    message=policy.message,
                    field=policy.field,
                    operator=policy.operator,
                    expected=expected,
                    actual=actual,
                    decision_latency_us=0,
                )
            )

        return decisions


def validate_sequence_value(policy: PolicyConfig) -> None:
    """Raise `ValueError` when a sequence policy's value is malformed.

    Centralised here so `mirage.config.PolicyConfig.validate_operator_value`
    can call into a single source of truth without dragging the
    operator implementations into `mirage.config`.
    """

    if policy.operator == "count_lte":
        if not isinstance(policy.value, int) or isinstance(policy.value, bool) or policy.value < 0:
            raise ValueError(
                "operator 'count_lte' requires a non-negative integer value."
            )
        return
    if policy.operator == "rate_lte":
        try:
            limit, window = _parse_rate_value(policy.value)
        except ValueError as exc:
            raise ValueError(
                "operator 'rate_lte' requires a mapping like "
                "{limit: <non-negative int>, window_seconds: <positive number>}."
            ) from exc
        if limit < 0 or window <= 0:
            raise ValueError(
                "operator 'rate_lte' requires limit >= 0 and window_seconds > 0."
            )
        return


def _parse_rate_value(value: Any) -> tuple[int, float]:
    if not isinstance(value, dict):
        raise ValueError("rate_lte value must be a mapping.")
    if "limit" not in value or "window_seconds" not in value:
        raise ValueError("rate_lte value must include 'limit' and 'window_seconds'.")
    limit = value["limit"]
    window = value["window_seconds"]
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("rate_lte 'limit' must be an integer.")
    if isinstance(window, bool) or not isinstance(window, (int, float)):
        raise ValueError("rate_lte 'window_seconds' must be a number.")
    return int(limit), float(window)


__all__ = [
    "SEQUENCE_OPERATORS",
    "SequenceEvaluator",
    "SequenceTracker",
    "validate_sequence_value",
]
