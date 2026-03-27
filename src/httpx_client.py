from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


class MirageResponseError(AssertionError):
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
