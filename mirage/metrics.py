from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class PolicyDecisionRecord:
    name: str
    passed: bool
    message: str
    field: str
    operator: str
    expected: Any = None
    actual: Any = None
    decision_latency_us: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunEventRecord:
    timestamp: str | None
    request: dict[str, Any]
    outcome: str
    message: str | None
    matched_mock: str | None
    policy_passed: bool
    response: dict[str, Any]
    policy_decisions: list[PolicyDecisionRecord]
    time_to_decide_us: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    trace_path: str
    event_count: int
    first_event_at: str | None
    last_event_at: str | None
    # CI-mode outcomes (mirage.proxy / MirageEngine).
    allowed_count: int
    policy_violation_count: int
    unmatched_route_count: int
    config_error_count: int
    # Gateway-mode outcomes (mirage.gateway / MirageGateway).
    blocked_count: int = 0
    flagged_count: int = 0
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunDetail:
    summary: RunSummary
    events: list[RunEventRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "events": [event.to_dict() for event in self.events],
        }


@dataclass(frozen=True)
class EndpointSummary:
    method: str
    path: str
    action_count: int
    allowed_count: int
    policy_violation_count: int
    unmatched_route_count: int
    config_error_count: int
    blocked_count: int
    flagged_count: int
    error_count: int
    run_count: int
    last_seen_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyFailureSummary:
    name: str
    failure_count: int
    run_count: int
    last_seen_at: str | None
    field: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OverviewSummary:
    run_count: int
    action_count: int
    # CI-mode outcomes.
    allowed_count: int
    policy_violation_count: int
    unmatched_route_count: int
    config_error_count: int
    # Gateway-mode outcomes.
    blocked_count: int
    flagged_count: int
    error_count: int
    # Cross-mode rollup: any non-allowed final outcome counts as risky.
    risky_run_count: int
    # Fleet-wide containment rate: blocked / max(1, blocked + policy_violation_count + flagged).
    # `None` when no decisions exist across the fleet.
    containment_rate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContainmentMetrics:
    """Per-run containment and latency rollup.

    `containment_rate` answers the operator question: of all the actions
    Mirage believed to be policy-violating, what fraction were actually
    prevented from reaching the upstream? It is computed as
    `blocked / max(1, blocked + policy_violation_count + flagged)` so a
    run with no violations resolves to `1.0`. Flagged actions count
    against containment because they reached the upstream even though
    policy said no (passthrough mode by design).

    This metric does NOT measure false negatives. Mirage cannot label
    actions it never saw, so any policy-violating action that escaped
    the gateway entirely is invisible here. False-negative measurement
    is a benchmark concern (see `benchmarks/`), not a runtime concern.

    `decision_latency_*_us` percentiles describe per-policy evaluation
    latency, captured by `PolicyEvaluator.evaluate`. `time_to_decide_*_us`
    percentiles describe gateway end-to-end decision time, captured by
    `MirageGateway.handle_request` from request entry to allow/block
    decision (before upstream forwarding).

    Percentile fields return `None` when no data is available for that
    measurement; they do not return zero.
    """

    run_id: str
    total_actions: int
    blocked_count: int
    flagged_count: int
    allowed_count: int
    policy_violation_count: int
    containment_rate: float | None
    decision_latency_p50_us: int | None
    decision_latency_p95_us: int | None
    decision_latency_p99_us: int | None
    time_to_decide_p50_us: int | None
    time_to_decide_p95_us: int | None
    time_to_decide_p99_us: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DashboardSnapshot:
    overview: OverviewSummary
    recent_runs: list[RunSummary]
    top_endpoints: list[EndpointSummary]
    top_failing_policies: list[PolicyFailureSummary]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overview": self.overview.to_dict(),
            "recent_runs": [run.to_dict() for run in self.recent_runs],
            "top_endpoints": [endpoint.to_dict() for endpoint in self.top_endpoints],
            "top_failing_policies": [policy.to_dict() for policy in self.top_failing_policies],
        }


