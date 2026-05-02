import json
from pathlib import Path

from mirage.metrics import (
    ContainmentMetrics,
    DashboardSnapshot,
    RunEventRecord,
    TraceMetricsStore,
    collect_dashboard_metrics,
    compute_containment_metrics,
    get_run_containment,
    get_run_metrics,
)


def _trace_event(
    *,
    timestamp: str,
    method: str,
    path: str,
    outcome: str,
    status_code: int,
    policy_decisions: list[dict] | None = None,
    message: str | None = None,
    matched_mock: str | None = None,
    policy_passed: bool = True,
) -> dict:
    return {
        "timestamp": timestamp,
        "run_id": "unused",
        "request": {
            "method": method,
            "path": path,
            "payload": {},
            "headers": {"x-mirage-run-id": "unused"},
        },
        "outcome": outcome,
        "message": message,
        "matched_mock": matched_mock,
        "policy_passed": policy_passed,
        "policy_decisions": policy_decisions or [],
        "response": {
            "status_code": status_code,
            "body": {"status": "success"},
        },
    }


def _write_trace(root: Path, run_id: str, events: list[dict]) -> Path:
    path = root / f"{run_id}.json"
    path.write_text(json.dumps({"run_id": run_id, "events": events}, indent=2), encoding="utf-8")
    return path


def test_collect_dashboard_metrics_rolls_up_runs_endpoints_and_policies(tmp_path):
    _write_trace(
        tmp_path,
        "alpha",
        [
            _trace_event(
                timestamp="2026-03-27T10:00:00+00:00",
                method="GET",
                path="/v1/suppliers/SUP-001",
                outcome="allowed",
                status_code=200,
                matched_mock="get_supplier_sup_001",
            ),
            _trace_event(
                timestamp="2026-03-27T10:01:00+00:00",
                method="POST",
                path="/v1/submit_bid",
                outcome="policy_violation",
                status_code=200,
                matched_mock="submit_bid",
                policy_passed=False,
                message="Mirage policy violation: enforce_bid_limit...",
                policy_decisions=[
                    {
                        "name": "enforce_bid_limit",
                        "passed": False,
                        "message": "Agents cannot submit bids above the approved threshold.",
                        "field": "bid_amount",
                        "operator": "lte",
                        "expected": 10000,
                        "actual": 50000.0,
                    }
                ],
            ),
        ],
    )
    _write_trace(
        tmp_path,
        "beta",
        [
            _trace_event(
                timestamp="2026-03-27T11:00:00+00:00",
                method="POST",
                path="/v1/submit_bid",
                outcome="policy_violation",
                status_code=200,
                matched_mock="submit_bid",
                policy_passed=False,
                message="Mirage policy violation: require_approved_supplier...",
                policy_decisions=[
                    {
                        "name": "require_approved_supplier",
                        "passed": False,
                        "message": "Procurement bids must use approved suppliers.",
                        "field": "supplier.risk_tier",
                        "operator": "eq",
                        "expected": "approved",
                        "actual": "blocked",
                    },
                    {
                        "name": "enforce_bid_limit",
                        "passed": False,
                        "message": "Agents cannot submit bids above the approved threshold.",
                        "field": "bid_amount",
                        "operator": "lte",
                        "expected": 10000,
                        "actual": 25000.0,
                    },
                ],
            )
        ],
    )
    _write_trace(
        tmp_path,
        "gamma",
        [
            _trace_event(
                timestamp="2026-03-27T12:00:00+00:00",
                method="POST",
                path="/v1/suppliers",
                outcome="unmatched_route",
                status_code=404,
                matched_mock=None,
                policy_passed=False,
                message="No Mirage mock configured for POST /v1/suppliers.",
            )
        ],
    )
    _write_trace(
        tmp_path,
        "delta",
        [
            _trace_event(
                timestamp="2026-03-27T13:00:00+00:00",
                method="GET",
                path="/v1/health",
                outcome="config_error",
                status_code=500,
                matched_mock=None,
                policy_passed=False,
                message="Mirage config error: invalid config",
            )
        ],
    )

    snapshot = collect_dashboard_metrics(tmp_path, recent_limit=3, top_limit=3)

    assert isinstance(snapshot, DashboardSnapshot)
    assert snapshot.overview.run_count == 4
    assert snapshot.overview.action_count == 5
    assert snapshot.overview.allowed_count == 1
    assert snapshot.overview.policy_violation_count == 2
    assert snapshot.overview.unmatched_route_count == 1
    assert snapshot.overview.config_error_count == 1
    assert snapshot.overview.risky_run_count == 4

    assert [run.run_id for run in snapshot.recent_runs] == ["delta", "gamma", "beta"]
    assert snapshot.recent_runs[0].last_event_at == "2026-03-27T13:00:00+00:00"
    assert snapshot.recent_runs[2].event_count == 1
    assert snapshot.recent_runs[2].policy_violation_count == 1

    assert [endpoint.path for endpoint in snapshot.top_endpoints] == [
        "/v1/submit_bid",
        "/v1/health",
        "/v1/suppliers/SUP-001",
    ]
    assert snapshot.top_endpoints[0].action_count == 2
    assert snapshot.top_endpoints[0].policy_violation_count == 2
    assert snapshot.top_endpoints[1].config_error_count == 1

    assert [policy.name for policy in snapshot.top_failing_policies] == [
        "enforce_bid_limit",
        "require_approved_supplier",
    ]
    assert snapshot.top_failing_policies[0].failure_count == 2
    assert snapshot.top_failing_policies[0].run_count == 2
    assert snapshot.top_failing_policies[1].failure_count == 1


