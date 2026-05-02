"""OpenAI Agents SDK adapter.

Wraps an `Agent` instance so every tool call the agent makes is first
evaluated by a running Mirage gateway. The gateway's configured
policies decide allow or block. Blocked tool calls surface to the agent
as a runtime error (HTTP 403 from the gateway, surfaced through the
wrapped tool); allowed tool calls fall through to the original tool
implementation.

The OpenAI Agents SDK is an optional dependency. The import happens
inside `wrap_with_mirage` so the rest of `mirage` continues to install
and run without it. Install with `pip install mirage-ci[openai-agents]`.

This adapter does NOT modify model invocations. Mirage is concerned
with actions, not with what the model says. Output-quality scoring is
a separate concern, intentionally out of scope.
"""

from __future__ import annotations

import copy
import os
from typing import TYPE_CHECKING, Any, Callable
import uuid

import httpx

if TYPE_CHECKING:
    from agents import Agent  # type: ignore[import-not-found]
else:
    Agent = Any


_INSTALL_HINT = (
    "OpenAI Agents SDK not installed. "
    "Install with `pip install mirage-ci[openai-agents]`."
)


def wrap_with_mirage(
    agent: "Agent",
    *,
    gateway_url: str,
    run_id: str | None = None,
    timeout_seconds: float = 10.0,
) -> "Agent":
    """Return a copy of `agent` whose tool calls are routed through a Mirage gateway.

    Tool calls made by the wrapped agent are sent to the Mirage gateway
    at `gateway_url` for a policy decision before the underlying tool
    runs. The gateway's own configured policies decide allow/block. The
    agent does not see policy decisions directly; a blocked action
    surfaces as an HTTP 403 from the gateway, which the wrapped tool
    raises as a `MiragePolicyBlockedError` for the agent's normal
    error-handling path.

    `gateway_url` must point at a running `mirage gateway` instance
    (see the `mirage gateway` CLI). When `run_id` is omitted, a fresh
    one is generated and passed via the `X-Mirage-Run-Id` header so the
    gateway groups every tool call from this wrapped agent into one
    Mirage run.

    This adapter does NOT modify model invocations. Mirage is concerned
    with actions, not with what the model says. Output-quality scoring
    is a separate concern, intentionally out of scope.
    """

    if agent is None:
        raise ValueError("wrap_with_mirage requires an `agent` instance.")
    if not gateway_url:
        raise ValueError("wrap_with_mirage requires a non-empty `gateway_url`.")

    _require_openai_agents_sdk()

    resolved_run_id = run_id or _generate_run_id()
    wrapped = copy.copy(agent)

    tools = getattr(wrapped, "tools", None)
    if not tools:
        return wrapped

    new_tools: list[Any] = []
    for tool in tools:
        new_tools.append(
            _wrap_tool(
                tool,
                gateway_url=gateway_url.rstrip("/"),
                run_id=resolved_run_id,
                timeout_seconds=timeout_seconds,
            )
        )
    wrapped.tools = new_tools
    return wrapped


class MiragePolicyBlockedError(RuntimeError):
    """Raised by a Mirage-wrapped tool when the gateway blocks the call.

    The agent's tool-error handling can catch this directly. The
    `decisions` attribute carries the failed policy decisions returned
    by the gateway in its 403 body.
    """

    def __init__(self, message: str, *, decisions: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.decisions = decisions or []


def _wrap_tool(
    tool: Any,
    *,
    gateway_url: str,
    run_id: str,
    timeout_seconds: float,
) -> Any:
    tool_name = _tool_name(tool)
    original_call = _resolve_tool_callable(tool)

    def mirage_checked(*args: Any, **kwargs: Any) -> Any:
        payload = _payload_from_call(args, kwargs)
        _check_with_gateway(
            gateway_url=gateway_url,
            run_id=run_id,
            tool_name=tool_name,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
        return original_call(*args, **kwargs)

    return _replace_tool_callable(tool, mirage_checked)


def _check_with_gateway(
    *,
    gateway_url: str,
    run_id: str,
    tool_name: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> None:
    path = f"/v1/tools/{tool_name}"
    headers = {"X-Mirage-Run-Id": run_id, "Content-Type": "application/json"}
    try:
        response = httpx.post(
            f"{gateway_url}{path}",
            json=payload,
            headers=headers,
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise MiragePolicyBlockedError(
            f"Mirage gateway unreachable at {gateway_url}: {exc}"
        ) from exc

    if response.status_code == 403:
        body = _safe_json(response)
        decisions = body.get("policy_decisions") if isinstance(body, dict) else None
        message = (
            body.get("message")
            if isinstance(body, dict) and body.get("message")
            else f"Mirage gateway blocked tool call to {tool_name}."
        )
        raise MiragePolicyBlockedError(str(message), decisions=decisions or [])


def _payload_from_call(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if args:
        payload["args"] = list(args)
    if kwargs:
        payload["kwargs"] = dict(kwargs)
    return payload


def _tool_name(tool: Any) -> str:
    name = getattr(tool, "name", None)
    if isinstance(name, str) and name:
        return name
    fn = _resolve_tool_callable(tool)
    return getattr(fn, "__name__", "tool")


def _resolve_tool_callable(tool: Any) -> Callable[..., Any]:
    for attr in ("__call__", "func", "callable", "run", "_func"):
        candidate = getattr(tool, attr, None)
        if attr == "__call__" and callable(tool):
            return tool
        if callable(candidate):
            return candidate
    raise TypeError(f"Cannot resolve a callable from tool: {tool!r}")


def _replace_tool_callable(tool: Any, replacement: Callable[..., Any]) -> Any:
    if callable(tool):
        try:
            wrapped = copy.copy(tool)
        except TypeError:
            wrapped = tool
        for attr in ("func", "callable", "run", "_func"):
            if hasattr(tool, attr):
                setattr(wrapped, attr, replacement)
                return wrapped
        return replacement
    for attr in ("func", "callable", "run", "_func"):
        if hasattr(tool, attr):
            wrapped = copy.copy(tool)
            setattr(wrapped, attr, replacement)
            return wrapped
    raise TypeError(f"Cannot replace callable on tool: {tool!r}")


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {}


def _generate_run_id() -> str:
    prefix = os.getenv("MIRAGE_RUN_ID_PREFIX", "openai-agents")
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _require_openai_agents_sdk() -> None:
    try:
        import agents  # type: ignore[import-not-found]  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ImportError(_INSTALL_HINT) from exc


__all__ = [
    "MiragePolicyBlockedError",
    "wrap_with_mirage",
]
