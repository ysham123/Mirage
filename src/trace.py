from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TraceStore:
    def __init__(self, artifact_root: Path):
        self.artifact_root = artifact_root
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def append_event(self, run_id: str, event: dict[str, Any]) -> Path:
        trace_path = self.trace_path(run_id)
        trace = self.read_trace(run_id)
        trace["events"].append(event)
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        return trace_path

    def read_trace(self, run_id: str) -> dict[str, Any]:
        trace_path = self.trace_path(run_id)
        if not trace_path.exists():
            return {"run_id": run_id, "events": []}
        return json.loads(trace_path.read_text(encoding="utf-8"))

    def trace_path(self, run_id: str) -> Path:
        safe_run_id = run_id.replace("/", "_")
        return self.artifact_root / f"{safe_run_id}.json"
