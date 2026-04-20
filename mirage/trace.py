from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any


class TraceStore:
    def __init__(self, artifact_root: Path):
        self.artifact_root = artifact_root
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self._run_locks: dict[str, threading.Lock] = {}
        self._run_locks_guard = threading.Lock()

    def append_event(self, run_id: str, event: dict[str, Any]) -> Path:
        trace_path = self.trace_path(run_id)
        with self._lock_for_run(run_id):
            trace = self._read_trace(trace_path, run_id)
            trace["events"].append(event)
            self._write_trace(trace_path, trace)
        return trace_path

    def read_trace(self, run_id: str) -> dict[str, Any]:
        return self._read_trace(self.trace_path(run_id), run_id)

    def trace_path(self, run_id: str) -> Path:
        safe_run_id = run_id.replace("/", "_")
        return self.artifact_root / f"{safe_run_id}.json"

    def _lock_for_run(self, run_id: str) -> threading.Lock:
        with self._run_locks_guard:
            lock = self._run_locks.get(run_id)
            if lock is None:
                lock = threading.Lock()
                self._run_locks[run_id] = lock
            return lock

    def _read_trace(self, trace_path: Path, run_id: str) -> dict[str, Any]:
        if not trace_path.exists():
            return {"run_id": run_id, "events": []}

        raw = trace_path.read_text(encoding="utf-8").strip()
        if not raw:
            return {"run_id": run_id, "events": []}

        return json.loads(raw)

    def _write_trace(self, trace_path: Path, trace: dict[str, Any]) -> None:
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.artifact_root,
                delete=False,
            ) as handle:
                json.dump(trace, handle, indent=2)
                handle.write("\n")
                temp_path = handle.name
            os.replace(temp_path, trace_path)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
