from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from src.trace import TraceStore


class MirageResponseError(AssertionError):
    pass


class MirageRunError(AssertionError):
    pass


@dataclass(frozen=True)
class MirageResponseReport:
    run_id: str | None
    outcome: str
    policy_passed: bool
    trace_path: str | None
    matched_mock: str | None
    message: str | None
    decision_summary: str | None

    @property
    def safe(self) -> bool:
        return self.outcome == "allowed" and self.policy_passed


@dataclass(frozen=True)
class MirageRunIssue:
    index: int
    method: str
    path: str
    outcome: str
    message: str | None
    matched_mock: str | None
    decision_summary: str | None


@dataclass(frozen=True)
class MirageRunSummary:
    run_id: str
    trace_path: str
    found: bool
    total_actions: int
    safe_actions: int
    risky_actions: int
    outcomes: dict[str, int]
    issues: list[MirageRunIssue]

    @property
    def safe(self) -> bool:
        return self.found and self.risky_actions == 0

    def to_text(self) -> str:
        if not self.found:
            return (
                f"Mirage run '{self.run_id}' has no trace at {self.trace_path}. "
                "Route the agent through Mirage or set a stable run_id before gating."
            )

        lines = [
            f"Mirage run: {self.run_id}",
            f"Trace path: {self.trace_path}",
            (
                "Summary: "
                f"{self.total_actions} action(s), "
                f"{self.safe_actions} safe, "
                f"{self.risky_actions} risky"
            ),
        ]
        if not self.issues:
            lines.append("Result: clean run")
            return "\n".join(lines)

        lines.append("Risky actions:")
        for issue in self.issues:
            detail = issue.decision_summary or issue.message or "Mirage marked the action as unsafe."
            lines.append(
                f"- [{issue.outcome}] {issue.method} {issue.path} "
                f"(event {issue.index}, mock={issue.matched_mock or 'none'}): {detail}"
            )
            hint = _remediation_hint(issue.outcome)
            if hint:
                lines.append(f"  Next: {hint}")
        return "\n".join(lines)


class MirageSession:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        run_id: str | None = None,
        artifact_root: str | Path | None = None,
        timeout: float = 10.0,
        **client_kwargs: Any,
    ):
        self.run_id = run_id or os.getenv("MIRAGE_RUN_ID") or f"mirage-run-{uuid.uuid4().hex[:8]}"
        self.artifact_root = _resolve_artifact_root(artifact_root)
        self._client = create_mirage_client(
            base_url=base_url,
            run_id=self.run_id,
            timeout=timeout,
            **client_kwargs,
        )
        self._reports: list[MirageResponseReport] = []

    @property
    def client(self) -> httpx.Client:
        return self._client

    @property
    def reports(self) -> tuple[MirageResponseReport, ...]:
        return tuple(self._reports)

    def __enter__(self) -> MirageSession:
        self._client.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._client.__exit__(exc_type, exc, tb)

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        response = self._client.request(method, url, **kwargs)
        self._reports.append(mirage_response_report(response))
        return response

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    def summary(self) -> MirageRunSummary:
        return mirage_run_summary(self.run_id, artifact_root=self.artifact_root)

    def assert_clean(self) -> MirageRunSummary:
        return assert_mirage_run_clean(self.run_id, artifact_root=self.artifact_root)


def create_mirage_client(
    *,
    base_url: str | None = None,
    run_id: str | None = None,
    timeout: float = 10.0,
    **client_kwargs: Any,
) -> httpx.Client:
    resolved_base_url = base_url or os.getenv("MIRAGE_PROXY_URL", "http://localhost:8000")
    resolved_run_id = run_id or os.getenv("MIRAGE_RUN_ID")

    headers = dict(client_kwargs.pop("headers", {}) or {})
    if resolved_run_id and "X-Mirage-Run-Id" not in headers and "x-mirage-run-id" not in headers:
        headers["X-Mirage-Run-Id"] = resolved_run_id

    return httpx.Client(
        base_url=resolved_base_url,
        timeout=timeout,
        headers=headers,
        **client_kwargs,
    )


