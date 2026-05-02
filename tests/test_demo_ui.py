import json
from fastapi.testclient import TestClient

from demo_ui.server import create_demo_app


def _write_trace(root, run_id, events):
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run_id}.json"
    path.write_text(json.dumps({"run_id": run_id, "events": events}, indent=2), encoding="utf-8")
    return path


def _assert_has_keys(payload, keys):
    missing = sorted(set(keys) - set(payload.keys()))
    assert not missing, f"Missing keys: {missing}"


def _assert_run_payload_matches_ui_contract(body):
    _assert_has_keys(
        body,
        {
            "run_id",
            "meta",
            "summary",
            "risk",
            "agent_health",
            "side_effects",
            "trace",
            "trace_path",
        },
    )
    _assert_has_keys(body["meta"], {"run_id", "trace_path", "source", "event_count"})
    _assert_has_keys(
        body["summary"],
        {"headline", "final_outcome", "trace_event_count", "trace_path"},
    )
    _assert_has_keys(
        body["risk"],
        {"score", "level", "total_steps", "risky_steps", "suppressed_steps", "allowed_steps"},
    )
    _assert_has_keys(body["agent_health"], {"status", "summary", "confidence", "label"})
    assert isinstance(body["side_effects"], list)
    assert body["side_effects"]
    _assert_has_keys(
        body["side_effects"][0],
        {
            "id",
            "step_index",
            "name",
            "method",
            "path",
            "payload",
            "status_code",
            "response_body",
            "outcome",
            "severity",
            "message",
            "decision_summary",
            "decisions",
            "matched_mock",
            "policy_passed",
            "timestamp",
            "confidence",
            "suppressed",
            "suppression",
            "status",
        },
    )
    _assert_has_keys(body["trace"], {"run_id", "events"})


