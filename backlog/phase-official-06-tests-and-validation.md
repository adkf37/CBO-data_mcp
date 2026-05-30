# Phase 06: Tests, Evals, Docs, Validation

**Status:** Not Started
**Depends on:** 03, 04, 05
**Estimated scope:** M

## Objective

Lock in the new functionality with unit tests, agent-level evals, refreshed docs,
and a green validation run that preserves the existing 70% coverage gate.

## Tasks

- [ ] Add fixtures in `tests/conftest.py`: a tiny sample `data/cbo_official/`
  layout and/or a small prebuilt DuckDB for fast, offline tests.
- [ ] `tests/test_build_official_db.py` — ingestion: tables created, row counts,
  date normalization (quarterly/FY/CY), `variable_catalog` populated.
- [ ] `tests/test_official_loader.py` — `OfficialDataLoader` query methods,
  date filters, vintage filters, demographic dimension filters.
- [ ] `tests/test_official_tools.py` — each tool's filtering, sources/citation,
  chart JSON, growth math, spending ranking, mixed-frequency guard.
- [ ] Add 4-6 prompts to `evals/cbo_qa.xml` covering economic projection lookup,
  vintage comparison of the deficit, a spending_detail ranking, and a demographic
  cohort lookup (with expected tool traces).
- [ ] Update `README.md` / `QUICK_START.md` with the fetch + build steps
  (`fetch_cbo_official.py`, `build_official_db.py`) and example questions.
- [ ] Run `pytest` (default contract: `--cov=src --cov-fail-under=70 -m "not
  integration"`) and confirm green.
- [ ] Write `.squad/validation_report.md` with commands run, results, and pass/fail.

## Key Files

- `tests/conftest.py` — new official fixtures.
- `tests/test_build_official_db.py`, `tests/test_official_loader.py`, `tests/test_official_tools.py` — new.
- `evals/cbo_qa.xml` — new official-data prompts + traces.
- `README.md`, `QUICK_START.md` — setup + example updates.
- `.squad/validation_report.md` — validation evidence.

## Acceptance Criteria

- `pytest` passes with coverage >= 70% on `src/`.
- New evals pass (or are documented as integration-gated when `GEMINI_API_KEY`
  is absent).
- Docs let a new user fetch, build the DB, and ask an economic/budget question
  end to end.

## Notes

- Keep new tests offline-safe (no network/API key) by using vendored sample data.
- Mirror existing test style in `tests/test_data_loader.py` and
  `tests/test_mcp_tools.py`.
