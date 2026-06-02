from __future__ import annotations

import json

import pytest

from src import mcp_server
from src.tool_registry import list_tool_names


@pytest.mark.asyncio
async def test_create_mcp_server_exposes_registered_tools():
    server = mcp_server.create_mcp_server()

    tools = await server.list_tools()

    assert {tool.name for tool in tools} == set(list_tool_names())


@pytest.mark.asyncio
async def test_mcp_tool_schema_hides_loader_injection_parameters():
    server = mcp_server.create_mcp_server()

    tools = await server.list_tools()
    by_name = {tool.name: tool for tool in tools}

    assert "loader" not in by_name["list_file_types"].inputSchema["properties"]
    assert "loader" not in by_name["get_projection"].inputSchema["properties"]
    assert by_name["get_projection"].inputSchema["required"] == ["file_type"]
    assert (
        by_name["get_projection"].inputSchema["properties"]["include_totals"]["default"]
        is True
    )


@pytest.mark.asyncio
async def test_mcp_server_routes_calls_through_registry(monkeypatch):
    declaration = {
        "name": "echo_tool",
        "description": "Echo the provided text.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "shout": {"type": "boolean"},
            },
            "required": ["text"],
        },
    }
    calls: list[dict] = []

    def fake_tool(**kwargs):
        calls.append(kwargs)
        return {"received": kwargs}

    monkeypatch.setattr(
        mcp_server,
        "get_gemini_tool_declarations",
        lambda: [declaration],
    )
    monkeypatch.setattr(mcp_server, "get_tool", lambda name: fake_tool)

    server = mcp_server.create_mcp_server()
    result = await server.call_tool("echo_tool", {"text": "hello"})

    assert calls == [{"text": "hello", "shout": None}]
    payload = json.loads(result[0].text)
    assert payload == {"received": {"text": "hello", "shout": None}}


def test_main_runs_selected_transport(monkeypatch):
    calls = []

    class FakeServer:
        def run(self, *, transport):
            calls.append(transport)

    monkeypatch.setattr(mcp_server, "mcp", FakeServer())

    mcp_server.main(["--transport", "streamable-http"])

    assert calls == ["streamable-http"]
