# Data Crosswalk: Program-Detail vs. Official CBO Datasets

This assistant now draws on **two complementary data families**. This document
explains what each covers, where they overlap, and which one to prefer for a
given question. The routing rules here are also encoded in the agent system
prompt (`src/llm_agent.py`).

## The two families

### A. Program-detail data (original)

- **Source:** CBO baseline projection workbooks for individual benefit programs
  (e.g. `51302-2026-02-medicare.xlsx`), vendored and parsed into tidy CSVs.
- **Tools:** `list_file_types`, `summarize_file_type`, `get_projection`,
  `aggregate_metric`, `top_n`, `growth_rate`, `compare_vintages`,
  `search_programs`, `chart_projection`, `export_csv`.
- **Shape:** `(program, category, fiscal_year, value, unit, vintage)` with rich
  per-program category/unit detail (outlays, enrollment, per-enrollee dollars).
- **Best for:** A **specific named benefit program** — Medicaid enrollment,
  Medicare outlays by part, SNAP spending, SSDI beneficiaries, Unemployment
  Insurance, Veterans Benefits, etc.

### B. Official US-CBO/cbo-data (new)

- **Source:** The official [US-CBO/cbo-data](https://github.com/US-CBO/cbo-data)
  GitHub repository, fetched into `data/cbo_official/` and ingested into
  `data/cbo_official.duckdb`.
- **Tools:** `list_official_datasets`, `summarize_official_dataset`,
  `search_official_variables`, `get_official_series`, `official_growth_rate`,
  `compare_official_vintages`, `chart_official_series`, `query_budget_accounts`,
  `query_demographic`.
- **Datasets (13):**
  - *Economic:* `economic_projections`, `historical_economic`,
    `long_term_economic`, `potential_gdp`, `demographic`
  - *Budget:* `ten_year_budget`, `long_term_budget`, `historical_budget`,
    `revenue_detail`, `spending_detail`, `tax_parameters`, `trust_fund`,
    `automatic_stabilizers`
- **Best for:** Macroeconomic indicators (GDP, unemployment, inflation, interest
  rates), government-wide budget totals (deficit, debt, total revenues/outlays),
  agency/account-level spending, and demographics (population, fertility,
  mortality, migration, labor-force participation).

## Routing matrix

| Question type | Preferred family | Primary tool(s) |
|---|---|---|
| Projected unemployment rate / GDP growth / inflation / interest rates | Official | `search_official_variables` → `get_official_series` / `chart_official_series` |
| Federal deficit / debt held by the public / total revenues | Official | `get_official_series` on `ten_year_budget` |
| Long-run (25-/30-year) budget or economic outlook | Official | `get_official_series` on `long_term_budget` / `long_term_economic` |
| Top agencies / budget functions by spending | Official | `query_budget_accounts` (group_by + top_n) |
| A single budget account's outlays / budget authority | Official | `query_budget_accounts` (lookup) |
| Population / fertility / mortality / migration by cohort | Official | `query_demographic` |
| Revenue by source (individual income, payroll, corporate) | Official | `get_official_series` on `revenue_detail` |
| Tax bracket / parameter values | Official | `get_official_series` on `tax_parameters` |
| **Medicaid / Medicare / SNAP / SSDI / UI / VA** program detail | Program-detail | `summarize_file_type` → `get_projection` / `chart_projection` |

## Known overlaps and tie-breaks

1. **Historical vs. projected economics.** `historical_economic` holds realized
   values; `economic_projections` holds the same variables going forward (many
   level variables are identical at the splice year). The official tools expose
   `estimate_type` (`actual` vs `projected`) so a single series can span both.
   When a user asks for "actuals" use `estimate_type='actual'`; for the forecast
   use `'projected'`.

2. **Program outlays: program-detail vs. `spending_detail`.** Both can report
   spending for, say, a health program, but at **different granularity**:
   - Program-detail files break a program into categories/units (outlays,
     enrollment, per-enrollee) across many years and vintages — best for a deep
     dive on one program.
   - `spending_detail` is a **wide, whole-of-government** snapshot (~2,000
     budget accounts × budget authority + outlays) — best for cross-agency
     rankings and totals. Do **not** add a program-detail outlay figure to a
     `spending_detail` total for the same program: they are different cuts and
     would double-count.

3. **Budget totals vs. program sums.** `ten_year_budget` totals (deficit,
   revenues, outlays) are authoritative for government-wide figures. Never
   reconstruct a government-wide total by summing individual program-detail
   files; use the official total instead.

## Date semantics (official data)

- Tokens: `2025q1` (quarterly), `FY2026` (fiscal year), `CY2026` (calendar
  year), or a bare year.
- Pass 4-digit years to `date_start` / `date_end`.
- `file_type` chooses a frequency view (`quarterly`, `fiscal`, `calendar`,
  `annual_fy`, `annual_cy`); omit it for an annual view.

## Rebuilding the official store

```pwsh
python scripts/fetch_cbo_official.py     # clone/update the official repo
python scripts/catalog_official.py       # write data/official_catalog.json
python scripts/build_official_db.py      # build data/cbo_official.duckdb
```

`data/official_catalog.json` is tracked in git; `data/cbo_official/` and
`data/cbo_official.duckdb` are git-ignored (rebuildable artifacts).
