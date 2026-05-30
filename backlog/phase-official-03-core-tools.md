# Phase 03: Core Long-Format MCP Tools + Agent Routing

**Status:** Not Started
**Depends on:** 02
**Estimated scope:** L

## Objective

Expose the official long-format datasets to the LLM via new MCP tools that mirror
the discovery/lookup/compare/chart patterns of the existing tools, and teach the
agent when to route to them.

## Tasks

- [ ] Create `src/official_tools.py` implementing:
  - [ ] `list_official_datasets(domain=None)` — discovery of the 14 datasets with
    domain/format/frequency/vintages (from `data/official_catalog.json`).
  - [ ] `summarize_official_dataset(dataset, vintage=None)` — variables with
    descriptions+units, date range, frequency, format. Analogous to
    `summarize_file_type` in `src/mcp_tools.py`.
  - [ ] `search_variables(query, dataset=None)` — substring search over variable
    names + descriptions via `variable_catalog`.
  - [ ] `get_series(dataset, variables, date_start=None, date_end=None,
    vintage=None, estimate_type=None)` — returns rows + per-variable `unit` +
    `sources` citation block.
  - [ ] `compare_official_vintages(dataset, variable, vintage_a, vintage_b,
    date_start=None, date_end=None)` — analogous to `compare_vintages`.
  - [ ] `series_growth_rate(dataset, variable, date_start, date_end, vintage=None)`
    — absolute change, pct change, CAGR (date-aware: quarterly vs annual).
  - [ ] `chart_series(dataset, variable, vintage=None, vintages=None,
    date_start=None, date_end=None, kind='line', title=None)` — reuse the Chart.js
    builder from `chart_projection`; support multi-vintage overlay.
- [ ] Build a `sources` citation block for official data (repo + raw GitHub URL +
  vintage + dataset), mirroring the existing `sources` pattern.
- [ ] Register the new tools in `src/tool_registry.py` (`TOOL_FUNCTIONS` +
  `_TOOL_DECLARATIONS`); confirm `get_gemini_tool_declarations()` includes them.
- [ ] Update `src/llm_agent.py` `_SYSTEM_PROMPT` with a new section:
  - [ ] Two data families (program-detail vs official economic/budget/demographic).
  - [ ] Routing rules (GDP/unemployment/inflation/rates/deficit/debt/revenue/tax/
    demographic -> official tools).
  - [ ] Date formats (quarterly/FY/CY), `estimate_type` actual vs projected.
- [ ] Confirm existing `export_csv` works on `get_series` rows (generic row export).

## Key Files

- `src/official_tools.py` — new; all official long-format tool logic.
- `src/tool_registry.py` — register new tools alongside the existing 11.
- `src/llm_agent.py` — extend `_SYSTEM_PROMPT` routing + date/estimate guidance.
- `src/mcp_tools.py` — reference for `_filtered_frame`, `chart_projection`, `sources` pattern, `export_csv`.

## Acceptance Criteria

- `get_gemini_tool_declarations()` returns the new tools with valid JSON schema.
- The agent answers "What does CBO project for the unemployment rate through 2035?"
  by calling `get_series`/`chart_series` on `economic_projections` and citing the
  source.
- The agent answers "How did the projected deficit change between the last two
  releases?" via `compare_official_vintages` on `ten_year_budget`.
- Existing 11 tools and their tests remain unaffected.

## Notes

- Watch total tool count (11 existing + new). If selection degrades, consolidate
  (e.g., fold growth into `get_series`); keep the core set tight (~7 new).
- Reuse charting/citation/export infrastructure rather than duplicating it.
