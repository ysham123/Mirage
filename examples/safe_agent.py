# Safe Agent Demo - Shows an agent request that passes Mirage policy checks
import os
import time

from mirage.httpx_client import create_mirage_client, mirage_response_report

RUN_ID = os.getenv("MIRAGE_RUN_ID", "safe-agent-demo")

print("Agent booting up...")
time.sleep(1)
print("Reasoning: I should stay within approved thresholds.")
time.sleep(1)
print("Action: Submitting compliant bid to procurement API...")

safe_payload = {
    "contract_id": "STANDARD-7",
    "bid_amount": 7500.00,
}

try:
    with create_mirage_client(run_id=RUN_ID) as client:
        response = client.post("/v1/submit_bid", json=safe_payload)
        report = mirage_response_report(response)
        print(f"Mirage Outcome: {report.outcome}")
        print(f"Mirage Trace: {report.trace_path}")
        print(f"Mirage Decision: {report.decision_summary or report.message}")
        print(f"Agent Log: Success! Response: {response.json()}")
except Exception as e:
    print(f"Agent Log: Connection failed. {e}")
