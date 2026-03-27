import pytest
from fastapi.testclient import TestClient

from src.engine import MirageEngine
from src.httpx_client import (
    MirageResponseError,
    assert_mirage_response_safe,
    mirage_response_report,
)
from src.proxy import create_app


def test_proxy_exposes_mirage_metadata_headers_for_safe_request(proxy_client):
    response = proxy_client.post(
        "/v1/submit_bid",
        json={"contract_id": "SAFE-1", "bid_amount": 5000},
        headers={"X-Mirage-Run-Id": "proxy-safe"},
    )

    report = mirage_response_report(response)

    assert response.status_code == 200
    assert report.safe is True
    assert report.outcome == "allowed"
    assert report.run_id == "proxy-safe"
    assert report.matched_mock == "submit_bid"


def test_proxy_exposes_policy_violation_metadata_for_httpx_helper(proxy_client):
    response = proxy_client.post(
        "/v1/submit_bid",
        json={"contract_id": "RISKY-1", "bid_amount": 50000},
        headers={"X-Mirage-Run-Id": "proxy-unsafe"},
    )

    report = mirage_response_report(response)

    assert response.status_code == 200
    assert report.safe is False
    assert report.outcome == "policy_violation"
    assert "bid_amount" in (report.decision_summary or "")

    with pytest.raises(MirageResponseError, match="policy_violation"):
        assert_mirage_response_safe(response)


def test_proxy_treats_non_json_payload_as_failure_that_keeps_control_flow(proxy_client):
    response = proxy_client.post(
        "/v1/submit_bid",
        content="plain text payload",
        headers={
            "Content-Type": "text/plain",
            "X-Mirage-Run-Id": "proxy-non-json",
        },
    )

    report = mirage_response_report(response)

    assert response.status_code == 200
    assert report.outcome == "policy_violation"
    assert report.safe is False


def test_proxy_returns_clear_config_error_for_bad_engine(tmp_path):
    app = create_app(
        MirageEngine(
            mocks_path=tmp_path / "missing-mocks.yaml",
            policies_path=tmp_path / "missing-policies.yaml",
            artifact_root=tmp_path / "artifacts" / "traces",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/submit_bid",
            json={"bid_amount": 10},
            headers={"X-Mirage-Run-Id": "proxy-config-error"},
        )

    report = mirage_response_report(response)

    assert response.status_code == 500
    assert report.outcome == "config_error"
    assert report.safe is False
    assert "config error" in (report.message or "").lower()