def test_get_run_metrics_returns_detailed_run_lookup(tmp_path):
    _write_trace(
        tmp_path,
        "procurement-risky-demo",
        [
            _trace_event(
                timestamp="2026-03-27T10:00:00+00:00",
                method="GET",
                path="/v1/suppliers/SUP-001",
                outcome="allowed",
                status_code=200,
                matched_mock="get_supplier_sup_001",
            ),
            _trace_event(
                timestamp="2026-03-27T10:01:00+00:00",
                method="POST",
                path="/v1/submit_bid",
                outcome="policy_violation",
                status_code=200,
                matched_mock="submit_bid",
                policy_passed=False,
                message="Mirage policy violation: enforce_bid_limit...",
                policy_decisions=[
                    {
                        "name": "enforce_bid_limit",
                        "passed": False,
                        "message": "Agents cannot submit bids above the approved threshold.",
                        "field": "bid_amount",
                        "operator": "lte",
                        "expected": 10000,
                        "actual": 50000.0,
                    }
                ],
            ),
        ],
    )

    detail = get_run_metrics(tmp_path, "procurement-risky-demo")

    assert detail is not None
    assert detail.summary.run_id == "procurement-risky-demo"
    assert detail.summary.event_count == 2
    assert detail.summary.last_event_at == "2026-03-27T10:01:00+00:00"
    assert detail.events[0].request["method"] == "GET"
    assert detail.events[1].outcome == "policy_violation"
    assert detail.events[1].policy_decisions[0].name == "enforce_bid_limit"


def test_get_run_metrics_returns_none_for_missing_run(tmp_path):
    assert get_run_metrics(tmp_path, "missing-run") is None


def test_trace_metrics_store_handles_missing_artifacts_directory(tmp_path):
    store = TraceMetricsStore(tmp_path / "missing" / "artifacts" / "traces")

    snapshot = store.snapshot()

    assert snapshot.overview.run_count == 0
    assert snapshot.recent_runs == []
    assert snapshot.top_endpoints == []
    assert snapshot.top_failing_policies == []


