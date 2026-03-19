# Pytest configuration and fixtures for agent safety tests
import pytest
import json
import os

LOG_FILE = "examples/audit_log.json"

@pytest.fixture

def transaction_log():
  if not os.path.exists(LOG_FILE):
    return []
  with open(LOG_FILE, "r") as f:
    return json.load(f)
    
