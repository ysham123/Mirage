from examples.procurement_harness.agent import ProcurementAgent


def test_procurement_harness_safe_workflow(procurement_harness_client):
    agent = ProcurementAgent(procurement_harness_client)

    result = agent.run_compliant_bid_workflow()

    assert result.supplier_lookup is not None
    assert result.supplier_lookup.mirage.outcome == "allowed"
    assert result.supplier_lookup.response_body["supplier_id"] == "SUP-001"
    assert result.action.mirage.outcome == "allowed"
    assert result.action.mirage.safe is True
    assert result.action.response_body["status"] == "success"


def test_procurement_harness_risky_workflow_keeps_control_flow(procurement_harness_client):
    agent = ProcurementAgent(procurement_harness_client)

    result = agent.run_risky_bid_workflow()

    assert result.supplier_lookup is not None
    assert result.supplier_lookup.mirage.outcome == "allowed"
    assert result.action.mirage.outcome == "policy_violation"
    assert result.action.mirage.safe is False
    assert "bid_amount" in (result.action.mirage.decision_summary or "")
    assert result.action.response_body["status"] == "success"


def test_procurement_harness_unconfigured_route_is_clear_failure(procurement_harness_client):
    agent = ProcurementAgent(procurement_harness_client)

    result = agent.run_unconfigured_supplier_workflow()

    assert result.supplier_lookup is None
    assert result.action.mirage.outcome == "unmatched_route"
    assert result.action.mirage.safe is False
    assert result.action.response_body["status"] == "error"
    assert "No Mirage mock configured" in (result.action.mirage.message or "")
