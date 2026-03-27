from __future__ import annotations

from typing import Literal

from examples.procurement_harness.agent import ProcurementAgent, ProcurementWorkflowResult

ScenarioName = Literal["safe", "risky", "unmatched"]
SCENARIO_NAMES: tuple[ScenarioName, ...] = ("safe", "risky", "unmatched")


def run_scenario(agent: ProcurementAgent, scenario: ScenarioName) -> ProcurementWorkflowResult:
    if scenario == "safe":
        return agent.run_compliant_bid_workflow()
    if scenario == "risky":
        return agent.run_risky_bid_workflow()
    return agent.run_unconfigured_supplier_workflow()