def test_demo_ui_root_serves_html(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/")

    html = response.text
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Mirage</title>" in html
    assert "Action Review" in html
    assert "Needs Review" in html
    assert "Policy Friction" in html
    assert "Run Graph" in html
    assert 'data-queue-filter="risky"' in html
    assert 'data-queue-filter="allowed"' in html
    assert "Compliant Bid" in html
    assert "Excessive Bid" in html
    assert "New Supplier" in html
    assert 'fetchJSON("/api/metrics/overview")' in html
    assert 'fetchJSON("/api/scenario/" + name)' in html
    assert 'params.get("run_id")' in html
    assert "Select a run from the review queue or launch a demo scenario." in html


def test_demo_ui_logo_asset_serves_svg(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/assets/mirage-logo.svg")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"


def test_demo_ui_cors_allows_configured_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("MIRAGE_ALLOWED_ORIGINS", "http://127.0.0.1:3000")

    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.options(
            "/api/metrics/overview",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_demo_ui_cors_blocks_default_localhost_regex_when_allowlist_is_set(tmp_path, monkeypatch):
    monkeypatch.setenv("MIRAGE_ALLOWED_ORIGINS", "https://console.example.com")
    monkeypatch.delenv("MIRAGE_ALLOWED_ORIGIN_REGEX", raising=False)

    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.options(
            "/api/metrics/overview",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


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


def test_demo_ui_scenario_payload_matches_ui_run_contract(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/api/scenario/safe")

    body = response.json()
    assert response.status_code == 200
    _assert_run_payload_matches_ui_contract(body)
    assert body["meta"]["source"] == "proxy-backed procurement harness"
    assert body["summary"]["final_outcome"] == "allowed"


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
    assert body["summary"]["suppressed_actions"] == 0
    assert body["top_endpoints"][0]["label"].startswith("GET ") or body["top_endpoints"][0]["label"].startswith("POST ")
    assert body["top_policy_failures"][0]["name"] == "enforce_bid_limit"
    assert body["recent_runs"][0]["run_id"] == "run-beta"
    assert body["recent_runs"][1]["outcome"] == "policy_violation"


def test_demo_ui_metrics_overview_matches_ui_contract(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    _write_trace(
        artifact_root,
        "run-overview",
        [
            {
                "timestamp": "2026-03-28T11:00:00+00:00",
                "run_id": "run-overview",
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
    _assert_has_keys(body, {"summary", "recent_runs", "top_endpoints", "top_policy_failures"})
    _assert_has_keys(
        body["summary"],
        {
            "total_runs",
            "total_actions",
            "allowed",
            "policy_violation",
            "unmatched_route",
            "config_error",
            "risky_runs",
            "suppressed_actions",
        },
    )
    assert isinstance(body["recent_runs"], list)
    assert body["recent_runs"]
    _assert_has_keys(
        body["recent_runs"][0],
        {"run_id", "outcome", "headline", "timestamp", "request", "event_count", "suppressed_count"},
    )
    _assert_has_keys(body["recent_runs"][0]["request"], {"method", "path"})
    assert isinstance(body["top_endpoints"], list)
    assert body["top_endpoints"]
    _assert_has_keys(body["top_endpoints"][0], {"label", "description", "count", "method", "path"})
    assert body["top_policy_failures"] == []


def test_demo_ui_metrics_overview_counts_risky_runs_across_full_trace_store(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    for index in range(12):
        outcome = "allowed" if index == 11 else "policy_violation"
        _write_trace(
            artifact_root,
            f"run-{index:02d}",
            [
                {
                    "timestamp": f"2026-03-28T{10 + (index // 60):02d}:{index % 60:02d}:00+00:00",
                    "run_id": f"run-{index:02d}",
                    "request": {"method": "POST", "path": "/v1/submit_bid", "payload": {"bid_amount": index + 1}},
                    "outcome": outcome,
                    "message": (
                        "Request matched a Mirage mock and passed all policy checks."
                        if outcome == "allowed"
                        else "Mirage policy violation: enforce_bid_limit..."
                    ),
                    "matched_mock": "submit_bid",
                    "policy_passed": outcome == "allowed",
                    "policy_decisions": (
                        []
                        if outcome == "allowed"
                        else [
                            {
                                "name": "enforce_bid_limit",
                                "passed": False,
                                "message": "Agents cannot submit bids above the approved threshold.",
                                "field": "bid_amount",
                                "operator": "lte",
                                "expected": 10000,
                                "actual": index + 1,
                            }
                        ]
                    ),
                    "response": {"status_code": 200, "body": {"status": "success"}},
                }
            ],
        )

    with TestClient(create_demo_app(artifact_root=artifact_root)) as client:
        response = client.get("/api/metrics/overview")

    body = response.json()
    assert response.status_code == 200
    assert body["summary"]["total_runs"] == 12
    assert body["summary"]["risky_runs"] == 11
    assert len(body["recent_runs"]) == 10


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
    assert body["risk"]["risky_steps"] == 1
    assert body["agent_health"]["status"] == "watch"
    assert body["side_effects"][1]["path"] == "/v1/submit_bid"
    assert body["side_effects"][1]["suppressed"] is False


def test_demo_ui_metrics_run_detail_matches_ui_contract(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    _write_trace(
        artifact_root,
        "run-contract",
        [
            {
                "timestamp": "2026-03-28T10:00:00+00:00",
                "run_id": "run-contract",
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
        response = client.get("/api/metrics/runs/run-contract")

    body = response.json()
    assert response.status_code == 200
    _assert_run_payload_matches_ui_contract(body)
    assert body["meta"]["source"] == "trace metrics review"


def test_demo_ui_chat_stream_replays_sse_events(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    _write_trace(
        artifact_root,
        "run-stream",
        [
            {
                "timestamp": "2026-03-28T10:00:00+00:00",
                "run_id": "run-stream",
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

    with TestClient(create_demo_app(artifact_root=artifact_root)) as client:
        response = client.get("/api/chat/stream", params={"run_id": "run-stream"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: status" in response.text
    assert "event: message_delta" in response.text
    assert "event: complete" in response.text
    assert "run-stream" in response.text


def test_demo_ui_containment_endpoint_returns_metrics_for_known_run(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    _write_trace(
        artifact_root,
        "run-containment",
        [
            {
                "timestamp": "2026-04-01T10:00:00+00:00",
                "run_id": "run-containment",
                "mode": "enforce",
                "request": {"method": "POST", "path": "/v1/submit_bid", "payload": {}},
                "outcome": "blocked",
                "message": "blocked",
                "policy_passed": False,
                "time_to_decide_us": 80,
                "policy_decisions": [
                    {
                        "name": "p",
                        "passed": False,
                        "message": "msg",
                        "field": "f",
                        "operator": "lte",
                        "expected": 1,
                        "actual": 2,
                        "decision_latency_us": 50,
                    }
                ],
                "response": {"status_code": 403, "body": {}},
            },
            {
                "timestamp": "2026-04-01T10:00:01+00:00",
                "run_id": "run-containment",
                "mode": "passthrough",
                "request": {"method": "POST", "path": "/v1/submit_bid", "payload": {}},
                "outcome": "allowed",
                "message": "ok",
                "policy_passed": True,
                "time_to_decide_us": 60,
                "policy_decisions": [
                    {
                        "name": "p",
                        "passed": True,
                        "message": "ok",
                        "field": "f",
                        "operator": "lte",
                        "expected": 1,
                        "actual": 0,
                        "decision_latency_us": 30,
                    }
                ],
                "response": {"status_code": 200, "body": {}},
            },
        ],
    )

    with TestClient(create_demo_app(artifact_root=artifact_root)) as client:
        response = client.get("/api/runs/run-containment/containment")

    body = response.json()
    assert response.status_code == 200
    assert body["run_id"] == "run-containment"
    assert body["blocked_count"] == 1
    assert body["allowed_count"] == 1
    assert body["containment_rate"] == 1.0
    assert body["decision_latency_p50_us"] is not None
    assert body["time_to_decide_p50_us"] is not None


def test_demo_ui_containment_endpoint_returns_404_for_unknown_run(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/api/runs/unknown/containment")

    assert response.status_code == 404


def test_demo_ui_overview_summary_exposes_fleet_containment_rate(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    _write_trace(
        artifact_root,
        "fleet-containment",
        [
            {
                "timestamp": "2026-04-01T10:00:00+00:00",
                "run_id": "fleet-containment",
                "mode": "enforce",
                "request": {"method": "POST", "path": "/v1/x", "payload": {}},
                "outcome": "blocked",
                "policy_passed": False,
                "policy_decisions": [],
                "response": {"status_code": 403, "body": {}},
            },
            {
                "timestamp": "2026-04-01T10:00:01+00:00",
                "run_id": "fleet-containment",
                "mode": "passthrough",
                "request": {"method": "POST", "path": "/v1/x", "payload": {}},
                "outcome": "flagged",
                "policy_passed": False,
                "policy_decisions": [],
                "response": {"status_code": 200, "body": {}},
            },
        ],
    )

    with TestClient(create_demo_app(artifact_root=artifact_root)) as client:
        response = client.get("/api/metrics/overview")

    body = response.json()
    assert response.status_code == 200
    assert body["summary"]["containment_rate"] == 0.5


def test_demo_ui_can_suppress_side_effect(tmp_path):
    artifact_root = tmp_path / "artifacts" / "traces"
    _write_trace(
        artifact_root,
        "run-suppress",
        [
            {
                "timestamp": "2026-03-28T10:00:00+00:00",
                "run_id": "run-suppress",
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

    with TestClient(create_demo_app(artifact_root=artifact_root)) as client:
        suppress_response = client.post(
            "/api/runs/run-suppress/side-effects/1/suppress",
            json={"reason": "Muted while procurement owners review the threshold."},
        )
        run_response = client.get("/api/metrics/runs/run-suppress")
        overview_response = client.get("/api/metrics/overview")

    suppress_body = suppress_response.json()
    run_body = run_response.json()
    overview_body = overview_response.json()

    assert suppress_response.status_code == 200
    assert suppress_body["side_effect"]["suppressed"] is True
    assert suppress_body["suppression"]["reason"] == "Muted while procurement owners review the threshold."
    assert run_body["side_effects"][0]["suppressed"] is True
    assert run_body["side_effects"][0]["suppression"]["reason"] == "Muted while procurement owners review the threshold."
    assert overview_body["summary"]["suppressed_actions"] == 1
