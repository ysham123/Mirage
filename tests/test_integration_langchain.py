"""Tests for the LangChain integration adapter.

These exercise the adapter against a stub LangChain-shaped agent so
they do not require LangChain in CI. The first test confirms a
friendly error path when LangChain is absent; the rest substitute the
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

from mirage.integrations.langchain import (
    MiragePolicyBlockedError,
    wrap_with_mirage,
)


@pytest.fixture
def stub_langchain_module(monkeypatch):
    module = types.ModuleType("langchain")
    monkeypatch.setitem(sys.modules, "langchain", module)
    yield module
    monkeypatch.delitem(sys.modules, "langchain", raising=False)


@dataclass
class _StubTool:
    name: str
    func: Callable[..., Any]


class _StubAgent:
    def __init__(self, tools: list[_StubTool]):
        self.tools = tools


def test_wrap_with_mirage_raises_when_langchain_not_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "langchain", None)
    with pytest.raises(ImportError) as exc_info:
        wrap_with_mirage(_StubAgent([]), gateway_url="http://gw")
    assert "langchain" in str(exc_info.value).lower()


def test_wrap_with_mirage_routes_tool_call_through_gateway(stub_langchain_module, monkeypatch):
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

    def real_tool(bid_amount: int) -> dict:
        return {"status": "submitted", "bid_amount": bid_amount}

    agent = _StubAgent([_StubTool(name="submit_bid", func=real_tool)])
    wrapped = wrap_with_mirage(
        agent,
        gateway_url="https://gw.example.com",
        run_id="agent-run-1",
    )

    result = wrapped.tools[0].func(bid_amount=5000)
    assert result == {"status": "submitted", "bid_amount": 5000}
    assert captured["url"] == "https://gw.example.com/v1/tools/submit_bid"
    assert captured["headers"]["x-mirage-run-id"] == "agent-run-1"


def test_default_payload_mapper_lifts_kwargs_to_root(stub_langchain_module, monkeypatch):
    captured: dict[str, Any] = {}

    def transport_handler(request: httpx.Request) -> httpx.Response:
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "allowed"})

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Client(transport=httpx.MockTransport(transport_handler)).post(
            url, **kwargs
        ),
    )

    agent = _StubAgent([_StubTool(name="submit_bid", func=lambda **kw: kw)])
    wrapped = wrap_with_mirage(agent, gateway_url="https://gw.example.com")
    wrapped.tools[0].func(bid_amount=5000, contract_id="x")

    body = captured["body"]
    assert body["tool"] == "submit_bid"
    assert body["bid_amount"] == 5000
    assert body["contract_id"] == "x"
    assert body["kwargs"] == {"bid_amount": 5000, "contract_id": "x"}


def test_default_payload_mapper_lifts_single_dict_arg_to_root(stub_langchain_module, monkeypatch):
    captured: dict[str, Any] = {}

    def transport_handler(request: httpx.Request) -> httpx.Response:
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "allowed"})

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Client(transport=httpx.MockTransport(transport_handler)).post(
            url, **kwargs
        ),
    )

    agent = _StubAgent([_StubTool(name="t", func=lambda payload: payload)])
    wrapped = wrap_with_mirage(agent, gateway_url="https://gw.example.com")
    wrapped.tools[0].func({"bid_amount": 5000})

    body = captured["body"]
    assert body["bid_amount"] == 5000
    assert body["args"] == [{"bid_amount": 5000}]


def test_custom_payload_mapper_overrides_default(stub_langchain_module, monkeypatch):
    captured: dict[str, Any] = {}

    def transport_handler(request: httpx.Request) -> httpx.Response:
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "allowed"})

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Client(transport=httpx.MockTransport(transport_handler)).post(
            url, **kwargs
        ),
    )

    def my_mapper(tool_name, args, kwargs):
        return {"override_field": "custom-value"}

    agent = _StubAgent([_StubTool(name="t", func=lambda **kw: kw)])
    wrapped = wrap_with_mirage(
        agent, gateway_url="https://gw.example.com", payload_mapper=my_mapper
    )
    wrapped.tools[0].func(anything=1)
    assert captured["body"] == {"override_field": "custom-value"}


def test_wrap_with_mirage_blocks_tool_call_on_403(stub_langchain_module, monkeypatch):
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

    def real_tool(**kwargs) -> int:
        real_tool_called["value"] = True
        return 1

    agent = _StubAgent([_StubTool(name="submit_bid", func=real_tool)])
    wrapped = wrap_with_mirage(agent, gateway_url="https://gw.example.com")

    with pytest.raises(MiragePolicyBlockedError) as exc_info:
        wrapped.tools[0].func(bid_amount=50000)

    assert "cap_bid_amount" in str(exc_info.value)
    assert real_tool_called["value"] is False


def test_wrap_with_mirage_validates_gateway_url(stub_langchain_module):
    with pytest.raises(ValueError):
        wrap_with_mirage(_StubAgent([]), gateway_url="")


def test_wrap_with_mirage_does_not_mutate_original_agent(stub_langchain_module, monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Response(200, json={"status": "allowed"}),
    )

    original_tool = _StubTool(name="t", func=lambda: 7)
    agent = _StubAgent([original_tool])
    wrapped = wrap_with_mirage(agent, gateway_url="https://gw.example.com")

    assert wrapped is not agent
    assert wrapped.tools is not agent.tools
    assert agent.tools[0].func() == 7
