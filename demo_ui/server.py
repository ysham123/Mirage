"""Mirage Demo UI server for founder demos."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse, JSONResponse

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
        trace_path = result.action.mirage.trace_path or str(app.state.engine.trace_store.trace_path(run_id))

        return {
            "scenario": name,
            "run_id": run_id,
            "steps": _scenario_steps(name, result),
            "trace": app.state.engine.trace_store.read_trace(run_id),
            "trace_path": trace_path,
        }

    return app


def _scenario_steps(name: ScenarioName, result: ProcurementWorkflowResult) -> list[dict]:
    steps: list[dict] = []
    if result.supplier_lookup is not None:
        steps.append(
            _step(
                "Supplier Lookup",
                "GET",
                "/v1/suppliers/SUP-001",
                None,
                result.supplier_lookup,
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
            )
        )
    return steps


def _step(name: str, method: str, path: str, payload: dict | None, result: ProcurementCallResult) -> dict:
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
        },
        "response": {"status_code": result.status_code, "body": result.response_body},
    }


app = create_demo_app()


if __name__ == "__main__":
    uvicorn.run(
        "demo_ui.server:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5100")),
        reload=True,
    )