def mirage_response_report(response: httpx.Response) -> MirageResponseReport:
    outcome = response.headers.get("X-Mirage-Outcome")
    policy_header = response.headers.get("X-Mirage-Policy-Passed")
    if outcome is None or policy_header is None:
        raise ValueError("Response does not include Mirage metadata headers.")

    return MirageResponseReport(
        run_id=response.headers.get("X-Mirage-Run-Id"),
        outcome=outcome,
        policy_passed=policy_header.lower() == "true",
        trace_path=response.headers.get("X-Mirage-Trace-Path"),
        matched_mock=response.headers.get("X-Mirage-Matched-Mock"),
        message=response.headers.get("X-Mirage-Message"),
        decision_summary=response.headers.get("X-Mirage-Decision-Summary"),
    )


def assert_mirage_response_safe(response: httpx.Response) -> MirageResponseReport:
    report = mirage_response_report(response)
    if report.safe:
        return report

    detail = report.decision_summary or report.message or "Mirage marked the request as unsafe."
    raise MirageResponseError(
        "Mirage request was not safe "
        f"(outcome={report.outcome}, run_id={report.run_id}, trace_path={report.trace_path}): {detail}"
    )


def mirage_run_summary(
    run_id: str,
    *,
    artifact_root: str | Path | None = None,
) -> MirageRunSummary:
    store = TraceStore(_resolve_artifact_root(artifact_root))
    trace_path = store.trace_path(run_id)
    trace = store.read_trace(run_id)
    events = trace.get("events", [])

    if not trace_path.exists():
        return MirageRunSummary(
            run_id=run_id,
            trace_path=str(trace_path),
            found=False,
            total_actions=0,
            safe_actions=0,
            risky_actions=0,
            outcomes={},
            issues=[],
        )

    issues: list[MirageRunIssue] = []
    outcomes: dict[str, int] = {}
    safe_actions = 0
    risky_actions = 0

    for index, event in enumerate(events, start=1):
        request = event.get("request", {}) if isinstance(event, dict) else {}
        outcome = str(event.get("outcome", "unknown"))
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        policy_passed = bool(event.get("policy_passed", False))
        is_safe = outcome == "allowed" and policy_passed
        if is_safe:
            safe_actions += 1
            continue

        risky_actions += 1
        issues.append(
            MirageRunIssue(
                index=index,
                method=str(request.get("method", "REQUEST")).upper(),
                path=str(request.get("path", "unknown")),
                outcome=outcome,
                message=_coerce_optional_text(event.get("message")),
                matched_mock=_coerce_optional_text(event.get("matched_mock")),
                decision_summary=_summarize_event_decisions(event),
            )
        )

    return MirageRunSummary(
        run_id=run_id,
        trace_path=str(trace_path),
        found=True,
        total_actions=len(events),
        safe_actions=safe_actions,
        risky_actions=risky_actions,
        outcomes=outcomes,
        issues=issues,
    )


def assert_mirage_run_clean(
    run_id: str,
    *,
    artifact_root: str | Path | None = None,
) -> MirageRunSummary:
    summary = mirage_run_summary(run_id, artifact_root=artifact_root)
    if summary.safe:
        return summary
    raise MirageRunError(summary.to_text())


def _resolve_artifact_root(artifact_root: str | Path | None) -> Path:
    if artifact_root is not None:
        return Path(artifact_root)
    default_root = Path(__file__).resolve().parent.parent / "artifacts" / "traces"
    return Path(os.getenv("MIRAGE_ARTIFACT_ROOT", str(default_root)))


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


_REMEDIATION_HINTS: dict[str, str] = {
    "unmatched_route": "Add a mock for this route in mocks.yaml or route the agent around it.",
    "policy_violation": "Tighten the agent or relax this policy in policies.yaml.",
    "config_error": "Fix the config file referenced in the message above before rerunning.",
}


def _remediation_hint(outcome: str) -> str | None:
    return _REMEDIATION_HINTS.get(outcome)


def _summarize_event_decisions(event: dict[str, Any]) -> str | None:
    decisions = event.get("policy_decisions", [])
    failed = [decision for decision in decisions if isinstance(decision, dict) and not decision.get("passed", False)]
    if not failed:
        return _coerce_optional_text(event.get("message"))

    parts = []
    for decision in failed:
        field = decision.get("field", "field")
        operator = decision.get("operator", "eq")
        expected = repr(decision.get("expected"))
        actual = repr(decision.get("actual"))
        message = decision.get("message", "Mirage policy failed.")
        parts.append(f"{decision.get('name', 'policy')}: {message} ({field} {operator} {expected}, got {actual})")
    return " | ".join(parts)
