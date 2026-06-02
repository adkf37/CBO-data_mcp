"""MCP server adapter for the CBO data tools.

This module exposes the existing tool registry through the official MCP Python
SDK. It is intentionally a thin adapter: the Gemini web app and the MCP server
both call the same functions in ``src.mcp_tools`` and ``src.official_tools``.

Run locally with:

    python -m src.mcp_server
"""

from __future__ import annotations

import argparse
import inspect
from collections.abc import Callable
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from src.tool_registry import get_gemini_tool_declarations, get_tool

_SERVER_NAME = "cbo-data-mcp"

_TYPE_MAP: dict[str, Any] = {
    "array": list[Any],
    "boolean": bool,
    "integer": int,
    "number": float,
    "object": dict[str, Any],
    "string": str,
}


def _annotation_for_schema(schema: dict[str, Any], *, required: bool) -> Any:
    """Return a Python annotation matching a small JSON-schema subset."""
    base = _TYPE_MAP.get(str(schema.get("type")), Any)
    return base if required else Optional[base]


def _adapter_signature(
    declaration: dict[str, Any],
    tool_fn: Callable[..., Any],
) -> inspect.Signature:
    """Build a public MCP signature from the existing tool declaration."""
    parameters_schema = declaration.get("parameters", {})
    properties = parameters_schema.get("properties", {})
    required = set(parameters_schema.get("required", []))
    original_parameters = inspect.signature(tool_fn).parameters
    parameters: list[inspect.Parameter] = []
    for name, schema in properties.items():
        is_required = name in required
        original = original_parameters.get(name)
        if is_required:
            default = inspect.Parameter.empty
        elif original is not None and original.default is not inspect.Parameter.empty:
            default = original.default
        else:
            default = None
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=_annotation_for_schema(schema, required=is_required),
            )
        )
    return inspect.Signature(parameters=parameters, return_annotation=Any)


def _make_tool_adapter(
    name: str,
    declaration: dict[str, Any],
) -> Callable[..., Any]:
    """Create a FastMCP-friendly wrapper around a registered tool function."""
    tool_fn = get_tool(name)

    def adapter(**kwargs: Any) -> Any:
        return tool_fn(**kwargs)

    adapter.__name__ = name
    adapter.__qualname__ = name
    adapter.__doc__ = declaration.get("description", "")
    adapter.__signature__ = _adapter_signature(declaration, tool_fn)  # type: ignore[attr-defined]
    return adapter


def create_mcp_server() -> FastMCP:
    """Return a FastMCP server with every registered CBO tool exposed."""
    server = FastMCP(
        _SERVER_NAME,
        instructions=(
            "Tools for querying Congressional Budget Office baseline, "
            "economic, budget, spending, and demographic projection data. "
            "Use discovery tools first when the dataset, variable, vintage, "
            "category, or unit is uncertain."
        ),
    )
    for declaration in get_gemini_tool_declarations():
        name = declaration["name"]
        server.add_tool(
            _make_tool_adapter(name, declaration),
            name=name,
            description=declaration.get("description", ""),
        )
    return server


mcp = create_mcp_server()


def main(argv: list[str] | None = None) -> None:
    """Run the MCP server.

    Stdio is the default because it is the simplest transport for local MCP
    clients. The same server object can also run via streamable HTTP for remote
    experiments.
    """
    parser = argparse.ArgumentParser(description="Run the CBO Data MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default="stdio",
        help="MCP transport to run. Use stdio for local desktop clients.",
    )
    args = parser.parse_args(argv)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
