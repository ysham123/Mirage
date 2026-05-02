"""Tests for mirage.gateway.

Covers the runtime gateway: passthrough mode (forward + log), enforce mode
(forward when policy passes, block when it fails), config errors, upstream
errors, and the FastAPI surface (X-Mirage-* headers + outcome taxonomy).

Upstream HTTP is mocked with httpx.MockTransport so the tests never make a
real network call.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from mirage.gateway import MirageGateway, create_gateway_app
from tests.conftest import write_mirage_config


def _build_gateway(
    *,
    tmp_path: Path,
    mode: str,
    upstream_responses: dict[str, httpx.Response] | None = None,
) -> MirageGateway:
    _, policies_path = write_mirage_config(tmp_path)
    upstream_responses = upstream_responses or {
        "/v1/submit_bid": httpx.Response(
            200,
            json={"status": "success", "transaction_id": "trx_real_99"},
        ),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        match = upstream_responses.get(request.url.path)
        if match is None:
            return httpx.Response(404, json={"status": "not_found"})
        return match

    transport = httpx.MockTransport(handler)
    upstream_client = httpx.Client(
        transport=transport,
        base_url="https://upstream.example.com",
    )
    return MirageGateway(
        upstream_url="https://upstream.example.com",
        mode=mode,  # type: ignore[arg-type]
        policies_path=policies_path,
        artifact_root=tmp_path / "artifacts" / "traces",
        upstream_client=upstream_client,
    )


def test_passthrough_allowed_request_forwards_to_upstream(tmp_path):
    gateway = _build_gateway(tmp_path=tmp_path, mode="passthrough")
    result = gateway.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 5000},
        run_id="passthrough-allowed",
    )
    gateway.close()

    assert result.outcome == "allowed"
    assert result.mode == "passthrough"
    assert result.policy_passed is True
    assert result.upstream_status == 200
    assert result.body["transaction_id"] == "trx_real_99"


def test_passthrough_policy_violation_flagged_but_forwarded(tmp_path):
    gateway = _build_gateway(tmp_path=tmp_path, mode="passthrough")
    result = gateway.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 50000},
        run_id="passthrough-flagged",
    )
    gateway.close()

    assert result.outcome == "flagged"
    assert result.policy_passed is False
    assert result.upstream_status == 200
    assert result.body["transaction_id"] == "trx_real_99"
    assert any("enforce_bid_limit" in d.name for d in result.failed_decisions())


def test_enforce_policy_violation_blocks_with_403(tmp_path):
    gateway = _build_gateway(tmp_path=tmp_path, mode="enforce")
    result = gateway.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 50000},
        run_id="enforce-blocked",
    )
    gateway.close()

    assert result.outcome == "blocked"
    assert result.status_code == 403
    assert result.policy_passed is False
    assert result.upstream_status is None
    assert "enforce_bid_limit" in result.body["message"]


def test_enforce_allowed_request_still_forwards(tmp_path):
    gateway = _build_gateway(tmp_path=tmp_path, mode="enforce")
    result = gateway.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 5000},
        run_id="enforce-allowed",
    )
    gateway.close()

    assert result.outcome == "allowed"
    assert result.status_code == 200
    assert result.upstream_status == 200


def test_trace_event_carries_mode_and_unified_outcome(tmp_path):
    gateway = _build_gateway(tmp_path=tmp_path, mode="enforce")
    gateway.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 50000},
        run_id="trace-shape",
    )
    gateway.close()

    trace_path = tmp_path / "artifacts" / "traces" / "trace-shape.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    event = trace["events"][0]
    assert event["mode"] == "enforce"
    assert event["outcome"] == "blocked"
    assert event["upstream_url"] == "https://upstream.example.com"
    assert event["upstream_status"] is None


def test_trace_event_carries_decision_latency_and_time_to_decide(tmp_path):
    gateway = _build_gateway(tmp_path=tmp_path, mode="enforce")
    gateway.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 50000},
        run_id="latency-trace",
    )
    gateway.close()

    trace_path = tmp_path / "artifacts" / "traces" / "latency-trace.json"
    event = json.loads(trace_path.read_text(encoding="utf-8"))["events"][0]
    assert "time_to_decide_us" in event
    assert isinstance(event["time_to_decide_us"], int)
    assert event["time_to_decide_us"] >= 0
    decisions = event["policy_decisions"]
    assert decisions
    assert all("decision_latency_us" in decision for decision in decisions)
    assert all(decision["decision_latency_us"] >= 0 for decision in decisions)


def test_upstream_error_returns_502_outcome_error(tmp_path):
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("upstream offline")

    transport = httpx.MockTransport(boom)
    upstream_client = httpx.Client(transport=transport, base_url="https://upstream.example.com")
    _, policies_path = write_mirage_config(tmp_path)
    gateway = MirageGateway(
        upstream_url="https://upstream.example.com",
        mode="passthrough",
        policies_path=policies_path,
        artifact_root=tmp_path / "artifacts" / "traces",
        upstream_client=upstream_client,
    )
    result = gateway.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 5000},
        run_id="upstream-down",
    )
    gateway.close()

    assert result.outcome == "error"
    assert result.status_code == 502


def test_gateway_app_exposes_health_and_decision_headers(tmp_path):
    gateway = _build_gateway(tmp_path=tmp_path, mode="enforce")
    app = create_gateway_app(gateway=gateway)
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {
            "status": "ok",
            "mode": "enforce",
            "upstream": "https://upstream.example.com",
        }

        blocked = client.post(
            "/v1/submit_bid",
            json={"bid_amount": 50000},
            headers={"X-Mirage-Run-Id": "header-blocked"},
        )
        assert blocked.status_code == 403
        assert blocked.headers["X-Mirage-Mode"] == "enforce"
        assert blocked.headers["X-Mirage-Outcome"] == "blocked"
        assert blocked.headers["X-Mirage-Policy-Passed"] == "false"
        assert "enforce_bid_limit" in blocked.headers["X-Mirage-Decision-Summary"]
    gateway.close()


def test_gateway_rejects_invalid_mode():
    with pytest.raises(ValueError):
        MirageGateway(upstream_url="", mode="passthrough")


def test_load_policies_only_returns_empty_mocks(tmp_path):
    """`load_policies_only` is the helper the gateway uses to avoid the
    'load policies file as mocks file' hack. The result must always have
    an empty mocks list, even if the policies file doesn't define mocks."""
    from mirage.config import load_policies_only

    _, policies_path = write_mirage_config(tmp_path)
    config = load_policies_only(policies_path)

    assert config.mocks == []
    assert len(config.policies) == 1
    assert config.policies[0].name == "enforce_bid_limit"


