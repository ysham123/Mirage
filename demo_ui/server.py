"""Mirage console API plus the zero-dependency legacy review shell.

`demo_ui/` is the shared backend for both:

- the single-file HTML review shell served at `/`
- the richer Next.js operator client under `ui/`
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator
import uuid

import uvicorn
from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.testclient import TestClient

from examples.procurement_harness.agent import (
    ProcurementAgent,
    ProcurementCallResult,
    ProcurementWorkflowResult,
)
from examples.procurement_harness.scenarios import SCENARIO_NAMES, ScenarioName, run_scenario
from mirage.engine import MirageEngine
from mirage.metrics import build_metrics_overview, build_run_metrics, get_run_containment
from mirage.proxy import create_app

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
        app.state.side_effect_suppressions = {}
        try:
            yield
        finally:
            proxy_client.close()

    app = FastAPI(title="Mirage Console API", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, **_cors_middleware_kwargs())

    @app.get("/")
    async def serve_ui():
        return FileResponse(Path(__file__).parent / "index.html", media_type="text/html")

    @app.get("/assets/mirage-logo.svg")
    async def serve_logo():
        return FileResponse(Path(__file__).parent / "assets" / "mirage-logo.svg", media_type="image/svg+xml")

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
            suppressions={},
        )
        payload["scenario"] = name
        return payload

    @app.get("/api/metrics/overview")
    async def metrics_overview():
        overview = build_metrics_overview(app.state.engine.trace_store.artifact_root)
        recent_runs: list[dict[str, Any]] = []
        suppressions = _suppression_store(app)
        for run in overview.get("recent_runs", []):
            run_metrics = build_run_metrics(app.state.engine.trace_store.artifact_root, run["run_id"])
            last_request = _last_request_from_trace(run_metrics["trace"]) if run_metrics else {}
            suppression_count = len(suppressions.get(run["run_id"], {}))
            recent_runs.append(
                {
                    **run,
                    "outcome": run_metrics["final_outcome"] if run_metrics else "unknown",
                    "headline": run_metrics["headline"] if run_metrics else "Mirage run review.",
                    "timestamp": run.get("last_event_at"),
                    "request": last_request,
                    "suppressed_count": suppression_count,
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
                "blocked": overview["overview"]["blocked_count"],
                "flagged": overview["overview"]["flagged_count"],
                "error": overview["overview"]["error_count"],
                "risky_runs": overview["overview"]["risky_run_count"],
                "containment_rate": overview["overview"].get("containment_rate"),
                "suppressed_actions": sum(len(run_suppressions) for run_suppressions in suppressions.values()),
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
        payload = _build_run_payload(app, run_id)
        if payload is None:
            return JSONResponse(status_code=404, content={"error": f"Unknown run: {run_id}"})
        return payload

    @app.get("/api/runs/{run_id}/containment")
    async def run_containment(run_id: str):
        metrics = get_run_containment(app.state.engine.trace_store.artifact_root, run_id)
        if metrics is None:
            return JSONResponse(status_code=404, content={"error": f"Unknown run: {run_id}"})
        return metrics.to_dict()

    @app.get("/api/gateway/feed")
    async def gateway_feed(limit: int = Query(default=50, ge=1, le=500)):
        events = _collect_gateway_events(
            app.state.engine.trace_store.artifact_root, limit=limit
        )
        return {"events": events, "count": len(events)}

    @app.get("/api/chat/stream")
    async def chat_stream(run_id: str = Query(..., description="Mirage run ID to replay as a chat stream.")):
        payload = _build_run_payload(app, run_id)
        if payload is None:
            return JSONResponse(status_code=404, content={"error": f"Unknown run: {run_id}"})

        async def stream() -> AsyncIterator[str]:
            risk = payload["risk"]
            yield _sse_event(
                "status",
                {
                    "run_id": run_id,
                    "message": f"Connected to Mirage review stream for {run_id}.",
                    "level": risk["level"],
                },
            )
            intro = (
                f"{payload['summary']['headline']} "
                f"Mirage inspected {payload['meta']['event_count']} action(s) with "
                f"{risk['risky_steps']} risky and {risk['suppressed_steps']} suppressed."
            )
            for chunk in _chunk_text(intro):
                yield _sse_event(
                    "message_delta",
                    {
                        "message_id": f"{run_id}-summary",
                        "role": "assistant",
                        "delta": chunk,
                    },
                )
                await asyncio.sleep(0.012)

            for side_effect in payload["side_effects"]:
                yield _sse_event(
                    "step",
                    {
                        "run_id": run_id,
                        "step_index": side_effect["step_index"],
                        "side_effect": side_effect,
                        "message": _stream_step_message(side_effect),
                    },
                )
                yield _sse_event(
                    "metric",
                    {
                        **risk,
                        "focus_step_index": side_effect["step_index"],
                        "focus_outcome": side_effect["outcome"],
                    },
                )
                await asyncio.sleep(0.02)

            yield _sse_event(
                "complete",
                {
                    "run_id": run_id,
                    "completed_at": _now_iso(),
                    "risk": risk,
                },
            )

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/api/runs/{run_id}/side-effects/{step_index}/suppress")
    async def suppress_side_effect(
        run_id: str,
        step_index: int,
        payload: dict[str, Any] | None = Body(default=None),
    ):
        run_payload = _build_run_payload(app, run_id)
        if run_payload is None:
            return JSONResponse(status_code=404, content={"error": f"Unknown run: {run_id}"})

        side_effect = _find_side_effect(run_payload, step_index)
        if side_effect is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"Unknown side effect {step_index} for run {run_id}."},
            )

        reason = _normalize_suppression_reason(payload, side_effect)
        suppression = {
            "suppressed": True,
            "reason": reason,
            "suppressed_at": _now_iso(),
            "step_index": step_index,
        }
        _suppression_store(app).setdefault(run_id, {})[step_index] = suppression
        updated_payload = _build_run_payload(app, run_id)
        updated_side_effect = _find_side_effect(updated_payload, step_index) if updated_payload else None
        return {
            "run_id": run_id,
            "step_index": step_index,
            "suppression": suppression,
            "side_effect": updated_side_effect,
        }

    return app


def _cors_middleware_kwargs() -> dict[str, Any]:
    origins = [value.strip() for value in os.getenv("MIRAGE_ALLOWED_ORIGINS", "").split(",") if value.strip()]
    origin_regex = os.getenv("MIRAGE_ALLOWED_ORIGIN_REGEX")
    if origin_regex is None and not origins:
        origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    kwargs: dict[str, Any] = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if origins:
        kwargs["allow_origins"] = origins
    if origin_regex:
        kwargs["allow_origin_regex"] = origin_regex
    return kwargs


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
    suppressions: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    indexed_steps = [
        _decorate_step(step, index=index, run_id=run_id, suppression=suppressions.get(index))
        for index, step in enumerate(steps, start=1)
    ]
    side_effects = [_side_effect_from_step(step) for step in indexed_steps]
    risk = _build_risk_snapshot(indexed_steps, final_outcome)
    agent_health = _build_agent_health(final_outcome, risk)
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
        "risk": risk,
        "agent_health": agent_health,
        "steps": indexed_steps,
        "side_effects": side_effects,
        "trace": trace,
        "trace_path": trace_path,
    }


def _build_run_payload(app: FastAPI, run_id: str) -> dict[str, Any] | None:
    run_metrics = build_run_metrics(app.state.engine.trace_store.artifact_root, run_id)
    if run_metrics is None:
        return None
    payload = _run_detail_payload(
        run_id=run_metrics["run_id"],
        trace=run_metrics["trace"],
        trace_path=run_metrics["trace_path"],
        source="trace metrics review",
        headline=run_metrics["headline"],
        final_outcome=run_metrics["final_outcome"],
        steps=_trace_events_to_steps(run_metrics["trace"].get("events", [])),
        suppressions=_suppression_store(app).get(run_id, {}),
    )
    containment = get_run_containment(app.state.engine.trace_store.artifact_root, run_id)
    if containment is not None:
        payload["containment"] = containment.to_dict()
    return payload


def _decorate_step(
    step: dict[str, Any],
    *,
    index: int,
    run_id: str,
    suppression: dict[str, Any] | None,
) -> dict[str, Any]:
    outcome = str(step.get("mirage", {}).get("outcome", "unknown"))
    decisions = step.get("mirage", {}).get("decisions", []) or []
    confidence = _confidence_for_outcome(outcome, len(decisions))
    return {
        **step,
        "step_index": index,
        "step_id": f"{run_id}-step-{index}",
        "severity": _severity_for_outcome(outcome, suppression),
        "confidence": confidence,
        "suppression": suppression,
    }


def _side_effect_from_step(step: dict[str, Any]) -> dict[str, Any]:
    mirage = step.get("mirage", {})
    request = step.get("request", {})
    response = step.get("response", {})
    suppression = step.get("suppression")
    status = "suppressed" if suppression else mirage.get("outcome", "unknown")
    return {
        "id": step["step_id"],
        "step_index": step["step_index"],
        "name": step.get("name"),
        "method": request.get("method", "GET"),
        "path": request.get("path", "/"),
        "payload": request.get("payload"),
        "status_code": response.get("status_code"),
        "response_body": response.get("body"),
        "outcome": mirage.get("outcome", "unknown"),
        "severity": step.get("severity"),
        "message": mirage.get("message"),
        "decision_summary": mirage.get("decision_summary"),
        "decisions": mirage.get("decisions", []),
        "matched_mock": mirage.get("matched_mock"),
        "policy_passed": mirage.get("policy_passed", False),
        "timestamp": step.get("trace_event", {}).get("timestamp"),
        "confidence": step.get("confidence"),
        "suppressed": bool(suppression),
        "suppression": suppression,
        "status": status,
    }


def _build_risk_snapshot(steps: list[dict[str, Any]], final_outcome: str) -> dict[str, Any]:
    risky_steps = [step for step in steps if step.get("mirage", {}).get("outcome") != "allowed"]
    suppressed_steps = [step for step in steps if step.get("suppression")]
    base_score = {
        "allowed": 18,
        "policy_violation": 82,
        "unmatched_route": 68,
        "config_error": 92,
    }.get(final_outcome, 48)
    score = max(6, min(98, base_score + max(0, len(risky_steps) - 1) * 7 - len(suppressed_steps) * 12))
    if score >= 80:
        level = "critical"
    elif score >= 55:
        level = "elevated"
    elif score >= 30:
        level = "guarded"
    else:
        level = "stable"
    return {
        "score": score,
        "level": level,
        "total_steps": len(steps),
        "risky_steps": len(risky_steps),
        "suppressed_steps": len(suppressed_steps),
        "allowed_steps": sum(1 for step in steps if step.get("mirage", {}).get("outcome") == "allowed"),
    }


def _build_agent_health(final_outcome: str, risk: dict[str, Any]) -> dict[str, Any]:
    status = "stable"
    summary = "Agent actions are tracking inside configured guardrails."
    if final_outcome == "policy_violation":
        status = "watch"
        summary = "A policy caught a risky action before it became a real side effect."
    elif final_outcome == "unmatched_route":
        status = "watch"
        summary = "An unconfigured route needs a mock before this workflow is safe in CI."
    elif final_outcome == "config_error":
        status = "critical"
        summary = "Mirage config needs repair before the workflow can be trusted."
    elif final_outcome == "blocked":
        status = "watch"
        summary = "Gateway enforced a policy and blocked a risky action from reaching upstream."
    elif final_outcome == "flagged":
        status = "watch"
        summary = "Gateway flagged a policy violation in passthrough mode; enforcement was off."
    elif final_outcome == "error":
        status = "critical"
        summary = "Gateway hit an error decision path; check upstream and config."
    if risk["suppressed_steps"] and status == "watch":
        summary += " Suppression is active while the team reviews the trace."
    return {
        "status": status,
        "summary": summary,
        "confidence": round(max(0.35, 1 - risk["score"] / 120), 2),
        "label": {
            "stable": "Nominal",
            "watch": "Needs Review",
            "critical": "Degraded",
        }[status],
    }


def _confidence_for_outcome(outcome: str, decision_count: int) -> float:
    base = {
        "allowed": 0.92,
        "policy_violation": 0.63,
        "unmatched_route": 0.57,
        "config_error": 0.41,
        # Gateway-mode outcomes.
        "blocked": 0.55,
        "flagged": 0.6,
        "error": 0.41,
    }.get(outcome, 0.5)
    modifier = min(0.06, decision_count * 0.01)
    return round(max(0.32, min(0.98, base + modifier)), 2)


def _severity_for_outcome(outcome: str, suppression: dict[str, Any] | None) -> str:
    if suppression:
        return "suppressed"
    if outcome == "allowed":
        return "nominal"
    if outcome == "config_error" or outcome == "error":
        return "critical"
    if outcome == "policy_violation" or outcome == "blocked":
        return "high"
    if outcome == "unmatched_route" or outcome == "flagged":
        return "medium"
    return "low"


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


def _stream_step_message(side_effect: dict[str, Any]) -> str:
    decision_summary = side_effect.get("decision_summary") or side_effect.get("message") or "No extra detail."
    if side_effect.get("suppressed"):
        return f"{side_effect['name']} is currently suppressed. {decision_summary}"
    return (
        f"{side_effect['name']} finished as `{side_effect['outcome']}` on "
        f"`{side_effect['method']} {side_effect['path']}`. {decision_summary}"
    )


def _suppression_store(app: FastAPI) -> dict[str, dict[int, dict[str, Any]]]:
    return app.state.side_effect_suppressions


def _collect_gateway_events(artifact_root: str | Path, *, limit: int) -> list[dict[str, Any]]:
    """Return recent trace events whose `mode` is `passthrough` or `enforce`.

    Sorted by timestamp descending (newest first), capped at `limit`.
    Used by the console's Gateway tab to render a streaming decision
    feed without surfacing CI-mode events.
    """

    root = Path(artifact_root)
    if not root.exists():
        return []
    collected: list[dict[str, Any]] = []
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        events = data.get("events", [])
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            mode = event.get("mode")
            if mode not in ("passthrough", "enforce"):
                continue
            collected.append(_summarize_gateway_event(event, run_id=data.get("run_id") or path.stem))

    collected.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return collected[:limit]


def _summarize_gateway_event(event: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    request = event.get("request") if isinstance(event.get("request"), dict) else {}
    response = event.get("response") if isinstance(event.get("response"), dict) else {}
    decisions = event.get("policy_decisions") if isinstance(event.get("policy_decisions"), list) else []
    failed = [d for d in decisions if isinstance(d, dict) and not d.get("passed")]
    return {
        "run_id": run_id,
        "timestamp": event.get("timestamp"),
        "mode": event.get("mode"),
        "outcome": event.get("outcome"),
        "method": request.get("method"),
        "path": request.get("path"),
        "upstream_url": event.get("upstream_url"),
        "upstream_status": event.get("upstream_status"),
        "status_code": response.get("status_code"),
        "policy_passed": event.get("policy_passed", True),
        "time_to_decide_us": event.get("time_to_decide_us"),
        "failed_decisions": [
            {
                "name": d.get("name"),
                "field": d.get("field"),
                "operator": d.get("operator"),
                "message": d.get("message"),
            }
            for d in failed
        ],
        "message": event.get("message"),
    }


def _normalize_suppression_reason(payload: dict[str, Any] | None, side_effect: dict[str, Any]) -> str:
    reason = ""
    if isinstance(payload, dict):
        reason = str(payload.get("reason") or "").strip()
    if reason:
        return reason
    return side_effect.get("decision_summary") or "Suppressed from the Mirage console while triaging risk."


def _find_side_effect(payload: dict[str, Any] | None, step_index: int) -> dict[str, Any] | None:
    if payload is None:
        return None
    for side_effect in payload.get("side_effects", []):
        if side_effect.get("step_index") == step_index:
            return side_effect
    return None


def _chunk_text(text: str, size: int = 24) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [text]


def _sse_event(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


app = create_demo_app()


if __name__ == "__main__":
    uvicorn.run(
        "demo_ui.server:app",
        host=os.getenv("HOST", os.getenv("MIRAGE_HOST", "127.0.0.1")),
        port=int(os.getenv("PORT", "5100")),
        reload=True,
    )
