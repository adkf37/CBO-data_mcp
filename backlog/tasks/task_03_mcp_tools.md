# Task 03 — MCP Tools Implementation

**Phase:** Build 4c  
**Owner:** Backend Dev  
**Priority:** High  
**Depends on:** Task 02 (data consolidation)

---

## Objective

Implement the core Model Context Protocol (MCP) tools that the LLM will call to answer user questions about CBO data.

## Tools to Implement

| Tool Name | Description |
|---|---|
| `list_file_types` | Returns all available CBO data file type identifiers and descriptions |
| `list_vintages` | Returns available vintage years for a given file type |
| `get_projection` | Returns projection values filtered by file type, program, year range, and optional vintage |
| `compare_vintages` | Returns side-by-side comparison of the same metric across two vintages |
| `search_programs` | Full-text search across program/category names in a file type |
| `export_csv` | Exports a query result set to a CSV file and returns the file path |

## Acceptance Criteria

- [x] Module `src/mcp_tools.py` implements all 6 tools as callable Python functions.
- [x] Each tool has a docstring with parameter descriptions (used by the LLM as the tool schema).
- [x] Tool schemas are registered in `src/tool_registry.py` in MCP-compatible JSON format.
- [x] Unit tests in `tests/test_mcp_tools.py` cover:
  - `list_file_types` returns a non-empty list.
  - `get_projection` returns correct rows for a known program + year.
  - `compare_vintages` returns both vintages' values in the result.
  - `export_csv` creates a file at the returned path.
- [x] All tools handle missing/invalid inputs gracefully and return informative error messages.

## Implementation Notes

- Use the `mcp` Python library (`pip install mcp`) for protocol compliance.
- Tool inputs and outputs should be JSON-serializable.
- `export_csv` should write to a user-configurable output directory (default: `./exports/`). The full implementation of the CSV file-naming and metadata strategy is defined in Task 06; the Task 03 version may be a working stub that writes a basic file.
- `search_programs` performs case-insensitive substring matching across the program/category name column(s). Fuzzy matching is out of scope for the initial implementation.
- `tool_registry.py` must map each tool name string to the corresponding Python function so the Gemini integration (Task 04) can resolve calls dynamically without hard-coding function references.
- All tools must return a Python `dict` (or `list[dict]`) so results are directly JSON-serialisable for the MCP response envelope.
