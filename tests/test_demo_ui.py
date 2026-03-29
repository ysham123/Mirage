import json
from fastapi.testclient import TestClient

from demo_ui.server import create_demo_app


def _write_trace(root, run_id, events):
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run_id}.json"
    path.write_text(json.dumps({"run_id": run_id, "events": events}, indent=2), encoding="utf-8")
    return path


def test_demo_ui_root_serves_html(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Mirage</title>" in response.text


def test_demo_ui_safe_scenario_uses_procurement_flow(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/api/scenario/safe")

    body = response.json()
    assert response.status_code == 200
    assert body["scenario"] == "safe"
    assert body["meta"]["source"] == "proxy-backed procurement harness"
    assert [step["mirage"]["outcome"] for step in body["steps"]] == ["allowed", "allowed"]
    assert body["steps"][1]["request"]["path"] == "/v1/submit_bid"
    assert any(
        decision["name"] == "enforce_bid_limit"
        for decision in body["steps"][1]["mirage"]["decisions"]
    )
    assert body["steps"][1]["trace_event"]["timestamp"] is not None
    assert body["summary"]["trace_event_count"] == 2
    assert body["trace"]


def test_demo_ui_risky_scenario_exposes_policy_decisions(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/api/scenario/risky")

    body = response.json()
    assert response.status_code == 200
    assert body["scenario"] == "risky"
    assert body["summary"]["final_outcome"] == "policy_violation"
    assert body["steps"][1]["mirage"]["outcome"] == "policy_violation"
    assert body["steps"][1]["mirage"]["decisions"]
    assert any(
        decision["field"] == "bid_amount" and decision["passed"] is False
        for decision in body["steps"][1]["mirage"]["decisions"]
    )


def test_demo_ui_metrics_overview_aggregates_trace_store(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    _write_trace(
        artifact_root,
        "run-alpha",
        [
            {
                "timestamp": "2026-03-28T10:00:00+00:00",
                "run_id": "run-alpha",
                "request": {"method": "POST", "path": "/v1/submit_bid", "payload": {"bid_amount": 50000}},
                "outcome": "policy_violation",
                "message": "Mirage policy violation: enforce_bid_limit...",
                "matched_mock": "submit_bid",
                "policy_passed": False,
                "policy_decisions": [
                    {
                        "name": "enforce_bid_limit",
                        "passed": False,
                        "message": "Agents cannot submit bids above the approved threshold.",
                        "field": "bid_amount",
                        "operator": "lte",
                        "expected": 10000,
                        "actual": 50000,
                    }
                ],
                "response": {"status_code": 200, "body": {"status": "success"}},
            }
        ],
    )
    _write_trace(
        artifact_root,
        "run-beta",
        [
            {
                "timestamp": "2026-03-28T11:00:00+00:00",
                "run_id": "run-beta",
                "request": {"method": "GET", "path": "/v1/suppliers/SUP-001", "payload": {}},
                "outcome": "allowed",
                "message": "Request matched a Mirage mock and passed all policy checks.",
                "matched_mock": "get_supplier_sup_001",
                "policy_passed": True,
                "policy_decisions": [],
                "response": {"status_code": 200, "body": {"supplier_id": "SUP-001"}},
            }
        ],
    )

    with TestClient(create_demo_app(artifact_root=artifact_root)) as client:
        response = client.get("/api/metrics/overview")

    body = response.json()
    assert response.status_code == 200
    assert body["summary"]["total_runs"] == 2
    assert body["summary"]["total_actions"] == 2
    assert body["summary"]["policy_violation"] == 1
    assert body["top_endpoints"][0]["label"].startswith("GET ") or body["top_endpoints"][0]["label"].startswith("POST ")
    assert body["top_policy_failures"][0]["name"] == "enforce_bid_limit"
    assert body["recent_runs"][0]["run_id"] == "run-beta"
    assert body["recent_runs"][1]["outcome"] == "policy_violation"


def test_demo_ui_metrics_run_drilldown_returns_trace_backed_steps(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    _write_trace(
        artifact_root,
        "run-risky",
        [
            {
                "timestamp": "2026-03-28T10:00:00+00:00",
                "run_id": "run-risky",
                "request": {"method": "GET", "path": "/v1/suppliers/SUP-001", "payload": {}},
                "outcome": "allowed",
                "message": "Request matched a Mirage mock and passed all policy checks.",
                "matched_mock": "get_supplier_sup_001",
                "policy_passed": True,
                "policy_decisions": [],
                "response": {"status_code": 200, "body": {"supplier_id": "SUP-001"}},
            },
            {
                "timestamp": "2026-03-28T10:01:00+00:00",
                "run_id": "run-risky",
                "request": {
                    "method": "POST",
                    "path": "/v1/submit_bid",
                    "payload": {"bid_amount": 50000},
                },
                "outcome": "policy_violation",
                "message": "Mirage policy violation: enforce_bid_limit...",
                "matched_mock": "submit_bid",
                "policy_passed": False,
                "policy_decisions": [
                    {
                        "name": "enforce_bid_limit",
                        "passed": False,
                        "message": "Agents cannot submit bids above the approved threshold.",
                        "field": "bid_amount",
                        "operator": "lte",
                        "expected": 10000,
                        "actual": 50000,
                    }
                ],
                "response": {"status_code": 200, "body": {"status": "success"}},
            },
        ],
    )

    with TestClient(create_demo_app(artifact_root=artifact_root)) as client:
        response = client.get("/api/metrics/runs/run-risky")

    body = response.json()
    assert response.status_code == 200
    assert body["run_id"] == "run-risky"
    assert body["summary"]["final_outcome"] == "policy_violation"
    assert body["meta"]["source"] == "trace metrics review"
    assert [step["name"] for step in body["steps"]] == ["Supplier Lookup", "Submit Bid"]
    assert body["steps"][1]["mirage"]["decisions"][0]["name"] == "enforce_bid_limit"
