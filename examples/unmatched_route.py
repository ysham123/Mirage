# Unmatched Route Demo - Shows Mirage failing clearly when no mock is configured
import os
import time

from src.httpx_client import create_mirage_client, mirage_response_report

RUN_ID = os.getenv("MIRAGE_RUN_ID", "unmatched-route-demo")

print("Agent booting up...")
time.sleep(1)
print("Reasoning: I need to create a supplier record.")
time.sleep(1)
print("Action: Calling an API route Mirage does not know about yet...")

unmatched_payload = {
    "supplier_id": "NEW-VENDOR-22",
    "country": "US",
}

try:
    with create_mirage_client(run_id=RUN_ID) as client:
        response = client.post("/v1/create_supplier", json=unmatched_payload)
        report = mirage_response_report(response)
        print(f"Mirage Outcome: {report.outcome}")
        print(f"Mirage Trace: {report.trace_path}")
        print(f"Mirage Decision: {report.decision_summary or report.message}")
        print(f"Agent Log: Response: {response.json()}")
except Exception as e:
    print(f"Agent Log: Connection failed. {e}")
