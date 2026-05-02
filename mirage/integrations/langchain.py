"""LangChain adapter.

Wraps a LangChain agent or tool surface so every tool call is first
evaluated by a running Mirage gateway. The gateway's configured
policies decide allow or block. Blocked tool calls surface to the
agent as a runtime error (HTTP 403 from the gateway, surfaced through
the wrapped tool); allowed tool calls fall through to the original
implementation.

LangChain is an optional dependency. The import happens inside
`wrap_with_mirage` so the rest of `mirage` continues to install and
run without it. Install with `pip install mirage-ci[langchain]`.

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
    from langchain.agents import AgentExecutor  # type: ignore[import-not-found]
else:
    AgentExecutor = Any


_INSTALL_HINT = (
    "LangChain not installed. Install with `pip install mirage-ci[langchain]`."
)


def wrap_with_mirage(
    target: "AgentExecutor",
    *,
    gateway_url: str,
    run_id: str | None = None,
    timeout_seconds: float = 10.0,
    payload_mapper: Callable[[str, tuple[Any, ...], dict[str, Any]], dict[str, Any]] | None = None,
) -> "AgentExecutor":
    """Return a copy of `target` whose tool calls route through a Mirage gateway.

    `target` must expose a `tools` attribute that is iterable. Each
    tool can be a LangChain `BaseTool` (`name`, `func`/`coroutine`/
    `_run`), a function-style tool (`name`, callable), or any object
    that exposes a name and a callable surface. The adapter copies
    `target`, wraps each tool with a Mirage policy check, and returns
    the wrapped copy. The original `target` is not mutated.

    `gateway_url` must point at a running `mirage gateway` instance.
    When `run_id` is omitted, one is generated and passed via the
    `X-Mirage-Run-Id` header so the gateway groups every tool call
    from this wrapped agent into one Mirage run.

    `payload_mapper`, if provided, transforms the tool name and call
    args/kwargs into the JSON payload sent to the gateway. The default
    mapper sends `{"args": [...], "kwargs": {...}}` plus, for the
    common case of a single dict positional arg, the dict's keys at
    the payload root. Callers should provide a custom mapper when
    their gateway policies expect a specific payload shape.

    This adapter does NOT modify model invocations. Mirage is
    concerned with actions, not with what the model says.
    """

    if target is None:
        raise ValueError("wrap_with_mirage requires a `target` instance.")
    if not gateway_url:
        raise ValueError("wrap_with_mirage requires a non-empty `gateway_url`.")

    _require_langchain()

    resolved_run_id = run_id or _generate_run_id()
    mapper = payload_mapper or _default_payload_mapper
    wrapped = copy.copy(target)

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
                payload_mapper=mapper,
            )
        )
    wrapped.tools = new_tools
    return wrapped


class MiragePolicyBlockedError(RuntimeError):
    """Raised by a Mirage-wrapped LangChain tool when the gateway blocks the call."""

    def __init__(self, message: str, *, decisions: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.decisions = decisions or []


def _wrap_tool(
    tool: Any,
    *,
    gateway_url: str,
    run_id: str,
    timeout_seconds: float,
    payload_mapper: Callable[[str, tuple[Any, ...], dict[str, Any]], dict[str, Any]],
) -> Any:
    tool_name = _tool_name(tool)
    original_call = _resolve_tool_callable(tool)

    def mirage_checked(*args: Any, **kwargs: Any) -> Any:
        payload = payload_mapper(tool_name, args, kwargs)
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


def _default_payload_mapper(
    tool_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> dict[str, Any]:
    """Default payload mapper.

    Always emits `args` / `kwargs`. When the call is `tool({...})`
    with a single dict positional arg, the dict's top-level keys are
    also lifted to the payload root so policies that key off named
    fields (`field: bid_amount`) match without per-deployment custom
    mappers.
    """

    payload: dict[str, Any] = {"tool": tool_name}
    if args:
        payload["args"] = list(args)
    if kwargs:
        payload["kwargs"] = dict(kwargs)
        for key, value in kwargs.items():
            payload.setdefault(key, value)
    if len(args) == 1 and isinstance(args[0], dict):
        for key, value in args[0].items():
            payload.setdefault(key, value)
    return payload


def _tool_name(tool: Any) -> str:
    name = getattr(tool, "name", None)
    if isinstance(name, str) and name:
        return name
    fn = _resolve_tool_callable(tool)
    return getattr(fn, "__name__", "tool")


def _resolve_tool_callable(tool: Any) -> Callable[..., Any]:
    for attr in ("__call__", "func", "_run", "run", "coroutine", "_arun"):
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
        for attr in ("func", "_run", "run", "coroutine", "_arun"):
            if hasattr(tool, attr):
                setattr(wrapped, attr, replacement)
                return wrapped
        return replacement
    for attr in ("func", "_run", "run", "coroutine", "_arun"):
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
    prefix = os.getenv("MIRAGE_RUN_ID_PREFIX", "langchain")
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _require_langchain() -> None:
    try:
        import langchain  # type: ignore[import-not-found]  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ImportError(_INSTALL_HINT) from exc


__all__ = [
    "MiragePolicyBlockedError",
    "wrap_with_mirage",
]
