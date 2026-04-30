from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from .config import MirageConfig, MockRouteConfig, load_mirage_config
from .policy import (
    PolicyDecision,
    PolicyEvaluator,
    build_policy_violation_message,
    path_matches,
    summarize_decision,
)
from .runtime_paths import resolve_artifact_root, resolve_config_path
from .trace import TraceStore

__all__ = [
    "MirageEngine",
    "MirageResult",
    "PolicyDecision",
]


class MirageResult(BaseModel):
    status_code: int
    body: Any
    outcome: Literal["allowed", "policy_violation", "unmatched_route", "config_error"]
    policy_passed: bool
    run_id: str
    mock_name: str | None = None
    decisions: list[PolicyDecision] = Field(default_factory=list)
    trace_path: str
    message: str | None = None

    def failed_decisions(self) -> list[PolicyDecision]:
        return [decision for decision in self.decisions if not decision.passed]

    def decision_summary(self) -> str | None:
        decisions = self.failed_decisions()
        if not decisions:
            return None
        return " | ".join(summarize_decision(decision) for decision in decisions)


class MirageEngine:
    def __init__(
        self,
        mocks_path: str | Path | None = None,
        policies_path: str | Path | None = None,
        artifact_root: str | Path | None = None,
    ):
        self.mocks_path = resolve_config_path(
            explicit=mocks_path,
            env_var="MIRAGE_MOCKS_PATH",
            filename="mocks.yaml",
        )
        self.policies_path = resolve_config_path(
            explicit=policies_path,
            env_var="MIRAGE_POLICIES_PATH",
            filename="policies.yaml",
        )
        self.trace_store = TraceStore(resolve_artifact_root(artifact_root))

    def handle_request(
        self,
        *,
        method: str,
        path: str,
        payload: Any = None,
        headers: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> MirageResult:
        headers = headers or {}
        body = payload if payload is not None else {}
        resolved_run_id = self._resolve_run_id(run_id, headers)

        try:
            config = load_mirage_config(self.mocks_path, self.policies_path)
        except (FileNotFoundError, OSError, ValueError, ValidationError) as exc:
            message = f"Mirage config error: {exc}"
            response_body = {"status": "error", "message": message}
            trace_path = self._write_trace(
                run_id=resolved_run_id,
                method=method,
                path=path,
                body=body,
                headers=headers,
                mock_name=None,
                policy_passed=False,
                decisions=[],
                response_status=500,
                response_body=response_body,
                outcome="config_error",
                message=message,
            )
            return MirageResult(
                status_code=500,
                body=response_body,
                outcome="config_error",
                policy_passed=False,
                run_id=resolved_run_id,
                trace_path=str(trace_path),
                message=message,
            )

        mock = self._match_mock(config, method, path)
        decisions = self._evaluate_policies(config, method, path, body)
        policies_passed = all(decision.passed for decision in decisions)

        if mock is None:
            response_status = 404
            response_body = {
                "status": "error",
                "message": f"No Mirage mock configured for {method.upper()} {path}.",
            }
            outcome = "unmatched_route"
            policy_passed = False
            message = response_body["message"]
        else:
            response_status = mock.response.status_code
            response_body = mock.response.body
            if policies_passed:
                outcome = "allowed"
                policy_passed = True
                message = "Request matched a Mirage mock and passed all policy checks."
            else:
                outcome = "policy_violation"
                policy_passed = False
                message = self._build_policy_violation_message(decisions)

        trace_path = self._write_trace(
            run_id=resolved_run_id,
            method=method,
            path=path,
            body=body,
            headers=headers,
            mock_name=mock.name if mock else None,
            policy_passed=policy_passed,
            decisions=decisions,
            response_status=response_status,
            response_body=response_body,
            outcome=outcome,
            message=message,
        )

        return MirageResult(
            status_code=response_status,
            body=response_body,
            outcome=outcome,
            policy_passed=policy_passed,
            run_id=resolved_run_id,
            mock_name=mock.name if mock else None,
            decisions=decisions,
            trace_path=str(trace_path),
            message=message,
        )

    def _resolve_run_id(self, run_id: str | None, headers: dict[str, Any]) -> str:
        if run_id:
            return run_id

        header_run_id = headers.get("x-mirage-run-id") or headers.get("X-Mirage-Run-Id")
        if header_run_id:
            return str(header_run_id)

        return os.getenv("MIRAGE_RUN_ID", "default")

    def _match_mock(self, config: MirageConfig, method: str, path: str) -> MockRouteConfig | None:
        method_name = method.upper()
        for mock in config.mocks:
            if mock.method.upper() == method_name and path_matches(mock.path, path):
                return mock
        return None

    def _evaluate_policies(
        self,
        config: MirageConfig,
        method: str,
        path: str,
        payload: Any,
    ) -> list[PolicyDecision]:
        return PolicyEvaluator(config).evaluate(method=method, path=path, payload=payload)

    def _build_policy_violation_message(self, decisions: list[PolicyDecision]) -> str:
        return build_policy_violation_message(decisions)

    def _write_trace(
        self,
        *,
        run_id: str,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, Any],
        mock_name: str | None,
        policy_passed: bool,
        decisions: list[PolicyDecision],
        response_status: int,
        response_body: Any,
        outcome: str,
        message: str | None,
    ) -> Path:
        trace_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "request": {
                "method": method.upper(),
                "path": path,
                "payload": body,
                "headers": dict(headers),
            },
            "outcome": outcome,
            "message": message,
            "matched_mock": mock_name,
            "policy_passed": policy_passed,
            "policy_decisions": [_model_to_dict(decision) for decision in decisions],
            "response": {
                "status_code": response_status,
                "body": response_body,
            },
        }
        return self.trace_store.append_event(run_id, trace_event)


def _model_to_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
