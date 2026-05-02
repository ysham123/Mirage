"""Deterministic policy evaluator.

The policy layer is the load-bearing piece of Mirage's mission: same policy
file, evaluated by rules, in CI mode (against mocks) and in gateway mode
(against real upstreams). This module owns that evaluation. It deliberately
has no dependency on mocks, traces, FastAPI, or the run mode. Everything
else in the codebase calls into it.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel

from .config import MirageConfig, PolicyConfig


class PolicyDecision(BaseModel):
    name: str
    passed: bool
    message: str
    field: str
    operator: str
    expected: Any = None
    actual: Any = None


class PolicyEvaluator:
    """Evaluates a request payload against the policy section of MirageConfig.

    Pure function in a class wrapper so the same evaluator instance can be
    held by both the CI engine and the gateway. No I/O, no trace writes, no
    mode awareness.
    """

    def __init__(self, config: MirageConfig):
        self._config = config

    @property
    def config(self) -> MirageConfig:
        return self._config

    def evaluate(
        self,
        *,
        method: str,
        path: str,
        payload: Any,
    ) -> list[PolicyDecision]:
        method_name = method.upper()
        decisions: list[PolicyDecision] = []

        for policy in self._config.policies:
            if policy.method and policy.method.upper() != method_name:
                continue
            if policy.path and not path_matches(policy.path, path):
                continue

            actual, exists = extract_field(payload, policy.field)
            try:
                passed = apply_operator(policy, actual, exists)
                message = policy.message
            except TypeError as exc:
                passed = False
                message = f"{policy.message} (policy evaluation failed: {exc})"

            decisions.append(
                PolicyDecision(
                    name=policy.name,
                    passed=passed,
                    message=message,
                    field=policy.field,
                    operator=policy.operator,
                    expected=policy.value,
                    actual=actual,
                )
            )

        return decisions


def extract_field(payload: Any, field: str) -> tuple[Any, bool]:
    current = payload
    for part in field.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return None, False
    return current, True


def apply_operator(policy: PolicyConfig, actual: Any, exists: bool) -> bool:
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
    if operator == "regex_match":
        if not isinstance(actual, str):
            return False
        return re.search(expected, actual) is not None
    if operator == "not_regex_match":
        if not isinstance(actual, str):
            return False
        return re.search(expected, actual) is None
    if operator == "contains":
        if isinstance(actual, str):
            if not isinstance(expected, str):
                return False
            return expected in actual
        if isinstance(actual, (list, tuple)):
            return expected in actual
        return False
    if operator == "not_contains":
        if isinstance(actual, str):
            if not isinstance(expected, str):
                return False
            return expected not in actual
        if isinstance(actual, (list, tuple)):
            return expected not in actual
        return False
    if operator == "starts_with":
        if not isinstance(actual, str):
            return False
        return actual.startswith(expected)
    if operator == "not_starts_with":
        if not isinstance(actual, str):
            return False
        return not actual.startswith(expected)
    if operator == "ends_with":
        if not isinstance(actual, str):
            return False
        return actual.endswith(expected)
    if operator == "length_lte":
        if not hasattr(actual, "__len__"):
            return False
        return len(actual) <= expected
    if operator == "length_gte":
        if not hasattr(actual, "__len__"):
            return False
        return len(actual) >= expected
    if operator == "host_in":
        host = _extract_host(actual)
        if host is None:
            return False
        return host in expected
    if operator == "host_not_in":
        host = _extract_host(actual)
        if host is None:
            return False
        return host not in expected
    raise ValueError(f"Unsupported operator: {operator}")


def _extract_host(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    host = parsed.hostname
    return host if host else None


_PARAM_RE = re.compile(r"\{([^{}/]+)\}")


def path_matches(pattern: str, path: str) -> bool:
    if "{" not in pattern:
        return pattern == path
    regex = (
        "^"
        + _PARAM_RE.sub(
            r"(?P<\1>[^/]+)",
            re.escape(pattern).replace(r"\{", "{").replace(r"\}", "}"),
        )
        + "$"
    )
    return re.match(regex, path) is not None


def summarize_decision(decision: PolicyDecision) -> str:
    if decision.operator == "exists":
        detail = f"field '{decision.field}' must exist"
    else:
        detail = (
            f"field '{decision.field}' must satisfy "
            f"{decision.operator} {format_value(decision.expected)} but got {format_value(decision.actual)}"
        )
    return f"{decision.name}: {decision.message} ({detail})"


def format_value(value: Any) -> str:
    return repr(value)


def build_policy_violation_message(decisions: list[PolicyDecision]) -> str:
    failed = [decision for decision in decisions if not decision.passed]
    if not failed:
        return "Mirage detected a policy violation."
    return "Mirage policy violation: " + " | ".join(
        summarize_decision(decision) for decision in failed
    )
