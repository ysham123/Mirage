from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.config import MirageConfig, MockRouteConfig, PolicyConfig, load_mirage_config
from src.trace import TraceStore


class PolicyDecision(BaseModel):
    name: str
    passed: bool
    message: str
    field: str
    operator: str
    expected: Any = None
    actual: Any = None


class MirageResult(BaseModel):
    status_code: int
    body: Any
    policy_passed: bool
    mock_name: str | None = None
    decisions: list[PolicyDecision] = Field(default_factory=list)
    trace_path: str


class MirageEngine:
    def __init__(
        self,
        mocks_path: str | Path | None = None,
        policies_path: str | Path | None = None,
        artifact_root: str | Path | None = None,
    ):
        root = Path(__file__).resolve().parent.parent
        self.mocks_path = Path(mocks_path or root / "mocks.yaml")
        self.policies_path = Path(policies_path or root / "policies.yaml")
        self.trace_store = TraceStore(Path(artifact_root or root / "artifacts" / "traces"))

    def handle_request(
        self,
        *,
        method: str,
        path: str,
        payload: Any = None,
        headers: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> MirageResult:
        config = load_mirage_config(self.mocks_path, self.policies_path)
        headers = headers or {}
        body = payload if payload is not None else {}
        resolved_run_id = self._resolve_run_id(run_id, headers)
        mock = self._match_mock(config, method, path)
        decisions = self._evaluate_policies(config, method, path, body)
        policy_passed = all(decision.passed for decision in decisions)

        if mock is None:
            response_status = 404
            response_body = {
                "status": "error",
                "message": f"No Mirage mock configured for {method.upper()} {path}.",
            }
        else:
            response_status = mock.response.status_code
            response_body = mock.response.body

        trace_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": {
                "method": method.upper(),
                "path": path,
                "payload": body,
                "headers": dict(headers),
            },
            "matched_mock": mock.name if mock else None,
            "policy_passed": policy_passed,
            "policy_decisions": [_model_to_dict(decision) for decision in decisions],
            "response": {
                "status_code": response_status,
                "body": response_body,
            },
        }
        trace_path = self.trace_store.append_event(resolved_run_id, trace_event)

        return MirageResult(
            status_code=response_status,
            body=response_body,
            policy_passed=policy_passed,
            mock_name=mock.name if mock else None,
            decisions=decisions,
            trace_path=str(trace_path),
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
            if mock.method.upper() == method_name and mock.path == path:
                return mock
        return None

    def _evaluate_policies(
        self,
        config: MirageConfig,
        method: str,
        path: str,
        payload: Any,
    ) -> list[PolicyDecision]:
        decisions: list[PolicyDecision] = []
        method_name = method.upper()

        for policy in config.policies:
            if policy.method and policy.method.upper() != method_name:
                continue
            if policy.path and policy.path != path:
                continue

            actual, exists = self._extract_field(payload, policy.field)
            passed = self._apply_operator(policy, actual, exists)
            decisions.append(
                PolicyDecision(
                    name=policy.name,
                    passed=passed,
                    message=policy.message,
                    field=policy.field,
                    operator=policy.operator,
                    expected=policy.value,
                    actual=actual,
                )
            )

        return decisions

    def _extract_field(self, payload: Any, field: str) -> tuple[Any, bool]:
        current = payload
        for part in field.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
                continue
            return None, False
        return current, True

    def _apply_operator(self, policy: PolicyConfig, actual: Any, exists: bool) -> bool:
        operator = policy.operator
        expected = policy.value

        if operator == "exists":
            return exists
        if not exists:
            return False
        if operator == "eq":
            return actual == expected
        if operator == "neq":
            return actual != expected
        if operator == "lt":
            return actual < expected
        if operator == "lte":
            return actual <= expected
        if operator == "gt":
            return actual > expected
        if operator == "gte":
            return actual >= expected
        if operator == "in":
            return actual in expected
        if operator == "not_in":
            return actual not in expected
        raise ValueError(f"Unsupported operator: {operator}")


def _model_to_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
