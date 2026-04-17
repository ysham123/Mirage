import json

import httpx
import pytest

from src.cli import main
from src.httpx_client import (
    MirageRunError,
    MirageSession,
    assert_mirage_run_clean,
    create_mirage_client,
    mirage_run_summary,
)


def test_create_mirage_client_uses_environment_defaults(monkeypatch):
    monkeypatch.setenv("MIRAGE_PROXY_URL", "http://mirage.local")
    monkeypatch.setenv("MIRAGE_RUN_ID", "env-run")

    with create_mirage_client() as client:
        assert str(client.base_url) == "http://mirage.local"
        assert client.headers["X-Mirage-Run-Id"] == "env-run"


def test_create_mirage_client_preserves_explicit_header(monkeypatch):
    monkeypatch.setenv("MIRAGE_RUN_ID", "env-run")

    with create_mirage_client(headers={"X-Mirage-Run-Id": "explicit-run"}) as client:
        assert client.headers["X-Mirage-Run-Id"] == "explicit-run"


def test_mirage_run_summary_reports_missing_run(tmp_path):
    summary = mirage_run_summary("missing-run", artifact_root=tmp_path)

    assert summary.found is False
    assert summary.safe is False
    assert summary.total_actions == 0
    assert "has no trace" in summary.to_text()


def test_mirage_run_summary_collects_risky_actions(tmp_path):
    _write_trace(
        tmp_path,
        "risky-run",
        [
            {
                "run_id": "risky-run",
                "request": {"method": "GET", "path": "/v1/suppliers/SUP-001"},
                "outcome": "allowed",
                "policy_passed": True,
                "matched_mock": "get_supplier_sup_001",
                "policy_decisions": [],
            },
            {
                "run_id": "risky-run",
                "request": {
                    "method": "POST",
                    "path": "/v1/submit_bid",
                    "payload": {"bid_amount": 50000},
                },
                "outcome": "policy_violation",
                "policy_passed": False,
                "matched_mock": "submit_bid",
                "message": "Mirage policy violation: enforce_bid_limit...",
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
            },
        ],
    )

    summary = mirage_run_summary("risky-run", artifact_root=tmp_path)

    assert summary.found is True
    assert summary.total_actions == 2
    assert summary.safe_actions == 1
    assert summary.risky_actions == 1
    assert summary.safe is False
    assert summary.issues[0].path == "/v1/submit_bid"
    assert "enforce_bid_limit" in summary.to_text()


def test_assert_mirage_run_clean_raises_for_risky_run(tmp_path):
    _write_trace(
        tmp_path,
        "risky-run",
        [
            {
                "run_id": "risky-run",
                "request": {"method": "POST", "path": "/v1/submit_bid"},
                "outcome": "policy_violation",
                "policy_passed": False,
                "matched_mock": "submit_bid",
                "message": "Mirage policy violation: enforce_bid_limit...",
                "policy_decisions": [],
            }
        ],
    )

    with pytest.raises(MirageRunError):
        assert_mirage_run_clean("risky-run", artifact_root=tmp_path)


def test_mirage_session_tracks_reports_and_summaries(tmp_path):
    _write_trace(
        tmp_path,
        "session-run",
        [
            {
                "run_id": "session-run",
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
                "X-Mirage-Run-Id": "session-run",
                "X-Mirage-Outcome": "allowed",
                "X-Mirage-Policy-Passed": "true",
                "X-Mirage-Trace-Path": str(tmp_path / "session-run.json"),
                "X-Mirage-Matched-Mock": "submit_bid",
                "X-Mirage-Message": "Request matched a Mirage mock and passed all policy checks.",
            },
        )

    with MirageSession(
        run_id="session-run",
        artifact_root=tmp_path,
        transport=httpx.MockTransport(handler),
    ) as mirage:
        response = mirage.post("/v1/submit_bid", json={"bid_amount": 7500})
        summary = mirage.assert_clean()

    assert response.status_code == 200
    assert len(mirage.reports) == 1
    assert mirage.reports[0].safe is True
    assert summary.safe is True
    assert summary.total_actions == 1


def test_cli_summarize_and_gate_run(tmp_path, capsys):
    _write_trace(
        tmp_path,
        "clean-run",
        [
            {
                "run_id": "clean-run",
                "request": {"method": "GET", "path": "/v1/suppliers/SUP-001"},
                "outcome": "allowed",
                "policy_passed": True,
                "matched_mock": "get_supplier_sup_001",
                "policy_decisions": [],
            }
        ],
    )

    summarize_exit = main(
        ["summarize-run", "--run-id", "clean-run", "--artifact-root", str(tmp_path)]
    )
    summarize_output = capsys.readouterr().out

    gate_exit = main(["gate-run", "--run-id", "clean-run", "--artifact-root", str(tmp_path)])
    gate_output = capsys.readouterr().out

    assert summarize_exit == 0
    assert gate_exit == 0
    assert "Mirage run: clean-run" in summarize_output
    assert "Result: clean run" in gate_output


def _write_trace(root, run_id, events):
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run_id}.json"
    path.write_text(json.dumps({"run_id": run_id, "events": events}, indent=2), encoding="utf-8")
    return path
