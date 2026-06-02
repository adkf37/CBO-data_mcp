# AGENTS.md

Guidance for coding agents working in this repository.

## Project Purpose

This repo is a Python CBO data assistant. It exposes CBO projection data through
MCP-style tool functions, a Gemini-backed CLI, and a small Flask web UI. The two
main data surfaces are:

- Program-detail baseline workbooks handled by `src/data_loader.py` and
  `src/mcp_tools.py`.
- Official US-CBO/cbo-data economic, budget, spending, and demographic datasets
  handled by `src/official_data/*` and `src/official_tools.py`.

Prefer preserving these two surfaces rather than merging their responsibilities.

## Important Paths

- `main.py`: CLI entry point.
- `src/llm_agent.py`: Gemini agent orchestration and tool-calling loop.
- `src/tool_registry.py`: authoritative registry and Gemini tool declarations.
- `src/mcp_tools.py`: program-detail CBO tools.
- `src/data_loader.py`: program-detail catalog and CSV/parquet loading.
- `src/official_tools.py`: official dataset tools exposed to the agent.
- `src/official_data/`: official CBO DuckDB build/query layer.
- `web/app.py`: Flask API and session management.
- `web/templates/index.html`: browser UI.
- `scripts/`: data acquisition, cataloging, DB build, and eval runners.
- `tests/`: pytest suite with offline synthetic fixtures.
- `docs/data_crosswalk.md`: routing guidance between program-detail and
  official data tools.
- `backlog/`: planning notes, not runtime code.

## Setup And Test Commands

Use Python 3.10+.

```powershell
pip install -r requirements.txt
python -m pytest -q
```

`pytest.ini` already excludes `integration` tests and enforces coverage over
`src/`. Integration tests require `GEMINI_API_KEY` and should not be made part of
the default local verification path unless the task explicitly needs live model
behavior.

Useful targeted checks:

```powershell
python -m pytest tests/test_mcp_tools.py -q
python -m pytest tests/test_official_tools.py -q
python -m pytest tests/test_web_app.py -q
```

To run the CLI:

```powershell
python main.py
```

To run the web app locally:

```powershell
flask --app web.app run
```

## Generated And Local Data

Do not commit generated runtime data or secrets. These are intentionally ignored:

- `.env`
- `.venv/`
- `node_modules/`
- `data/raw/`
- `data/catalog.json`
- `data/consolidated/`
- `data/cbo_official/`
- `data/cbo_official.duckdb`
- `exports/`
- coverage and Python cache artifacts

`data/official_catalog.json` is tracked and is the normalized catalog for the
official CBO datasets. Treat changes to it as source changes: inspect diffs
carefully and make sure any tests or docs still agree with it.

Program-detail data can be rebuilt with:

```powershell
python scripts/catalog_data.py
```

Official data can be rebuilt with:

```powershell
python scripts/fetch_cbo_official.py
python scripts/catalog_official.py
python scripts/build_official_db.py
```

The official loader can auto-build `data/cbo_official.duckdb` when missing. In
tests, prefer synthetic fixtures from `tests/conftest.py` instead of depending on
the live generated database.

## Coding Conventions

- Keep tool outputs JSON-serializable.
- Include `sources` blocks for data-bearing tool responses when possible.
- Keep chart tools returning Chart.js-compatible `chart_data`; the web UI
  consumes this directly.
- Register every new tool in `src/tool_registry.py` with both `TOOL_FUNCTIONS`
  and a matching declaration. `tests/test_official_tools.py` asserts registry
  consistency for official tools.
- Prefer small helper functions over duplicating filtering, citation, and JSON
  coercion logic.
- Be careful with mixed units. Many program-detail files contain dollars,
  enrollment counts, and per-person values in the same file. Aggregations and
  charts should narrow by `category` and/or `unit` to avoid invalid results.
- Preserve subtotal semantics. Several tools use `include_totals` to avoid
  double-counting total rows alongside subcomponents.
- Use pathlib for filesystem paths and parameterized SQL for DuckDB queries.
- Keep network-dependent work out of default tests.

## Data Routing Notes

Use program-detail tools for questions about selected program baselines such as
Medicaid, Medicare, SNAP, Social Security, SSI, unemployment insurance,
Veterans Benefits, and similar workbook-style projections.

Use official tools for macroeconomic projections, whole-budget totals, deficit,
debt, revenues, spending account rankings, and demographics. When variable names
are uncertain, call or test against discovery helpers first:

- `summarize_file_type` for program-detail files.
- `list_official_datasets`, `summarize_official_dataset`, or
  `search_official_variables` for official datasets.

## Web App Notes

`web/app.py` maintains in-process sessions with one lazily-created `CBOAgent` per
session. Tests should mock `CBOAgent` rather than making live Gemini calls.

The `/api/chat` response includes:

- `answer`
- `session_id`
- `tool_calls`
- `charts`
- `sources`
- `plan`

If changing chart behavior, check both the chart-producing tool and the web
response selection logic in `web/app.py`.

## Review Checklist For Changes

Before finishing a code change, consider running the narrowest relevant tests
plus `python -m pytest -q` when the change touches shared behavior.

For data/tool changes, verify:

- new or changed results remain JSON-serializable;
- citations are present and deduped where expected;
- unit filtering avoids mixed-unit aggregation;
- total/subtotal behavior is explicit;
- tool declarations match function signatures and names;
- default tests remain offline.

For UI/API changes, verify:

- browser responses remain JSON on errors;
- sessions still reset correctly;
- charts and sources are preserved in `/api/chat`;
- no live Gemini call is required in tests.
