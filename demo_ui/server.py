"""Mirage Demo UI server for founder demos."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse, JSONResponse

from src.metrics import build_metrics_overview, build_run_metrics
from examples.procurement_harness.agent import (
    ProcurementAgent,
    ProcurementCallResult,
    ProcurementWorkflowResult,
)
from examples.procurement_harness.scenarios import SCENARIO_NAMES, ScenarioName, run_scenario
from src.engine import MirageEngine
from src.proxy import create_app

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "examples" / "procurement_harness"


class _RunScopedClient:
    def __init__(self, client: TestClient, run_id: str):
        self._client = client
        self._headers = {"X-Mirage-Run-Id": run_id}

    def get(self, url: str, **kwargs):
        headers = {**self._headers, **dict(kwargs.pop("headers", {}) or {})}
        return self._client.get(url, headers=headers, **kwargs)

    def post(self, url: str, **kwargs):
        headers = {**self._headers, **dict(kwargs.pop("headers", {}) or {})}
        return self._client.post(url, headers=headers, **kwargs)


def create_demo_app(*, artifact_root: str | Path | None = None) -> FastAPI:
    engine = MirageEngine(
        mocks_path=HARNESS / "mocks.yaml",
        policies_path=HARNESS / "policies.yaml",
        artifact_root=artifact_root,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        proxy_client = TestClient(create_app(engine))
        app.state.proxy_client = proxy_client
        app.state.engine = engine
        try:
            yield
        finally:
            proxy_client.close()

    app = FastAPI(title="Mirage Demo", lifespan=lifespan)

    @app.get("/")
    async def serve_ui():
        return FileResponse(Path(__file__).parent / "index.html", media_type="text/html")

    @app.get("/api/scenario/{name}")
    async def run_demo_scenario(name: str):
        if name not in SCENARIO_NAMES:
            return JSONResponse(status_code=400, content={"error": f"Unknown scenario: {name}"})

        run_id = f"demo-{name}-{uuid.uuid4().hex[:8]}"
        agent = ProcurementAgent(_RunScopedClient(app.state.proxy_client, run_id))
        result = run_scenario(agent, name)
        trace = app.state.engine.trace_store.read_trace(run_id)
        trace_path = result.action.mirage.trace_path or str(app.state.engine.trace_store.trace_path(run_id))
        payload = _run_detail_payload(
            run_id=run_id,
            trace=trace,
            trace_path=trace_path,
            source="proxy-backed procurement harness",
            headline=_headline_for_scenario(name),
            final_outcome=result.action.mirage.outcome,
            steps=_scenario_steps(name, result, trace.get("events", [])),
        )
        payload["scenario"] = name
        return payload

    @app.get("/api/metrics/overview")
    async def metrics_overview():
        overview = build_metrics_overview(app.state.engine.trace_store.artifact_root)
        recent_runs: list[dict[str, Any]] = []
        for run in overview.get("recent_runs", []):
            run_metrics = build_run_metrics(app.state.engine.trace_store.artifact_root, run["run_id"])
            last_request = _last_request_from_trace(run_metrics["trace"]) if run_metrics else {}
            recent_runs.append(
                {
                    **run,
                    "outcome": run_metrics["final_outcome"] if run_metrics else "unknown",
                    "headline": run_metrics["headline"] if run_metrics else "Mirage run review.",
                    "timestamp": run.get("last_event_at"),
                    "request": last_request,
                }
            )

        return {
            "summary": {
                "total_runs": overview["overview"]["run_count"],
                "total_actions": overview["overview"]["action_count"],
                "allowed": overview["overview"]["allowed_count"],
                "policy_violation": overview["overview"]["policy_violation_count"],
                "unmatched_route": overview["overview"]["unmatched_route_count"],
                "config_error": overview["overview"]["config_error_count"],
            },
            "recent_runs": recent_runs,
            "top_endpoints": [
                {
                    **endpoint,
                    "count": endpoint["action_count"],
                    "label": f"{endpoint['method']} {endpoint['path']}",
                    "description": f"{endpoint['run_count']} runs",
                }
                for endpoint in overview.get("top_endpoints", [])
            ],
            "top_policy_failures": [
                {
                    **policy,
                    "count": policy["failure_count"],
                    "description": policy.get("message") or policy.get("field") or "",
                }
                for policy in overview.get("top_failing_policies", [])
            ],
        }

    @app.get("/api/metrics/runs/{run_id}")
    async def metrics_run_detail(run_id: str):
        run_metrics = build_run_metrics(app.state.engine.trace_store.artifact_root, run_id)
        if run_metrics is None:
            return JSONResponse(status_code=404, content={"error": f"Unknown run: {run_id}"})
        return _run_detail_payload(
            run_id=run_metrics["run_id"],
            trace=run_metrics["trace"],
            trace_path=run_metrics["trace_path"],
            source="trace metrics review",
            headline=run_metrics["headline"],
            final_outcome=run_metrics["final_outcome"],
            steps=_trace_events_to_steps(run_metrics["trace"].get("events", [])),
        )

    return app


def _scenario_steps(
    name: ScenarioName,
    result: ProcurementWorkflowResult,
    trace_events: list[dict[str, Any]],
) -> list[dict]:
    steps: list[dict] = []
    if result.supplier_lookup is not None:
        steps.append(
            _step(
                "Supplier Lookup",
                "GET",
                "/v1/suppliers/SUP-001",
                None,
                result.supplier_lookup,
                trace_events[0] if len(trace_events) > 0 else None,
            )
        )

    if name in ("safe", "risky"):
        supplier = result.supplier_lookup.response_body if result.supplier_lookup is not None else {}
        bid_amount = 7500.0 if name == "safe" else 50000.0
        steps.append(
            _step(
                "Submit Bid",
                "POST",
                "/v1/submit_bid",
                {
                    "contract_id": "RFP-ALPHA" if name == "safe" else "RFP-BLACKSWAN",
                    "supplier_id": supplier.get("supplier_id"),
                    "supplier": supplier,
                    "bid_amount": bid_amount,
                },
                result.action,
                trace_events[1] if len(trace_events) > 1 else None,
            )
        )
    else:
        steps.append(
            _step(
                "Create Supplier",
                "POST",
                "/v1/suppliers",
                {"supplier_id": "SUP-NEW-22", "country": "US"},
                result.action,
                trace_events[0] if len(trace_events) > 0 else None,
            )
        )
    return steps


def _step(
    name: str,
    method: str,
    path: str,
    payload: dict | None,
    result: ProcurementCallResult,
    trace_event: dict[str, Any] | None,
) -> dict:
    trace_event = trace_event or {}
    return {
        "name": name,
        "request": {"method": method, "path": path, "payload": payload},
        "mirage": {
            "run_id": result.mirage.run_id,
            "outcome": result.mirage.outcome,
            "policy_passed": result.mirage.policy_passed,
            "matched_mock": result.mirage.matched_mock,
            "message": result.mirage.message,
            "decision_summary": result.mirage.decision_summary,
            "decisions": trace_event.get("policy_decisions", []),
        },
        "response": {
            "status_code": trace_event.get("response", {}).get("status_code", result.status_code),
            "body": result.response_body,
        },
        "trace_event": {
            "timestamp": trace_event.get("timestamp"),
            "trace_path": result.mirage.trace_path,
        },
    }


def _trace_events_to_steps(trace_events: list[dict[str, Any]]) -> list[dict]:
    steps: list[dict] = []
    for index, trace_event in enumerate(trace_events, start=1):
        request = trace_event.get("request", {})
        response = trace_event.get("response", {})
        steps.append(
            {
                "name": _step_name_from_trace(index, request),
                "request": {
                    "method": request.get("method", "GET"),
                    "path": request.get("path", "/"),
                    "payload": request.get("payload") or None,
                },
                "mirage": {
                    "run_id": trace_event.get("run_id"),
                    "outcome": trace_event.get("outcome", "allowed"),
                    "policy_passed": trace_event.get("policy_passed", True),
                    "matched_mock": trace_event.get("matched_mock"),
                    "message": trace_event.get("message"),
                    "decision_summary": _decision_summary_from_trace(trace_event),
                    "decisions": trace_event.get("policy_decisions", []),
                },
                "response": {
                    "status_code": response.get("status_code", 200),
                    "body": response.get("body", {}),
                },
                "trace_event": {
                    "timestamp": trace_event.get("timestamp"),
                    "trace_path": None,
                },
            }
        )
    return steps


def _run_detail_payload(
    *,
    run_id: str,
    trace: dict[str, Any],
    trace_path: str,
    source: str,
    headline: str,
    final_outcome: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    event_count = len(trace.get("events", []))
    return {
        "run_id": run_id,
        "meta": {
            "run_id": run_id,
            "trace_path": trace_path,
            "source": source,
            "event_count": event_count,
        },
        "summary": {
            "headline": headline,
            "final_outcome": final_outcome,
            "trace_event_count": event_count,
            "trace_path": trace_path,
        },
        "steps": steps,
        "trace": trace,
        "trace_path": trace_path,
    }


def _headline_for_scenario(name: ScenarioName) -> str:
    if name == "safe":
        return "Compliant bid stays green."
    if name == "risky":
        return "Risky bid gets flagged while the workflow keeps moving."
    return "Unconfigured route fails clearly instead of leaking a side effect."


def _step_name_from_trace(index: int, request: dict[str, Any]) -> str:
    path = request.get("path", "/")
    method = str(request.get("method", "GET")).upper()
    if method == "GET" and path.startswith("/v1/suppliers/"):
        return "Supplier Lookup"
    if method == "POST" and path == "/v1/submit_bid":
        return "Submit Bid"
    if method == "POST" and path == "/v1/suppliers":
        return "Create Supplier"
    return f"Action {index}"


def _decision_summary_from_trace(trace_event: dict[str, Any]) -> str | None:
    failed = [decision for decision in trace_event.get("policy_decisions", []) if not decision.get("passed")]
    if not failed:
        return trace_event.get("message")
    return " | ".join(f"{decision['name']}: {decision['message']}" for decision in failed)


def _last_request_from_trace(trace: dict[str, Any]) -> dict[str, Any]:
    events = trace.get("events", [])
    if not events:
        return {}
    request = events[-1].get("request")
    if not isinstance(request, dict):
        return {}
    return request


app = create_demo_app()


if __name__ == "__main__":
    uvicorn.run(
        "demo_ui.server:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5100")),
        reload=True,
    )
