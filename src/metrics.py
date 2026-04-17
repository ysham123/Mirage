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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    trace_path: str
    event_count: int
    first_event_at: str | None
    last_event_at: str | None
    allowed_count: int
    policy_violation_count: int
    unmatched_route_count: int
    config_error_count: int

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
    allowed_count: int
    policy_violation_count: int
    unmatched_route_count: int
    config_error_count: int

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
        runs = [self._load_run_detail(path) for path in self._iter_trace_paths()]
        runs = [run for run in runs if run is not None]

        overview = OverviewSummary(
            run_count=len(runs),
            action_count=sum(run.summary.event_count for run in runs),
            allowed_count=sum(run.summary.allowed_count for run in runs),
            policy_violation_count=sum(run.summary.policy_violation_count for run in runs),
            unmatched_route_count=sum(run.summary.unmatched_route_count for run in runs),
            config_error_count=sum(run.summary.config_error_count for run in runs),
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
        return self._load_run_detail(trace_path)

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


def _final_outcome_for_run(detail: RunDetail) -> str:
    if detail.events:
        return detail.events[-1].outcome
    return "unknown"


def _headline_for_outcome(outcome: str) -> str:
    if outcome == "allowed":
        return "Compliant run stays green."
    if outcome == "policy_violation":
        return "Risky action gets flagged while the workflow keeps moving."
    if outcome == "unmatched_route":
        return "Unconfigured route fails clearly."
    if outcome == "config_error":
        return "Config error stops the run before interception."
    return "Mirage run review."
