from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.engine import MirageEngine, MirageResult


def create_app(engine: MirageEngine | None = None) -> FastAPI:
    app = FastAPI()
    mirage_engine = engine or MirageEngine()

    @app.get("/health")
    async def healthcheck():
        return {"status": "ok"}

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    async def handle_request(full_path: str, request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        path = f"/{full_path}" if full_path else "/"
        result = mirage_engine.handle_request(
            method=request.method,
            path=path,
            payload=payload,
            headers=dict(request.headers),
        )
        return JSONResponse(
            status_code=result.status_code,
            content=result.body,
            headers=_mirage_headers(result),
        )

    return app


def _mirage_headers(result: MirageResult) -> dict[str, str]:
    headers = {
        "X-Mirage-Run-Id": result.run_id,
        "X-Mirage-Outcome": result.outcome,
        "X-Mirage-Policy-Passed": str(result.policy_passed).lower(),
        "X-Mirage-Trace-Path": result.trace_path,
        "X-Mirage-Decision-Count": str(len(result.decisions)),
        "X-Mirage-Failed-Decision-Count": str(len(result.failed_decisions())),
    }
    if result.mock_name:
        headers["X-Mirage-Matched-Mock"] = result.mock_name
    if result.message:
        headers["X-Mirage-Message"] = result.message
    decision_summary = result.decision_summary()
    if decision_summary:
        headers["X-Mirage-Decision-Summary"] = decision_summary
    return headers


app = create_app()
