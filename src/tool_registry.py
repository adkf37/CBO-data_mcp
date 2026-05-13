"""
tool_registry.py — Task 03: MCP tool registration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.mcp_tools import (
    compare_vintages,
    export_csv,
    get_projection,
    list_file_types,
    list_vintages,
    search_programs,
)

ToolFn = Callable[..., Any]

TOOL_FUNCTIONS: dict[str, ToolFn] = {
    "list_file_types": list_file_types,
    "list_vintages": list_vintages,
    "get_projection": get_projection,
    "compare_vintages": compare_vintages,
    "search_programs": search_programs,
    "export_csv": export_csv,
}

_TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "list_file_types",
        "description": "Returns all available CBO file types with descriptions and vintages.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_vintages",
        "description": "Returns available vintage labels for a given file type.",
        "parameters": {
            "type": "object",
            "properties": {"file_type": {"type": "string"}},
            "required": ["file_type"],
        },
    },
    {
        "name": "get_projection",
        "description": "Returns filtered projection rows by file type, program, year range, and vintage.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "program": {"type": "string"},
                "year_start": {"type": "integer"},
                "year_end": {"type": "integer"},
                "vintage": {"type": "string"},
            },
            "required": ["file_type"],
        },
    },
    {
        "name": "compare_vintages",
        "description": "Compares a metric side-by-side across two vintages.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "metric": {"type": "string"},
                "vintage_a": {"type": "string"},
                "vintage_b": {"type": "string"},
                "program": {"type": "string"},
                "year": {"type": "integer"},
            },
            "required": ["file_type", "metric", "vintage_a", "vintage_b"],
        },
    },
    {
        "name": "search_programs",
        "description": "Performs case-insensitive substring search for program/category names.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["file_type", "query"],
        },
    },
    {
        "name": "export_csv",
        "description": "Exports query result rows to a CSV file and returns the file path.",
        "parameters": {
            "type": "object",
            "properties": {
                "rows": {"type": "array", "items": {"type": "object"}},
                "output_dir": {"type": "string"},
                "filename": {"type": "string"},
                "file_type": {"type": "string"},
                "vintage": {"type": "string"},
                "query_params": {"type": "object"},
            },
            "required": ["rows"],
        },
    },
]


def list_tool_names() -> list[str]:
    """Return all registered tool names."""
    return sorted(TOOL_FUNCTIONS.keys())


def get_tool(name: str) -> ToolFn:
    """Resolve a tool function by name."""
    if name not in TOOL_FUNCTIONS:
        raise KeyError(f"Unknown tool '{name}'. Available: {list_tool_names()}")
    return TOOL_FUNCTIONS[name]


def get_gemini_tool_declarations() -> list[dict[str, Any]]:
    """Return MCP/Gemini-compatible tool schema declarations."""
    return list(_TOOL_DECLARATIONS)
