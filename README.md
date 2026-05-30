# CBO-data_mcp

An LLM-powered CLI that lets you ask natural-language questions about U.S.
Congressional Budget Office (CBO) baseline budget projection data.  
It pairs **Google Gemini 2.5 Flash** with **Model Context Protocol (MCP)** tools
so that queries are automatically routed to the right data functions and returned
as concise, citation-ready answers.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Prepare CBO Data](#prepare-cbo-data)
4. [Run the CLI](#run-the-cli)
5. [Example Questions](#example-questions)
6. [Run the Tests](#run-the-tests)
7. [Project Structure](#project-structure)
8. [Known Limitations](#known-limitations)

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10 or later |
| Gemini API key | Required for natural-language queries |
| CBO data repo | Cloned automatically by the catalog script |

You can obtain a free Gemini API key at <https://aistudio.google.com/app/apikey>.

---

## Installation

```bash
# 1. Clone this repository
git clone https://github.com/adkf37/CBO-data_mcp.git
cd CBO-data_mcp

# 2. (Recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Gemini API key
cp .env.example .env
# Then open .env and replace "your_key_here" with your actual key
```

---

## Prepare CBO Data

The catalog script clones the CBO data repository into `data/raw/` and writes
`data/catalog.json`.  Both are git-ignored; re-run whenever you want fresh data.

```bash
python scripts/catalog_data.py
```

Expected output:

```
Cloning/updating CBO data repo into data/raw/ …
Catalogued 51 file type(s).  Catalog written to data/catalog.json.
```

### Official CBO datasets (economic, budget, demographic)

In addition to the per-program baseline workbooks above, the assistant can
query the official [US-CBO/cbo-data](https://github.com/US-CBO/cbo-data)
repository — macroeconomic projections (GDP, unemployment, inflation, interest
rates), government-wide budget totals (deficit, debt, revenues), detailed
spending by budget account, and demographic projections. This data is stored in
a DuckDB database for fast querying. Build it once with:

```bash
python scripts/fetch_cbo_official.py   # clone/update the official repo into data/cbo_official/
python scripts/catalog_official.py     # write data/official_catalog.json (13 datasets)
python scripts/build_official_db.py    # build data/cbo_official.duckdb
```

`data/official_catalog.json` is tracked; `data/cbo_official/` and the DuckDB file
are git-ignored (rebuildable). The loader auto-builds the database on first use
if it is missing. See [docs/data_crosswalk.md](docs/data_crosswalk.md) for how
the agent routes a question to the program-detail vs. official tools.

---

## Run the CLI

```bash
python main.py
```

You will see the banner:

```
CBO Data MCP CLI
Ask a question or use /help. Type /quit to exit.
cbo>
```

### Built-in Commands

| Command | Description |
|---------|-------------|
| `/help` | Show the help message |
| `/types` | List all available CBO file types |
| `/vintages <file_type>` | List available vintages for a file type |
| `/export [filename]` | Export the last answer to CSV in `./exports/` |
| `/chart <file_type> <metric> [k=v]` | Render a PNG chart in `./charts/` (kind=line\|bar, program=, vintage=, year_start=, year_end=, group_by=) |
| `/reset` | Clear the agent's conversation memory |
| `/trace` | Show the MCP tools called for the last question |
| `/quit` or `/exit` | Exit the CLI |

---

## Example Questions

```
cbo> How many people are projected to be enrolled in Medicaid in 2029?
cbo> Compare Medicare spending in 2024 versus 2025 projections.
cbo> What is the CBO deficit projection for 2030?
cbo> Which mandatory spending programs grow the fastest between 2025 and 2034?
cbo> Plot Medicaid outlays by year for the latest vintage.
cbo> /types
cbo> /vintages medicaid
cbo> /chart medicaid value kind=line program=Medicaid
cbo> /export medicaid_2029.csv
```

### MCP Tools Available to the Agent

| Tool | Purpose |
|---|---|
| `list_file_types` | Enumerate every CBO file type plus its vintages and description. |
| `list_vintages` | Vintages available for one file type. |
| `summarize_file_type` | Schema (columns, dtypes), year range, vintage list, and most frequent program names — call first on unfamiliar datasets. |
| `get_projection` | Filtered row-level lookups by program, year range, and vintage. |
| `search_programs` | Substring search across program/category names. |
| `compare_vintages` | Side-by-side metric comparison between two vintages. |
| `aggregate_metric` | sum/mean/min/max/median/count of a metric, optionally grouped. |
| `top_n` | Top (or bottom) N groups ranked by an aggregated metric. |
| `growth_rate` | Absolute change, percentage change, and CAGR between two years. |
| `chart_projection` | Render a PNG line/bar chart to `./charts/`. |
| `export_csv` | Persist any tool's rows to `./exports/` with metadata header. |

**Official US-CBO/cbo-data tools** (macro / budget totals / spending / demographics):

| Tool | Purpose |
|---|---|
| `list_official_datasets` | List the 13 official datasets (economic / budget). |
| `summarize_official_dataset` | Format, frequency, vintages, and variable sample for one dataset. |
| `search_official_variables` | Search variable names/descriptions (e.g. 'unemployment', 'deficit'). |
| `get_official_series` | Retrieve long-format series (GDP, unemployment, inflation, rates, deficit, debt, revenues). |
| `compare_official_vintages` | Compare one variable across two release vintages. |
| `official_growth_rate` | Absolute/percent change and CAGR for an official variable. |
| `chart_official_series` | Chart.js payload for an official series (with multi-vintage overlay). |
| `query_budget_accounts` | Look up or rank ~2,000 federal budget accounts (`spending_detail`). |
| `query_demographic` | Population, fertility, mortality, migration, and labor-force cohorts. |

Expected answer format (natural language, tool-cited):

> According to the **medicaid** file type, vintage **2025**, an estimated
> **84.4 million** people are projected to be enrolled in Medicaid in fiscal
> year 2029.

---

## Run the Tests

```bash
# Full suite (integration tests skipped unless GEMINI_API_KEY is set)
python -m pytest -q

# Non-integration only with coverage report
python -m pytest tests/ -m "not integration" --cov=src --cov-report=term

# Targeted suite (specific module)
python -m pytest tests/test_data_loader.py -v
```

Current coverage: **≥ 70 %** across `src/`.

---

## Project Structure

```
CBO-data_mcp/
├── data/                    # Runtime data (gitignored)
│   ├── raw/                 # CBO CSV files (cloned by catalog script)
│   ├── catalog.json         # Generated by scripts/catalog_data.py
│   └── consolidated/        # Parquet cache (generated at runtime)
├── exports/                 # CSV exports (generated at runtime)
├── scripts/
│   └── catalog_data.py      # Clones CBO repo, writes catalog.json
├── src/
│   ├── data_loader.py       # Cross-vintage CSV consolidation (DataLoader)
│   ├── mcp_tools.py         # MCP tool implementations
│   ├── tool_registry.py     # Tool name-to-function registry
│   └── llm_agent.py         # Gemini 2.5 Flash agent (CBOAgent)
├── tests/                   # Pytest unit and integration tests
├── main.py                  # CLI entry point (CBOCLI)
├── requirements.txt
├── pytest.ini
├── .env.example             # Environment variable template
└── README.md
```

---

## Known Limitations

- **Schema inconsistencies:** CBO file types that span many vintages (e.g.,
  discretionary spending) may have different column sets across years.  The
  `DataLoader` fills missing columns with `NaN` and emits a warning.
- **Integration tests require a live API key:** Tests marked
  `@pytest.mark.integration` are skipped unless `GEMINI_API_KEY` is set in the
  environment.
- **Parquet write failures:** If `pyarrow` is not installed, the disk cache for
  consolidated data is silently skipped; data is still read from raw CSVs.
- **Windows readline:** The CLI falls back to plain `input()` on platforms where
  the `readline` module is unavailable.