def test_trace_metrics_store_skips_malformed_trace_files(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text('{"run_id": "broken", "events": [', encoding="utf-8")

    snapshot = TraceMetricsStore(tmp_path).snapshot()

    assert snapshot.overview.run_count == 0
    assert snapshot.recent_runs == []


def _gateway_event(
    *,
    outcome: str,
    decisions_passed: bool,
    time_to_decide_us: int | None = None,
    decision_latency_us: int = 0,
    timestamp: str = "2026-04-01T00:00:00+00:00",
) -> dict:
    return {
        "timestamp": timestamp,
        "run_id": "g",
        "mode": "enforce" if outcome == "blocked" else "passthrough",
        "request": {
            "method": "POST",
            "path": "/v1/submit_bid",
            "payload": {},
            "headers": {},
        },
        "outcome": outcome,
        "message": None,
        "upstream_url": "https://upstream.example.com",
        "upstream_status": None if outcome == "blocked" else 200,
        "policy_passed": decisions_passed,
        "time_to_decide_us": time_to_decide_us,
        "policy_decisions": [
            {
                "name": "enforce_bid_limit",
                "passed": decisions_passed,
                "message": "msg",
                "field": "bid_amount",
                "operator": "lte",
                "expected": 100,
                "actual": 50,
                "decision_latency_us": decision_latency_us,
            }
        ],
        "response": {"status_code": 403 if outcome == "blocked" else 200, "body": {}},
    }


def test_compute_containment_metrics_returns_blocked_share():
    events = [
        RunEventRecord(
            timestamp=None,
            request={},
            outcome="blocked",
            message=None,
            matched_mock=None,
            policy_passed=False,
            response={},
            policy_decisions=[],
        ),
        RunEventRecord(
            timestamp=None,
            request={},
            outcome="blocked",
            message=None,
            matched_mock=None,
            policy_passed=False,
            response={},
            policy_decisions=[],
        ),
        RunEventRecord(
            timestamp=None,
            request={},
            outcome="flagged",
            message=None,
            matched_mock=None,
            policy_passed=False,
            response={},
            policy_decisions=[],
        ),
        RunEventRecord(
            timestamp=None,
            request={},
            outcome="allowed",
            message=None,
            matched_mock=None,
            policy_passed=True,
            response={},
            policy_decisions=[],
        ),
    ]
    metrics = compute_containment_metrics(events, run_id="r")
    assert metrics.blocked_count == 2
    assert metrics.flagged_count == 1
    assert metrics.allowed_count == 1
    assert metrics.containment_rate == 2 / 3
    assert metrics.decision_latency_p50_us is None
    assert metrics.time_to_decide_p50_us is None


def test_compute_containment_metrics_returns_none_when_no_decisions():
    events = [
        RunEventRecord(
            timestamp=None,
            request={},
            outcome="allowed",
            message=None,
            matched_mock=None,
            policy_passed=True,
            response={},
            policy_decisions=[],
        ),
    ]
    metrics = compute_containment_metrics(events, run_id="r")
    assert metrics.containment_rate is None


def test_compute_containment_metrics_percentiles_match_known_distribution():
    decisions = [
        {
            "name": "p",
            "passed": True,
            "message": "",
            "field": "x",
            "operator": "exists",
            "expected": None,
            "actual": True,
            "decision_latency_us": value,
        }
        for value in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    ]
    events = [
        _gateway_event(
            outcome="allowed",
            decisions_passed=True,
            time_to_decide_us=t,
            decision_latency_us=d["decision_latency_us"],
        )
        for t, d in zip([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000], decisions)
    ]
    parsed = [_parse_event(e) for e in events]
    metrics = compute_containment_metrics(parsed, run_id="r")
    assert metrics.decision_latency_p50_us is not None
    assert metrics.time_to_decide_p50_us is not None
    assert 50 <= metrics.decision_latency_p50_us <= 60
    assert 90 <= metrics.decision_latency_p95_us <= 100
    assert 95 <= metrics.decision_latency_p99_us <= 100
    assert 500 <= metrics.time_to_decide_p50_us <= 600


def test_get_run_containment_returns_metrics_for_known_run(tmp_path):
    _write_trace(
        tmp_path,
        "g-run",
        [
            _gateway_event(outcome="blocked", decisions_passed=False, time_to_decide_us=80),
            _gateway_event(outcome="allowed", decisions_passed=True, time_to_decide_us=60),
        ],
    )
    metrics = get_run_containment(tmp_path, "g-run")
    assert metrics is not None
    assert isinstance(metrics, ContainmentMetrics)
    assert metrics.run_id == "g-run"
    assert metrics.blocked_count == 1
    assert metrics.allowed_count == 1
    assert metrics.containment_rate == 1.0


def test_get_run_containment_returns_none_for_missing_run(tmp_path):
    assert get_run_containment(tmp_path, "missing") is None


def test_overview_summary_exposes_fleet_containment_rate(tmp_path):
    _write_trace(
        tmp_path,
        "fleet-1",
        [
            _gateway_event(outcome="blocked", decisions_passed=False),
            _gateway_event(outcome="flagged", decisions_passed=False),
        ],
    )
    snapshot = collect_dashboard_metrics(tmp_path)
    assert snapshot.overview.containment_rate == 0.5


def test_overview_summary_returns_none_containment_when_no_decisions(tmp_path):
    _write_trace(
        tmp_path,
        "fleet-2",
        [_gateway_event(outcome="allowed", decisions_passed=True)],
    )
    snapshot = collect_dashboard_metrics(tmp_path)
    assert snapshot.overview.containment_rate is None


def _parse_event(payload: dict) -> RunEventRecord:
    store = TraceMetricsStore("/tmp")
    return store._parse_event(payload)
