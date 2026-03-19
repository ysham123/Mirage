# Rogue Agent Demo - Shows an agent attempting to spend $10,000
import httpx
import time

PROXY_URL = "http://localhost:8000/v1/submit_bid"

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
    response = httpx.post(PROXY_URL, json=rogue_payload)
    if response.status_code == 200:
        print(f"Agent Log: Success! Response: {response.json()}")
except Exception as e:
    print(f"Agent Log: Connection failed. {e}")