import json
from types import SimpleNamespace

import httpx
import pytest

from mirage import pytest_plugin


def test_mirage_session_fixture_uses_nodeid_default_and_asserts_clean(tmp_path):
    run_id = "tests-test_plugin.py-test_clean"
    _write_trace(
        tmp_path,
        run_id,
        [
            {
                "run_id": run_id,
                "request": {"method": "POST", "path": "/v1/submit_bid"},
                "outcome": "allowed",
                "policy_passed": True,
                "matched_mock": "submit_bid",
                "message": "Request matched a Mirage mock and passed all policy checks.",
                "policy_decisions": [],
            }
        ],
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "success"},
            headers={
                "X-Mirage-Run-Id": run_id,
                "X-Mirage-Outcome": "allowed",
                "X-Mirage-Policy-Passed": "true",
                "X-Mirage-Trace-Path": str(tmp_path / f"{run_id}.json"),
            },
        )

    request = SimpleNamespace(node=SimpleNamespace(nodeid="tests/test_plugin.py::test_clean"))
    fixture_fn = pytest_plugin.mirage_session.__wrapped__
    generator = fixture_fn(
        request,
        {
            "artifact_root": tmp_path,
            "transport": httpx.MockTransport(handler),
        },
    )
    session = next(generator)
    response = session.post("/v1/submit_bid", json={"bid_amount": 7500})

    assert session.run_id == run_id
    assert response.status_code == 200

    with pytest.raises(StopIteration):
        next(generator)


def test_mirage_session_fixture_can_disable_teardown_assert_and_override_run_id(tmp_path):
    run_id = "custom-run"

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "success"},
            headers={
                "X-Mirage-Run-Id": run_id,
                "X-Mirage-Outcome": "policy_violation",
                "X-Mirage-Policy-Passed": "false",
                "X-Mirage-Trace-Path": str(tmp_path / f"{run_id}.json"),
                "X-Mirage-Decision-Summary": "enforce_bid_limit: bid too high",
            },
        )

    request = SimpleNamespace(node=SimpleNamespace(nodeid="tests/test_plugin.py::test_risky"))
    fixture_fn = pytest_plugin.mirage_session.__wrapped__
    generator = fixture_fn(
        request,
        {
            "run_id": run_id,
            "artifact_root": tmp_path,
            "transport": httpx.MockTransport(handler),
            "auto_assert": False,
        },
    )
    session = next(generator)
    response = session.post("/v1/submit_bid", json={"bid_amount": 50000})

    assert session.run_id == run_id
    assert response.status_code == 200

    with pytest.raises(StopIteration):
        next(generator)


def test_mirage_session_fixture_rejects_invalid_options_shape():
    request = SimpleNamespace(node=SimpleNamespace(nodeid="tests/test_plugin.py::test_invalid"))
    fixture_fn = pytest_plugin.mirage_session.__wrapped__
    generator = fixture_fn(request, ["not", "a", "mapping"])

    with pytest.raises(TypeError, match="mapping"):
        next(generator)


def test_mirage_session_fixture_rejects_invalid_auto_assert_type():
    request = SimpleNamespace(node=SimpleNamespace(nodeid="tests/test_plugin.py::test_invalid"))
    fixture_fn = pytest_plugin.mirage_session.__wrapped__
    generator = fixture_fn(request, {"auto_assert": "false"})

    with pytest.raises(TypeError, match="auto_assert"):
        next(generator)


def _write_trace(root, run_id, events):
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run_id}.json"
    path.write_text(json.dumps({"run_id": run_id, "events": events}, indent=2), encoding="utf-8")
    return path