def test_gateway_forwards_explicit_empty_dict_body(tmp_path):
    """A POST with an explicit empty JSON body should still forward as `{}`,
    not as 'no body.'"""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["content"] = request.content
        captured["content_type"] = request.headers.get("content-type")
        return httpx.Response(200, json={"echoed": True})

    transport = httpx.MockTransport(handler)
    upstream_client = httpx.Client(transport=transport, base_url="https://upstream.example.com")
    _, policies_path = write_mirage_config(tmp_path)
    gateway = MirageGateway(
        upstream_url="https://upstream.example.com",
        mode="passthrough",
        policies_path=policies_path,
        artifact_root=tmp_path / "artifacts" / "traces",
        upstream_client=upstream_client,
    )
    gateway.handle_request(
        method="POST",
        path="/v1/empty",
        payload={},
        run_id="empty-body",
    )
    gateway.close()

    assert captured["content"] == b"{}"


def test_gateway_app_lifespan_closes_upstream(tmp_path):
    """When the FastAPI app shuts down, the lifespan handler must close
    the upstream httpx client so uvicorn doesn't leak the connection pool."""
    from typing import Any as _Any

    closed: dict[str, bool] = {"value": False}

    class _RecordingClient(httpx.Client):
        def close(self) -> None:  # type: ignore[override]
            closed["value"] = True
            super().close()

    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    upstream_client = _RecordingClient(transport=transport, base_url="https://upstream.example.com")
    _, policies_path = write_mirage_config(tmp_path)
    gateway = MirageGateway(
        upstream_url="https://upstream.example.com",
        mode="passthrough",
        policies_path=policies_path,
        artifact_root=tmp_path / "artifacts" / "traces",
        upstream_client=upstream_client,
    )
    app = create_gateway_app(gateway=gateway)
    with TestClient(app):
        pass  # Entering and exiting the context invokes the lifespan handler.

    assert closed["value"] is True
