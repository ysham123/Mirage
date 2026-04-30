"""Production gateway mode for the Mirage policy runtime.

The gateway evaluates the same `policies.yaml` that CI mode evaluates, but
against real upstreams instead of mocked responses. Two enforcement
strategies:

  - passthrough  forward every request to upstream, log policy decisions,
                 do not block. The right starting mode for a new deployment:
                 see what your policies *would* catch before turning on
                 enforcement.

  - enforce      forward when the policy passes, block with 403 when it
                 fails. The same policy file, the same decisions, now load-
                 bearing for production traffic.

The decision logic is identical to CI mode (delegates to PolicyEvaluator).
The difference is purely what happens after the decision: a mocked response
in CI, a real upstream call (or a block) here.

Trace events emitted by the gateway carry a `mode` field
(`passthrough` | `enforce`) and a unified outcome taxonomy
(`allowed` | `flagged` | `blocked` | `error`) so downstream tooling can
distinguish gateway events from legacy CI events.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Literal

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError

from .config import load_policies_only
from .policy import (
    PolicyDecision,
    PolicyEvaluator,
    build_policy_violation_message,
    summarize_decision,
)
from .runtime_paths import resolve_artifact_root, resolve_config_path
from .trace import TraceStore


GatewayMode = Literal["passthrough", "enforce"]
GatewayOutcome = Literal["allowed", "flagged", "blocked", "error"]


class GatewayResult(BaseModel):
    status_code: int
    body: Any
    outcome: GatewayOutcome
    mode: GatewayMode
    policy_passed: bool
    run_id: str
    upstream_url: str
    decisions: list[PolicyDecision] = Field(default_factory=list)
    trace_path: str
    message: str | None = None
    upstream_status: int | None = None

    def failed_decisions(self) -> list[PolicyDecision]:
        return [decision for decision in self.decisions if not decision.passed]

    def decision_summary(self) -> str | None:
        decisions = self.failed_decisions()
        if not decisions:
            return None
        return " | ".join(summarize_decision(decision) for decision in decisions)


class MirageGateway:
    """The runtime gateway. Mirrors MirageEngine's interface but forwards to
    a real upstream and emits the unified outcome taxonomy."""

    def __init__(
        self,
        *,
        upstream_url: str,
        mode: GatewayMode = "passthrough",
        policies_path: str | Path | None = None,
        artifact_root: str | Path | None = None,
        upstream_client: httpx.Client | None = None,
    ):
        if not upstream_url:
            raise ValueError("MirageGateway requires an upstream_url.")
        self.upstream_url = upstream_url.rstrip("/")
        self.mode: GatewayMode = mode
        self.policies_path = resolve_config_path(
            explicit=policies_path,
            env_var="MIRAGE_POLICIES_PATH",
            filename="policies.yaml",
        )
        self.trace_store = TraceStore(resolve_artifact_root(artifact_root))
        self._upstream = upstream_client

    @property
    def upstream(self) -> httpx.Client:
        if self._upstream is None:
            self._upstream = httpx.Client(base_url=self.upstream_url, timeout=10.0)
        return self._upstream

    def close(self) -> None:
        if self._upstream is not None:
            self._upstream.close()
            self._upstream = None

    def handle_request(
        self,
        *,
        method: str,
        path: str,
        payload: Any = None,
        headers: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> GatewayResult:
        headers = headers or {}
        body = payload if payload is not None else {}
        resolved_run_id = self._resolve_run_id(run_id, headers)

        try:
            config = load_policies_only(self.policies_path)
        except (FileNotFoundError, OSError, ValueError, ValidationError) as exc:
            return self._handle_config_error(exc, resolved_run_id, method, path, body, headers)

        decisions = PolicyEvaluator(config).evaluate(method=method, path=path, payload=body)
        policy_passed = all(decision.passed for decision in decisions)

        if not policy_passed and self.mode == "enforce":
            return self._handle_blocked(
                method=method,
                path=path,
                body=body,
                headers=headers,
                run_id=resolved_run_id,
                decisions=decisions,
            )

        try:
            upstream_response = self._forward(method=method, path=path, body=body, headers=headers)
        except httpx.HTTPError as exc:
            return self._handle_upstream_error(
                exc=exc,
                method=method,
                path=path,
                body=body,
                headers=headers,
                run_id=resolved_run_id,
                decisions=decisions,
            )

        outcome: GatewayOutcome = "allowed" if policy_passed else "flagged"
        message = (
            "Request matched policy and was forwarded to upstream."
            if policy_passed
            else "Policy violation flagged in passthrough mode (request still forwarded)."
        )

        trace_path = self._write_trace(
            run_id=resolved_run_id,
            method=method,
            path=path,
            body=body,
            headers=headers,
            decisions=decisions,
            policy_passed=policy_passed,
            response_status=upstream_response.status_code,
            response_body=_safe_json(upstream_response),
            outcome=outcome,
            message=message,
            upstream_status=upstream_response.status_code,
        )

        return GatewayResult(
            status_code=upstream_response.status_code,
            body=_safe_json(upstream_response),
            outcome=outcome,
            mode=self.mode,
            policy_passed=policy_passed,
            run_id=resolved_run_id,
            upstream_url=self.upstream_url,
            decisions=decisions,
            trace_path=str(trace_path),
            message=message,
            upstream_status=upstream_response.status_code,
        )

    def _forward(
        self,
        *,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, Any],
    ) -> httpx.Response:
        forward_headers = {
            key: value
            for key, value in headers.items()
            if not _is_hop_by_hop(key) and not key.lower().startswith("x-mirage-")
        }
        return self.upstream.request(
            method.upper(),
            path,
            # Forward `{}`, `[]`, `0`, and `False` literally — only None means
            # "no body." Anything else is a payload the agent meant to send.
            json=body if body is not None else None,
            headers=forward_headers,
        )

    def _handle_blocked(
        self,
        *,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, Any],
        run_id: str,
        decisions: list[PolicyDecision],
    ) -> GatewayResult:
        message = build_policy_violation_message(decisions)
        response_body = {
            "status": "blocked",
            "message": message,
            "policy_decisions": [decision.model_dump() for decision in decisions if not decision.passed],
        }
        trace_path = self._write_trace(
            run_id=run_id,
            method=method,
            path=path,
            body=body,
            headers=headers,
            decisions=decisions,
            policy_passed=False,
            response_status=403,
            response_body=response_body,
            outcome="blocked",
            message=message,
            upstream_status=None,
        )
        return GatewayResult(
            status_code=403,
            body=response_body,
            outcome="blocked",
            mode=self.mode,
            policy_passed=False,
            run_id=run_id,
            upstream_url=self.upstream_url,
            decisions=decisions,
            trace_path=str(trace_path),
            message=message,
            upstream_status=None,
        )

    def _handle_config_error(
        self,
        exc: Exception,
        run_id: str,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, Any],
    ) -> GatewayResult:
        message = f"Mirage gateway config error: {exc}"
        response_body = {"status": "error", "message": message}
        trace_path = self._write_trace(
            run_id=run_id,
            method=method,
            path=path,
            body=body,
            headers=headers,
            decisions=[],
            policy_passed=False,
            response_status=500,
            response_body=response_body,
            outcome="error",
            message=message,
            upstream_status=None,
        )
        return GatewayResult(
            status_code=500,
            body=response_body,
            outcome="error",
            mode=self.mode,
            policy_passed=False,
            run_id=run_id,
            upstream_url=self.upstream_url,
            decisions=[],
            trace_path=str(trace_path),
            message=message,
            upstream_status=None,
        )

    def _handle_upstream_error(
        self,
        *,
        exc: httpx.HTTPError,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, Any],
        run_id: str,
        decisions: list[PolicyDecision],
    ) -> GatewayResult:
        message = f"Upstream request failed: {exc}"
        response_body = {"status": "error", "message": message}
        trace_path = self._write_trace(
            run_id=run_id,
            method=method,
            path=path,
            body=body,
            headers=headers,
            decisions=decisions,
            policy_passed=all(decision.passed for decision in decisions),
            response_status=502,
            response_body=response_body,
            outcome="error",
            message=message,
            upstream_status=None,
        )
        return GatewayResult(
            status_code=502,
            body=response_body,
            outcome="error",
            mode=self.mode,
            policy_passed=all(decision.passed for decision in decisions),
            run_id=run_id,
            upstream_url=self.upstream_url,
            decisions=decisions,
            trace_path=str(trace_path),
            message=message,
            upstream_status=None,
        )

    def _resolve_run_id(self, run_id: str | None, headers: dict[str, Any]) -> str:
        if run_id:
            return run_id
        header_run_id = headers.get("x-mirage-run-id") or headers.get("X-Mirage-Run-Id")
        if header_run_id:
            return str(header_run_id)
        return os.getenv("MIRAGE_RUN_ID", "default")

    def _write_trace(
        self,
        *,
        run_id: str,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, Any],
        decisions: list[PolicyDecision],
        policy_passed: bool,
        response_status: int,
        response_body: Any,
        outcome: GatewayOutcome,
        message: str | None,
        upstream_status: int | None,
    ) -> Path:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "mode": self.mode,
            "request": {
                "method": method.upper(),
                "path": path,
                "payload": body,
                "headers": dict(headers),
            },
            "outcome": outcome,
            "message": message,
            "upstream_url": self.upstream_url,
            "upstream_status": upstream_status,
            "policy_passed": policy_passed,
            "policy_decisions": [decision.model_dump() for decision in decisions],
            "response": {
                "status_code": response_status,
                "body": response_body,
            },
        }
        return self.trace_store.append_event(run_id, event)


def create_gateway_app(gateway: MirageGateway | None = None) -> FastAPI:
    """Build a FastAPI app for the gateway. Mirrors create_app() in proxy.py
    so deployment shape is symmetric: the legacy CI-mode proxy and the new
    runtime gateway are both `uvicorn module:app` style.

    The lifespan handler closes the upstream httpx client on shutdown, so
    `uvicorn`'s graceful-shutdown signal does not leak the connection pool.
    """

    upstream_url = os.getenv("MIRAGE_UPSTREAM_URL")
    if gateway is None:
        if not upstream_url:
            raise RuntimeError(
                "MIRAGE_UPSTREAM_URL must be set when create_gateway_app() is called "
                "without an explicit gateway instance."
            )
        mode = os.getenv("MIRAGE_GATEWAY_MODE", "passthrough")
        if mode not in {"passthrough", "enforce"}:
            raise RuntimeError(
                f"MIRAGE_GATEWAY_MODE must be 'passthrough' or 'enforce', got {mode!r}."
            )
        gateway = MirageGateway(upstream_url=upstream_url, mode=mode)  # type: ignore[arg-type]

    bound_gateway = gateway

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            bound_gateway.close()

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    async def healthcheck() -> dict[str, str]:
        return {
            "status": "ok",
            "mode": bound_gateway.mode,
            "upstream": bound_gateway.upstream_url,
        }

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    async def handle_request(full_path: str, request: Request) -> Response:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        path = f"/{full_path}" if full_path else "/"
        result = bound_gateway.handle_request(
            method=request.method,
            path=path,
            payload=payload,
            headers=dict(request.headers),
        )
        return JSONResponse(
            status_code=result.status_code,
            content=result.body,
            headers=_gateway_headers(result),
        )

    return app


def _gateway_headers(result: GatewayResult) -> dict[str, str]:
    headers = {
        "X-Mirage-Run-Id": result.run_id,
        "X-Mirage-Mode": result.mode,
        "X-Mirage-Outcome": result.outcome,
        "X-Mirage-Policy-Passed": str(result.policy_passed).lower(),
        "X-Mirage-Trace-Path": result.trace_path,
        "X-Mirage-Upstream-Url": result.upstream_url,
        "X-Mirage-Decision-Count": str(len(result.decisions)),
        "X-Mirage-Failed-Decision-Count": str(len(result.failed_decisions())),
    }
    if result.message:
        headers["X-Mirage-Message"] = _single_line(result.message)
    summary = result.decision_summary()
    if summary:
        headers["X-Mirage-Decision-Summary"] = _single_line(summary)
    return headers


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text}


_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)


def _is_hop_by_hop(header: str) -> bool:
    return header.lower() in _HOP_BY_HOP


def _single_line(text: str) -> str:
    return text.splitlines()[0] if "\n" in text else text


__all__ = [
    "GatewayMode",
    "GatewayOutcome",
    "GatewayResult",
    "MirageGateway",
    "create_gateway_app",
]
