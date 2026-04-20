import os
import time

from mirage.httpx_client import create_mirage_client, mirage_response_report

RUN_ID = os.getenv("MIRAGE_RUN_ID", "rogue-agent-demo")

print("Agent booting up...")
time.sleep(1)
print("Reasoning: I need to win this contract at all costs.")
time.sleep(1)
print("Action: Submitting aggressive bid to procurement API...")

# The agent thinks it is hitting the real API
rogue_payload = {
    "contract_id": "DEFENSE-99X",
    "bid_amount": 50000.00  # CATASTROPHIC AMOUNT
}

try:
    with create_mirage_client(run_id=RUN_ID) as client:
        response = client.post("/v1/submit_bid", json=rogue_payload)
        report = mirage_response_report(response)
        print(f"Mirage Outcome: {report.outcome}")
        print(f"Mirage Trace: {report.trace_path}")
        print(f"Mirage Decision: {report.decision_summary or report.message}")
        print(f"Agent Log: Success! Response: {response.json()}")
except Exception as e:
    print(f"Agent Log: Connection failed. {e}")
