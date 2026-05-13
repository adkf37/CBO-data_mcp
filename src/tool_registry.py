"""
tool_registry.py — Task 03: MCP tool registration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.mcp_tools import (
    aggregate_metric,
    chart_projection,
    compare_vintages,
    export_csv,
    get_projection,
    growth_rate,
    list_file_types,
    list_vintages,
    search_programs,
    summarize_file_type,
    top_n,
)

ToolFn = Callable[..., Any]

TOOL_FUNCTIONS: dict[str, ToolFn] = {
    "list_file_types": list_file_types,
    "list_vintages": list_vintages,
    "get_projection": get_projection,
    "compare_vintages": compare_vintages,
    "search_programs": search_programs,
    "export_csv": export_csv,
    "aggregate_metric": aggregate_metric,
    "top_n": top_n,
    "growth_rate": growth_rate,
    "summarize_file_type": summarize_file_type,
    "chart_projection": chart_projection,
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
        "description": (
            "Returns filtered projection rows by file type, program, year range, "
            "vintage, category, and unit. Use `category` to isolate one series "
            "within a program (e.g. only the 'Total Enrolled Within a Fiscal "
            "Year' rows of Medicaid) and `unit` to guarantee unit consistency."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "program": {"type": "string"},
                "year_start": {"type": "integer"},
                "year_end": {"type": "integer"},
                "vintage": {"type": "string"},
                "category": {"type": "string"},
                "unit": {"type": "string"},
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
    {
        "name": "aggregate_metric",
        "description": (
            "Aggregate a numeric metric across rows with optional grouping. "
            "Use this for sums, averages, min/max, or counts. agg must be one of "
            "sum, mean, min, max, median, count. Provide group_by to get one row "
            "per group (for example group_by='fiscal_year' to see a yearly total). "
            "IMPORTANT: many CBO datasets pack outlays, enrollment counts, and "
            "per-enrollee dollars into the same file under different `unit` "
            "values. The tool refuses to aggregate across mixed units — pass "
            "`unit=` (e.g. 'Millions of people') or `category=` to pick one "
            "unit-consistent series before aggregating."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "metric": {"type": "string"},
                "agg": {"type": "string"},
                "group_by": {"type": "string"},
                "program": {"type": "string"},
                "year_start": {"type": "integer"},
                "year_end": {"type": "integer"},
                "vintage": {"type": "string"},
                "category": {"type": "string"},
                "unit": {"type": "string"},
            },
            "required": ["file_type", "metric"],
        },
    },
    {
        "name": "top_n",
        "description": (
            "Return the top (or bottom) N groups ranked by an aggregated metric. "
            "Defaults to grouping by the program/category column. Set ascending=true "
            "for the bottom N. Supply `unit=` / `category=` to keep the ranking "
            "unit-consistent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "metric": {"type": "string"},
                "n": {"type": "integer"},
                "group_by": {"type": "string"},
                "agg": {"type": "string"},
                "ascending": {"type": "boolean"},
                "program": {"type": "string"},
                "year_start": {"type": "integer"},
                "year_end": {"type": "integer"},
                "vintage": {"type": "string"},
                "category": {"type": "string"},
                "unit": {"type": "string"},
            },
            "required": ["file_type", "metric"],
        },
    },
    {
        "name": "growth_rate",
        "description": (
            "Compute absolute change, percentage change, and CAGR for a metric "
            "between two years. Narrow with program / category / unit to ensure "
            "a single coherent series; mixed-unit slices are rejected."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "metric": {"type": "string"},
                "year_start": {"type": "integer"},
                "year_end": {"type": "integer"},
                "program": {"type": "string"},
                "vintage": {"type": "string"},
                "category": {"type": "string"},
                "unit": {"type": "string"},
            },
            "required": ["file_type", "metric", "year_start", "year_end"],
        },
    },
    {
        "name": "summarize_file_type",
        "description": (
            "Discovery tool: returns the schema (columns, dtypes), row count, "
            "year range, vintage list, most frequent program names, AND the full "
            "list of `categories`, `units`, and a `categories_by_unit` mapping "
            "that shows which categories report in which unit. Call this FIRST "
            "whenever you are about to chart or aggregate, so you can pick the "
            "correct unit-consistent category for the user's question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "vintage": {"type": "string"},
            },
            "required": ["file_type"],
        },
    },
    {
        "name": "chart_projection",
        "description": (
            "Build an interactive chart (line or bar) of a metric and return "
            "Chart.js-compatible JSON so the web UI can render it with zoom, "
            "hover tooltips, and a download-as-PNG button. "
            "The response includes chart_data (rendered in the browser) and "
            "points (raw numbers you can cite in the answer). "
            "CRITICAL: in CBO files the same `program` often contains rows with "
            "different `unit` values (outlays in $B, enrollment in millions of "
            "people, per-enrollee in $). The tool REJECTS mixed-unit slices. "
            "Always pass `category=` and/or `unit=` to isolate one series — "
            "e.g. for 'Medicaid enrollment over the next 10 years' pass "
            "file_type='medicaid', program='Medicaid', "
            "category='Total Enrolled Within a Fiscal Year', "
            "unit='Millions of people'. Call `summarize_file_type` first if "
            "you do not yet know which category/unit to pick. "
            "Do NOT include a file path in the answer — tell the user the chart "
            "is displayed below and they can download it with the button."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "metric": {"type": "string"},
                "program": {"type": "string"},
                "vintage": {"type": "string"},
                "year_start": {"type": "integer"},
                "year_end": {"type": "integer"},
                "kind": {"type": "string"},
                "group_by": {"type": "string"},
                "title": {"type": "string"},
                "category": {"type": "string"},
                "unit": {"type": "string"},
            },
            "required": ["file_type", "metric"],
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
