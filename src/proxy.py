from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.engine import MirageEngine

app = FastAPI()
engine = MirageEngine()


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
    result = engine.handle_request(
        method=request.method,
        path=path,
        payload=payload,
        headers=dict(request.headers),
    )
    return JSONResponse(status_code=result.status_code, content=result.body)
