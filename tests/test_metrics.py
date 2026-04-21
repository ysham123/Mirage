import json
from pathlib import Path

from src.metrics import (
    DashboardSnapshot,
    TraceMetricsStore,
    collect_dashboard_metrics,
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