class TraceMetricsStore:
    def __init__(self, artifact_root: str | Path):
        self.artifact_root = Path(artifact_root)

    def snapshot(self, *, recent_limit: int = 10, top_limit: int = 10) -> DashboardSnapshot:
        runs: list[RunDetail] = []
        for path in self._iter_trace_paths():
            try:
                run = self._load_run_detail(path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if run is not None:
                runs.append(run)

        blocked_total = sum(run.summary.blocked_count for run in runs)
        flagged_total = sum(run.summary.flagged_count for run in runs)
        violation_total = sum(run.summary.policy_violation_count for run in runs)
        containment_total = blocked_total + flagged_total + violation_total
        fleet_containment = (
            blocked_total / containment_total if containment_total > 0 else None
        )

        overview = OverviewSummary(
            run_count=len(runs),
            action_count=sum(run.summary.event_count for run in runs),
            allowed_count=sum(run.summary.allowed_count for run in runs),
            policy_violation_count=violation_total,
            unmatched_route_count=sum(run.summary.unmatched_route_count for run in runs),
            config_error_count=sum(run.summary.config_error_count for run in runs),
            blocked_count=blocked_total,
            flagged_count=flagged_total,
            error_count=sum(run.summary.error_count for run in runs),
            risky_run_count=sum(
                1 for run in runs if _final_outcome_for_run(run) not in ("allowed", "unknown")
            ),
            containment_rate=fleet_containment,
        )

        recent_runs = sorted(
            (run.summary for run in runs),
            key=lambda summary: (-_sort_timestamp(summary.last_event_at), summary.run_id),
        )[: max(0, recent_limit)]

        top_endpoints = self._summarize_endpoints(runs, limit=top_limit)
        top_policies = self._summarize_policy_failures(runs, limit=top_limit)

        return DashboardSnapshot(
            overview=overview,
            recent_runs=recent_runs,
            top_endpoints=top_endpoints,
            top_failing_policies=top_policies,
        )

    def get_run(self, run_id: str) -> RunDetail | None:
        trace_path = self._trace_path_for_run_id(run_id)
        if not trace_path.exists():
            return None
        try:
            return self._load_run_detail(trace_path)
        except (OSError, ValueError, json.JSONDecodeError):
            return None

    def _iter_trace_paths(self) -> list[Path]:
        if not self.artifact_root.exists():
            return []
        return sorted(
            (path for path in self.artifact_root.glob("*.json") if path.is_file()),
            key=lambda path: path.name,
        )

    def _trace_path_for_run_id(self, run_id: str) -> Path:
        safe_run_id = run_id.replace("/", "_")
        return self.artifact_root / f"{safe_run_id}.json"

    def _load_run_detail(self, path: Path) -> RunDetail | None:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return None

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a top-level mapping.")

        run_id = str(data.get("run_id") or path.stem)
        events_raw = data.get("events", [])
        if not isinstance(events_raw, list):
            raise ValueError(f"{path} must contain an events list.")

        events = [self._parse_event(event) for event in events_raw if isinstance(event, dict)]
        if len(events) != len(events_raw):
            raise ValueError(f"{path} contains a malformed trace event.")

        counts = Counter(event.outcome for event in events)
        timestamps = [event.timestamp for event in events if event.timestamp is not None]
        summary = RunSummary(
            run_id=run_id,
            trace_path=str(path),
            event_count=len(events),
            first_event_at=_min_timestamp(timestamps),
            last_event_at=_max_timestamp(timestamps),
            allowed_count=counts["allowed"],
            policy_violation_count=counts["policy_violation"],
            unmatched_route_count=counts["unmatched_route"],
            config_error_count=counts["config_error"],
            blocked_count=counts["blocked"],
            flagged_count=counts["flagged"],
            error_count=counts["error"],
        )
        return RunDetail(summary=summary, events=events)

    def _parse_event(self, event: dict[str, Any]) -> RunEventRecord:
        request = event.get("request") if isinstance(event.get("request"), dict) else {}
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        decisions_raw = event.get("policy_decisions", [])
        decisions = [
            PolicyDecisionRecord(
                name=str(decision.get("name", "")),
                passed=bool(decision.get("passed", False)),
                message=str(decision.get("message", "")),
                field=str(decision.get("field", "")),
                operator=str(decision.get("operator", "")),
                expected=decision.get("expected"),
                actual=decision.get("actual"),
                decision_latency_us=_coerce_non_negative_int(decision.get("decision_latency_us")),
            )
            for decision in decisions_raw
            if isinstance(decision, dict)
        ]

        return RunEventRecord(
            timestamp=_normalize_timestamp(event.get("timestamp")),
            request=request,
            outcome=str(event.get("outcome", "unknown")),
            message=event.get("message"),
            matched_mock=event.get("matched_mock"),
            policy_passed=bool(event.get("policy_passed", False)),
            response=response,
            policy_decisions=decisions,
            time_to_decide_us=_coerce_optional_non_negative_int(event.get("time_to_decide_us")),
        )

    def _summarize_endpoints(self, runs: list[RunDetail], *, limit: int) -> list[EndpointSummary]:
        endpoint_stats: dict[tuple[str, str], dict[str, Any]] = {}
        for run in runs:
            for event in run.events:
                method, path = _event_method_path(event.request)
                key = (method, path)
                stats = endpoint_stats.setdefault(
                    key,
                    {
                        "action_count": 0,
                        "allowed_count": 0,
                        "policy_violation_count": 0,
                        "unmatched_route_count": 0,
                        "config_error_count": 0,
                        "blocked_count": 0,
                        "flagged_count": 0,
                        "error_count": 0,
                        "run_ids": set(),
                        "last_seen_at": None,
                    },
                )
                stats["action_count"] += 1
                stats[f"{event.outcome}_count"] = stats.get(f"{event.outcome}_count", 0) + 1
                stats["run_ids"].add(run.summary.run_id)
                stats["last_seen_at"] = _max_timestamp([stats["last_seen_at"], event.timestamp])

        summaries = [
            EndpointSummary(
                method=method,
                path=path,
                action_count=stats["action_count"],
                allowed_count=stats["allowed_count"],
                policy_violation_count=stats["policy_violation_count"],
                unmatched_route_count=stats["unmatched_route_count"],
                config_error_count=stats["config_error_count"],
                blocked_count=stats["blocked_count"],
                flagged_count=stats["flagged_count"],
                error_count=stats["error_count"],
                run_count=len(stats["run_ids"]),
                last_seen_at=stats["last_seen_at"],
            )
            for (method, path), stats in endpoint_stats.items()
        ]
        return sorted(
            summaries,
            key=lambda summary: (-summary.action_count, summary.method, summary.path),
        )[: max(0, limit)]

    def _summarize_policy_failures(
        self, runs: list[RunDetail], *, limit: int
    ) -> list[PolicyFailureSummary]:
        policy_stats: dict[str, dict[str, Any]] = {}
        for run in runs:
            for event in run.events:
                for decision in event.policy_decisions:
                    if decision.passed:
                        continue
                    stats = policy_stats.setdefault(
                        decision.name,
                        {
                            "failure_count": 0,
                            "run_ids": set(),
                            "last_seen_at": None,
                            "field": decision.field,
                            "message": decision.message,
                        },
                    )
                    stats["failure_count"] += 1
                    stats["run_ids"].add(run.summary.run_id)
                    stats["last_seen_at"] = _max_timestamp([stats["last_seen_at"], event.timestamp])
                    if not stats.get("field"):
                        stats["field"] = decision.field
                    if not stats.get("message"):
                        stats["message"] = decision.message

        summaries = [
            PolicyFailureSummary(
                name=name,
                failure_count=stats["failure_count"],
                run_count=len(stats["run_ids"]),
                last_seen_at=stats["last_seen_at"],
                field=stats.get("field"),
                message=stats.get("message"),
            )
            for name, stats in policy_stats.items()
        ]
        return sorted(
            summaries,
            key=lambda summary: (-summary.failure_count, summary.name),
        )[: max(0, limit)]


def collect_dashboard_metrics(
    artifact_root: str | Path,
    *,
    recent_limit: int = 10,
    top_limit: int = 10,
) -> DashboardSnapshot:
    return TraceMetricsStore(artifact_root).snapshot(recent_limit=recent_limit, top_limit=top_limit)


def compute_containment_metrics(
    events: list[RunEventRecord], *, run_id: str
) -> ContainmentMetrics:
    """Roll up a list of trace events into a `ContainmentMetrics` snapshot.

    Containment rate is computed as
    `blocked / max(1, blocked + policy_violation + flagged)`.

    Interpretation: of all the actions Mirage believed to be policy-
    violating, what fraction were actually prevented from reaching the
    upstream? `blocked` only happens in gateway enforce mode.
    `policy_violation` only happens in CI mode (mock substitution).
    `flagged` happens in gateway passthrough mode and reaches upstream
    even though policy says no, so it counts against containment.

    This metric does NOT measure false negatives. Mirage cannot label
    actions it never saw, so any policy-violating action that escaped
    the gateway entirely is invisible here.

    Percentile fields return `None` when no data exists for that
    measurement; they do not return zero.
    """

    counts = Counter(event.outcome for event in events)
    blocked = counts.get("blocked", 0)
    flagged = counts.get("flagged", 0)
    allowed = counts.get("allowed", 0)
    violations = counts.get("policy_violation", 0)
    decision_pool = blocked + flagged + violations
    containment_rate = blocked / decision_pool if decision_pool > 0 else None

    decision_latencies: list[int] = [
        decision.decision_latency_us
        for event in events
        for decision in event.policy_decisions
        if decision.decision_latency_us is not None and decision.decision_latency_us > 0
    ]
    time_to_decide_values: list[int] = [
        event.time_to_decide_us
        for event in events
        if event.time_to_decide_us is not None and event.time_to_decide_us > 0
    ]

    return ContainmentMetrics(
        run_id=run_id,
        total_actions=len(events),
        blocked_count=blocked,
        flagged_count=flagged,
        allowed_count=allowed,
        policy_violation_count=violations,
        containment_rate=containment_rate,
        decision_latency_p50_us=_percentile(decision_latencies, 50),
        decision_latency_p95_us=_percentile(decision_latencies, 95),
        decision_latency_p99_us=_percentile(decision_latencies, 99),
        time_to_decide_p50_us=_percentile(time_to_decide_values, 50),
        time_to_decide_p95_us=_percentile(time_to_decide_values, 95),
        time_to_decide_p99_us=_percentile(time_to_decide_values, 99),
    )


def get_run_containment(
    artifact_root: str | Path, run_id: str
) -> ContainmentMetrics | None:
    detail = get_run_metrics(artifact_root, run_id)
    if detail is None:
        return None
    return compute_containment_metrics(detail.events, run_id=run_id)


def get_run_metrics(artifact_root: str | Path, run_id: str) -> RunDetail | None:
    return TraceMetricsStore(artifact_root).get_run(run_id)


def build_metrics_overview(
    artifact_root: str | Path,
    *,
    recent_limit: int = 10,
    top_limit: int = 10,
) -> dict[str, Any]:
    return collect_dashboard_metrics(
        artifact_root,
        recent_limit=recent_limit,
        top_limit=top_limit,
    ).to_dict()


def build_run_metrics(artifact_root: str | Path, run_id: str) -> dict[str, Any] | None:
    detail = get_run_metrics(artifact_root, run_id)
    if detail is None:
        return None

    trace_path = Path(detail.summary.trace_path)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    final_outcome = _final_outcome_for_run(detail)
    return {
        "run_id": detail.summary.run_id,
        "trace_path": detail.summary.trace_path,
        "trace": trace,
        "headline": _headline_for_outcome(final_outcome),
        "final_outcome": final_outcome,
        "events": [event.to_dict() for event in detail.events],
    }


def _event_method_path(request: dict[str, Any]) -> tuple[str, str]:
    method = str(request.get("method") or "UNKNOWN").upper()
    path = str(request.get("path") or "UNKNOWN")
    return method, path


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _datetime_to_iso(value)

    text = str(value)
    try:
        return _datetime_to_iso(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return text


def _datetime_to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _parse_sort_timestamp(value: str | None) -> float:
    if value is None:
        return float("-inf")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return float("-inf")


def _sort_timestamp(value: str | None) -> float:
    return _parse_sort_timestamp(value)


def _min_timestamp(values: Iterable[str | None]) -> str | None:
    parsed = [value for value in values if value is not None]
    if not parsed:
        return None
    return min(parsed, key=_parse_sort_timestamp)


def _max_timestamp(values: Iterable[str | None]) -> str | None:
    parsed = [value for value in values if value is not None]
    if not parsed:
        return None
    return max(parsed, key=_parse_sort_timestamp)


def _percentile(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be between 0 and 100")
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (percentile / 100) * (len(sorted_values) - 1)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = rank - lower_index
    interpolated = sorted_values[lower_index] + fraction * (
        sorted_values[upper_index] - sorted_values[lower_index]
    )
    return int(round(interpolated))


def _coerce_non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))


def _coerce_optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return max(0, int(value))


def _final_outcome_for_run(detail: RunDetail) -> str:
    if detail.events:
        return detail.events[-1].outcome
    return "unknown"


def _headline_for_outcome(outcome: str) -> str:
    # CI-mode outcomes.
    if outcome == "allowed":
        return "Compliant run stays green."
    if outcome == "policy_violation":
        return "Risky action gets flagged while the workflow keeps moving."
    if outcome == "unmatched_route":
        return "Unconfigured route fails clearly."
    if outcome == "config_error":
        return "Config error stops the run before interception."
    # Gateway-mode outcomes.
    if outcome == "blocked":
        return "Gateway blocked a policy-violating action before it reached the upstream."
    if outcome == "flagged":
        return "Gateway flagged a policy violation in passthrough mode and let the call through."
    if outcome == "error":
        return "Gateway hit an error decision path; check upstream and config."
    return "Mirage run review."
