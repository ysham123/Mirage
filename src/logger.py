import json
import os
from datetime import datetime

LOG_FILE = "examples/audit_log.json"

def clear_log():
    with open(LOG_FILE, "w") as f:
        json.dump([], f)

def log_action(endpoint: str, payload: dict):
    if not os.path.exists(LOG_FILE):
        clear_log()
        
    with open(LOG_FILE, "r+") as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
            
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "payload": payload
        })
        f.seek(0)
        json.dump(logs, f, indent=4)