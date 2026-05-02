"""Tests for the OpenAI Agents SDK adapter.

These tests exercise the adapter against a stub `Agent`-shaped object
so they do not require the real SDK in CI. The first test confirms a
friendly error path when the SDK is absent; the others substitute the
SDK with a stub module so the rest of the adapter logic exercises
exactly what it would in production.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any, Callable

import httpx
import pytest

from mirage.integrations.openai_agents import (
    MiragePolicyBlockedError,
    wrap_with_mirage,
)


@pytest.fixture
def stub_agents_module(monkeypatch):
    """Pretend the OpenAI Agents SDK is installed by registering a stub module."""

    module = types.ModuleType("agents")
    monkeypatch.setitem(sys.modules, "agents", module)
    yield module
    monkeypatch.delitem(sys.modules, "agents", raising=False)


@dataclass
class _StubTool:
    name: str
    func: Callable[..., Any]


class _StubAgent:
    def __init__(self, tools: list[_StubTool]):
        self.tools = tools


def test_wrap_with_mirage_raises_when_sdk_not_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "agents", None)
    with pytest.raises(ImportError) as exc_info:
        wrap_with_mirage(_StubAgent([]), gateway_url="http://gw")
    assert "openai-agents" in str(exc_info.value)


def test_wrap_with_mirage_routes_tool_call_through_gateway_and_proceeds_on_200(
    stub_agents_module, monkeypatch
):
    captured: dict[str, Any] = {}

    def transport_handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["content"] = request.content
        return httpx.Response(200, json={"status": "allowed"})

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Client(transport=httpx.MockTransport(transport_handler)).post(
            url, **kwargs
        ),
    )

    def real_tool(value: int) -> int:
        return value * 2

    stub_agent = _StubAgent([_StubTool(name="multiply", func=real_tool)])
    wrapped = wrap_with_mirage(
        stub_agent,
        gateway_url="https://gw.example.com",
        run_id="agent-run-1",
    )

    result = wrapped.tools[0].func(21)
    assert result == 42
    assert captured["url"] == "https://gw.example.com/v1/tools/multiply"
    assert captured["headers"]["x-mirage-run-id"] == "agent-run-1"


def test_wrap_with_mirage_blocks_tool_call_on_403(stub_agents_module, monkeypatch):
    def transport_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "status": "blocked",
                "message": "Mirage policy violation: cap_bid_amount",
                "policy_decisions": [{"name": "cap_bid_amount", "passed": False}],
            },
        )

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Client(transport=httpx.MockTransport(transport_handler)).post(
            url, **kwargs
        ),
    )

    real_tool_called = {"value": False}

    def real_tool(amount: int) -> int:
        real_tool_called["value"] = True
        return amount

    stub_agent = _StubAgent([_StubTool(name="submit_bid", func=real_tool)])
    wrapped = wrap_with_mirage(
        stub_agent,
        gateway_url="https://gw.example.com",
    )

    with pytest.raises(MiragePolicyBlockedError) as exc_info:
        wrapped.tools[0].func(50000)

    assert "cap_bid_amount" in str(exc_info.value)
    assert exc_info.value.decisions == [{"name": "cap_bid_amount", "passed": False}]
    assert real_tool_called["value"] is False


def test_wrap_with_mirage_surfaces_unreachable_gateway_as_blocked_error(
    stub_agents_module, monkeypatch
):
    def transport_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("gateway offline")

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Client(transport=httpx.MockTransport(transport_handler)).post(
            url, **kwargs
        ),
    )

    stub_agent = _StubAgent([_StubTool(name="x", func=lambda: 1)])
    wrapped = wrap_with_mirage(stub_agent, gateway_url="https://gw.example.com")

    with pytest.raises(MiragePolicyBlockedError) as exc_info:
        wrapped.tools[0].func()
    assert "unreachable" in str(exc_info.value)


def test_wrap_with_mirage_validates_gateway_url(stub_agents_module):
    with pytest.raises(ValueError):
        wrap_with_mirage(_StubAgent([]), gateway_url="")


def test_wrap_with_mirage_returns_agent_unchanged_when_no_tools(
    stub_agents_module, monkeypatch
):
    stub_agent = _StubAgent([])
    wrapped = wrap_with_mirage(stub_agent, gateway_url="https://gw.example.com")
    assert wrapped.tools == []


def test_wrap_with_mirage_does_not_mutate_original_agent(stub_agents_module, monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Response(200, json={"status": "allowed"}),
    )

    original_tool = _StubTool(name="t", func=lambda: 7)
    stub_agent = _StubAgent([original_tool])
    wrapped = wrap_with_mirage(stub_agent, gateway_url="https://gw.example.com")

    assert wrapped is not stub_agent
    assert wrapped.tools is not stub_agent.tools
    assert stub_agent.tools[0].func() == 7
