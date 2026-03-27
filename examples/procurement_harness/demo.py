from __future__ import annotations

import argparse
import os
import time

from examples.procurement_harness.agent import ProcurementAgent
from examples.procurement_harness.scenarios import SCENARIO_NAMES, run_scenario
from src.httpx_client import create_mirage_client


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Mirage procurement harness demo.")
    parser.add_argument(
        "scenario",
        choices=SCENARIO_NAMES,
        help="Which procurement scenario to run.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional Mirage run ID override.",
    )
    args = parser.parse_args()

    run_id = args.run_id or os.getenv("MIRAGE_RUN_ID") or f"procurement-{args.scenario}-demo"
    print("Agent booting up...")
    time.sleep(1)
    print("Workflow: Procurement approval harness")
    time.sleep(1)

    with create_mirage_client(run_id=run_id) as client:
        agent = ProcurementAgent(client)
        result = run_scenario(agent, args.scenario)

    if result.supplier_lookup is not None:
        print("Step 1: Supplier lookup")
        print(f"Mirage Outcome: {result.supplier_lookup.mirage.outcome}")
        print(f"Mirage Trace: {result.supplier_lookup.mirage.trace_path}")
        print(f"Supplier: {result.supplier_lookup.response_body}")

    print("Step 2: Agent action")
    print(f"Mirage Outcome: {result.action.mirage.outcome}")
    print(f"Mirage Trace: {result.action.mirage.trace_path}")
    print(f"Mirage Decision: {result.action.mirage.decision_summary or result.action.mirage.message}")
    print(f"Agent Log: Response: {result.action.response_body}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
