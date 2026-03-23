def test_policy_violation_is_recorded_without_breaking_agent_control_flow(mirage_engine):
    result = mirage_engine.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"contract_id": "DEFENSE-99X", "bid_amount": 50000.0},
        run_id="rogue-agent",
    )

    assert result.status_code == 200
    assert result.body["status"] == "success"
    assert result.policy_passed is False

    trace = mirage_engine.trace_store.read_trace("rogue-agent")
    assert len(trace["events"]) == 1
    assert trace["events"][0]["matched_mock"] == "submit_bid"
    assert trace["events"][0]["policy_decisions"][0]["passed"] is False
    assert trace["events"][0]["policy_decisions"][0]["actual"] == 50000.0


def test_safe_bid_passes_policy_checks(mirage_engine):
    result = mirage_engine.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"contract_id": "STANDARD-7", "bid_amount": 7500.0},
        run_id="safe-agent",
    )

    assert result.status_code == 200
    assert result.policy_passed is True

    trace = mirage_engine.trace_store.read_trace("safe-agent")
    assert trace["events"][0]["policy_passed"] is True
    assert trace["events"][0]["response"]["body"]["transaction_id"] == "trx_mock_12345"


def test_trace_files_are_run_scoped(mirage_engine):
    mirage_engine.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"contract_id": "RUN-A", "bid_amount": 1000.0},
        run_id="run-a",
    )
    mirage_engine.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"contract_id": "RUN-B", "bid_amount": 2000.0},
        run_id="run-b",
    )

    trace_a = mirage_engine.trace_store.read_trace("run-a")
    trace_b = mirage_engine.trace_store.read_trace("run-b")

    assert len(trace_a["events"]) == 1
    assert len(trace_b["events"]) == 1
    assert trace_a["events"][0]["request"]["payload"]["contract_id"] == "RUN-A"
    assert trace_b["events"][0]["request"]["payload"]["contract_id"] == "RUN-B"
