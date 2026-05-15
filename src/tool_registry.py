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
            "Year' rows of Medicaid) and `unit` to guarantee unit consistency. "
            "Rows include an `is_total` flag indicating whether the row is a "
            "subtotal/total of the rows beneath it; set `include_totals=false` "
            "to drop those rows before returning."
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
                "include_totals": {
                    "type": "boolean",
                    "description": (
                        "Whether rows flagged `is_total=true` (subtotals/totals) "
                        "are kept. Defaults to true for this tool."
                    ),
                },
            },
            "required": ["file_type"],
        },
    },
    {
        "name": "compare_vintages",
        "description": (
            "Compares a metric side-by-side across two vintages. When the user "
            "means a specific series within a file (for example Medicaid "
            "enrollment vs Medicaid outlays), pass `category=` and/or `unit=` "
            "so the comparison stays within one coherent measure. Set "
            "`include_totals=false` to drop subtotal rows from both sides."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "metric": {"type": "string"},
                "vintage_a": {"type": "string"},
                "vintage_b": {"type": "string"},
                "program": {"type": "string"},
                "year": {"type": "integer"},
                "category": {"type": "string"},
                "unit": {"type": "string"},
                "include_totals": {
                    "type": "boolean",
                    "description": (
                        "Whether subtotal/total rows are kept on both sides. "
                        "Defaults to true so callers can directly compare the "
                        "published total lines; set false to compare only the "
                        "subcomponents."
                    ),
                },
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
        "description": (
            "Exports query result rows to a CSV file with a provenance header. "
            "When exporting, pass `source_question` (the user's original question), "
            "`tool_calls` (list of {tool, args} entries describing how you got "
            "the rows), and `sources` (the citation list from the tool result) "
            "so the CSV is self-documenting and reproducible."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "rows": {"type": "array", "items": {"type": "object"}},
                "output_dir": {"type": "string"},
                "filename": {"type": "string"},
                "file_type": {"type": "string"},
                "vintage": {"type": "string"},
                "query_params": {"type": "object"},
                "source_question": {
                    "type": "string",
                    "description": "The user question that produced these rows.",
                },
                "tool_calls": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Trace of tool calls used to produce the rows; each "
                        "entry should look like {\"tool\": name, \"args\": {...}}."
                    ),
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Source citations (source_file/source_sheet/vintage) "
                        "from the tool result that produced these rows."
                    ),
                },
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
            "unit-consistent series before aggregating. "
            "BY DEFAULT, rows flagged `is_total=true` (subtotals like 'Total "
            "Medicare Benefits') are EXCLUDED so the sum does not double-count "
            "a total alongside its subcomponents. To sum only the published "
            "total lines instead, set `include_totals=true` AND narrow the "
            "slice (e.g. with `category=`) to just those total rows."
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
                "include_totals": {
                    "type": "boolean",
                    "description": (
                        "Keep `is_total=true` rows in the aggregation. "
                        "Defaults to false to prevent double counting."
                    ),
                },
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
            "unit-consistent. By default `is_total=true` rows are excluded so "
            "a 'Total' line does not crowd out the actual subcomponents."
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
                "include_totals": {"type": "boolean"},
            },
            "required": ["file_type", "metric"],
        },
    },
    {
        "name": "growth_rate",
        "description": (
            "Compute absolute change, percentage change, and CAGR for a metric "
            "between two years. Narrow with program / category / unit to ensure "
            "a single coherent series; mixed-unit slices are rejected. By "
            "default `is_total=true` rows are excluded so the start/end sums "
            "don't double-count subtotals."
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
                "include_totals": {"type": "boolean"},
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
            "Build an interactive chart of a metric and return Chart.js-compatible "
            "JSON so the web UI can render it. Supported kinds: "
            "'line' (default, for time series and vintage comparisons), "
            "'bar' (single-year program rankings), "
            "'stacked_bar' (composition over time — stack programs/categories by year). "
            "For multi-vintage line charts omit `vintage`, set `group_by='vintage'`, "
            "and pass `vintages=[...]` for explicit vintages or `vintage_start='YYYY'` "
            "for all vintages since a year. "
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
            "is displayed alongside the response."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {"type": "string"},
                "metric": {"type": "string"},
                "program": {"type": "string"},
                "vintage": {"type": "string"},
                "vintages": {"type": "array", "items": {"type": "string"}},
                "vintage_start": {"type": "string"},
                "year_start": {"type": "integer"},
                "year_end": {"type": "integer"},
                "kind": {
                    "type": "string",
                    "enum": ["line", "bar", "stacked_bar"],
                    "description": (
                        "line=time series/vintage comparison, "
                        "bar=single-year ranking, "
                        "stacked_bar=composition over time"
                    ),
                },
                "group_by": {"type": "string"},
                "title": {"type": "string"},
                "category": {"type": "string"},
                "unit": {"type": "string"},
                "include_totals": {
                    "type": "boolean",
                    "description": (
                        "Whether `is_total=true` rows are kept. Defaults to "
                        "false so stacked bars and summed lines don't double-"
                        "count a subtotal with its components. Set true when "
                        "you specifically want to chart the published total "
                        "line (and narrow with `category=` to just that line)."
                    ),
                },
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
