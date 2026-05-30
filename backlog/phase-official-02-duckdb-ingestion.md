# Phase 02: DuckDB Ingestion + Official Data Loader

**Status:** Not Started
**Depends on:** 01
**Estimated scope:** L

## Objective

Combine the vendored official CSVs into a single DuckDB database for fast
analytical queries, with normalized date handling and a variable metadata table,
and expose a read-only `OfficialDataLoader` access layer.

## Tasks

- [ ] Add `duckdb` to `requirements.txt`.
- [ ] Create a date-normalization helper that parses `1949q1`, `FY2026`, `CY2026`
  into `(year:int, freq:'quarterly'|'annual', basis:'FY'|'CY'|None, quarter:int|None,
  period_sort:str)` for range filtering and ordering.
- [ ] Create `scripts/build_official_db.py` that ingests `data/cbo_official/` into
  `data/cbo_official.duckdb`:
  - [ ] `economic_long` and `budget_long` tables: `dataset, vintage, date, year,
    freq, basis, period_sort, variable, value, estimate_type`.
  - [ ] `spending_detail` table: native wide columns + `vintage`.
  - [ ] `demographic` table: generic dimension columns (`year, age, sex,
    place_of_birth, immigration_status, migration_flow`) nullable + `measure_name`,
    `measure_value`, `dataset`, `vintage`.
  - [ ] `variable_catalog` table: `dataset, variable, description, unit, category,
    aggregation, source_frequency` loaded from `data/official_catalog.json`.
  - [ ] Indexes on `(dataset, variable, vintage)` for long tables and `(tin)` /
    `(agency)` for spending_detail.
- [ ] Create `src/official_data/__init__.py` and `src/official_data/loader.py`
  with `OfficialDataLoader` (lazy read-only DuckDB connection):
  - [ ] `list_datasets(domain=None)`, `list_variables(dataset)`,
    `list_vintages(dataset)`.
  - [ ] `query_series(dataset, variables, date_start=None, date_end=None,
    vintage=None, estimate_type=None) -> DataFrame`.
  - [ ] `query_spending(tin=None, title_query=None, agency=None,
    function_code=None, date=None, vintage=None) -> DataFrame`.
  - [ ] `query_demographic(measure, year_start=None, year_end=None, **dims) -> DataFrame`.
- [ ] Auto-build DB if missing on first loader use (or document the build step).

## Key Files

- `requirements.txt` — add `duckdb`.
- `scripts/build_official_db.py` — new; CSV -> DuckDB ingestion + indexes.
- `src/official_data/loader.py` — new; `OfficialDataLoader` query layer.
- `src/official_data/__init__.py` — new package marker.
- `data/cbo_official.duckdb` — generated DB (gitignore; rebuildable).
- `src/data_loader.py` — reference for `_extract_vintage`, parquet caching, memory-guard patterns.

## Acceptance Criteria

- `python scripts/build_official_db.py` builds `data/cbo_official.duckdb` with all
  tables populated for the headline datasets.
- `OfficialDataLoader().query_series("economic_projections", ["unemployment_rate"])`
  returns rows with normalized `year`/`freq` and the correct `unit` joinable from
  `variable_catalog`.
- Date filters work across quarterly and FY/CY datasets.
- Queries on a single dataset return in well under a second.

## Notes

- DuckDB can read CSV directly; prefer `read_csv_auto` during ingestion.
- Keep the DB read-only at query time; build is a separate offline step.
- Mixed-frequency handling: store `freq`/`basis` so tools can warn when mixing
  quarterly and annual series.
