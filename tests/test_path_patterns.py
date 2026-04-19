from textwrap import dedent

import pytest

from src.engine import MirageEngine, _path_matches
from tests.conftest import write_mirage_config


def test_exact_path_still_matches():
    assert _path_matches("/v1/submit_bid", "/v1/submit_bid")
    assert not _path_matches("/v1/submit_bid", "/v1/other")


def test_single_param_matches():
    assert _path_matches("/v1/suppliers/{id}", "/v1/suppliers/SUP-001")
    assert _path_matches("/v1/suppliers/{id}", "/v1/suppliers/abc123")


def test_param_does_not_cross_slash():
    assert not _path_matches("/v1/suppliers/{id}", "/v1/suppliers/SUP-001/extra")
    assert not _path_matches("/v1/suppliers/{id}", "/v1/suppliers/")


def test_multiple_params_match():
    assert _path_matches(
        "/v1/orgs/{org}/users/{user}",
        "/v1/orgs/acme/users/42",
    )
    assert not _path_matches(
        "/v1/orgs/{org}/users/{user}",
        "/v1/orgs/acme/users/",
    )


PATTERN_MOCKS = dedent(
    """
    mocks:
      - name: get_supplier
        method: GET
        path: /v1/suppliers/{supplier_id}
        response:
          status_code: 200
          json:
            status: approved
    """
).strip()

PATTERN_POLICIES = dedent(
    """
    policies:
      - name: require_approved_flag
        method: POST
        path: /v1/suppliers/{supplier_id}/approve
        field: approved_by
        operator: exists
        message: Approval actions must include an approver.
    """
).strip()


@pytest.fixture
def pattern_engine(tmp_path):
    mocks_path, policies_path = write_mirage_config(
        tmp_path,
        mocks_text=PATTERN_MOCKS,
        policies_text=PATTERN_POLICIES,
    )
    return MirageEngine(
        mocks_path=mocks_path,
        policies_path=policies_path,
        artifact_root=tmp_path / "artifacts" / "traces",
    )


def test_engine_matches_pattern_mock(pattern_engine):
    result = pattern_engine.handle_request(
        method="GET",
        path="/v1/suppliers/SUP-001",
        run_id="patterns",
    )
    assert result.outcome == "allowed"
    assert result.mock_name == "get_supplier"
    assert result.body["status"] == "approved"


def test_engine_enforces_pattern_policy(pattern_engine):
    pattern_engine.handle_request(
        method="POST",
        path="/v1/suppliers/SUP-001/approve",
        payload={},
        run_id="missing-approver",
    )
    # Policy applies to this path; mock does not exist → unmatched_route, but
    # policy decisions should still have been evaluated and recorded.
    trace = pattern_engine.trace_store.read_trace("missing-approver")
    decisions = trace["events"][0]["policy_decisions"]
    assert len(decisions) == 1
    assert decisions[0]["name"] == "require_approved_flag"
    assert decisions[0]["passed"] is False


def test_engine_skips_policy_when_path_does_not_match(pattern_engine):
    pattern_engine.handle_request(
        method="POST",
        path="/v1/unrelated",
        payload={},
        run_id="unrelated",
    )
    trace = pattern_engine.trace_store.read_trace("unrelated")
    assert trace["events"][0]["policy_decisions"] == []
