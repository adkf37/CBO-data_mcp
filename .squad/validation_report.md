# Validation Report — 2026-05-14 (official US-CBO/cbo-data integration)

## Scope

- **Initiative:** `official-data` — parallel format-aware layer over the official
  [US-CBO/cbo-data](https://github.com/US-CBO/cbo-data) repository.
- **Phase:** Validate
- **Recommendation:** Pass → advance to Closeout

## Checks Run

1. **New unit suites (offline synthetic DuckDB fixture)**
   - Command: `python -m pytest tests/test_build_official_db.py tests/test_official_loader.py tests/test_official_tools.py -q`
   - Result: Passed — 27 passed.
   - Evidence: build creates all 5 tables; loader query/rank/demographic paths
     return expected rows; the 9 official tools return rows + a `sources` block;
     tool registration matches Gemini declarations 1:1. No network access — a
     tiny synthetic catalog + CSV tree is built into a temp DuckDB.

2. **Full repository pytest contract**
   - Command: `python -m pytest -q`
   - Result: Passed — 131 passed, 3 deselected (integration).
   - Evidence: `pytest.ini` defaults applied (`--cov=src --cov-fail-under=70 -m "not integration"`).
     Total `src/` coverage 82.92% (gate 70%). New-module coverage:
     `src/official_data/build.py` 90%, `dates.py` 90%, `loader.py` 86%,
     `src/official_tools.py` 84%, `src/tool_registry.py` 81%.

3. **End-to-end smoke against the real built database**
   - Command: ad-hoc `python -c` driving `src/official_tools.py` against
     `data/cbo_official.duckdb` (219k economic / 41k budget / 66k spending /
     652k demographic / 1,178 variable-catalog rows).
   - Result: Passed — `get_series` (unemployment_rate), `series_growth_rate`
     (real_gdp CAGR), `chart_series`, `query_budget_accounts` (top agencies =
     HHS, SSA, Treasury), and `query_demographic` all returned correct data.

4. **Registration regression**
   - `tests/test_mcp_tools.py::test_tool_registry_contains_all_registered_tools`
     updated to the new 20-tool set; passes.

## Notes / Limitations

- The DuckDB file and vendored repo are git-ignored; CI rebuilds via
  `scripts/fetch_cbo_official.py` → `scripts/catalog_official.py` →
  `scripts/build_official_db.py`. `data/official_catalog.json` is tracked.
- Existing program-detail tools are unchanged; the two families are documented
  in `docs/data_crosswalk.md` and routed by `_SYSTEM_PROMPT`.
- Live Gemini routing (does the model pick the official tools for macro/budget
  questions?) is covered by 6 new prompts (ids 25–30) in `evals/cbo_qa.xml` but
  requires `GEMINI_API_KEY` to score; not run in this offline pass.

---

# Validation Report — 2026-05-13

## Scope

- **Task ID:** `task_08`
- **Phase:** Validate
- **Recommendation:** Pass → advance to Closeout

## Checks Run

1. **Install existing dependencies**
   - Command: `python -m pip install -r requirements.txt`
   - Result: Passed
   - Evidence: The declared runtime and test dependencies installed successfully in the fresh validation clone.

2. **Repository default pytest contract**
   - Command: `python -m pytest -q`
   - Result: Passed
   - Evidence summary:
     - `pytest.ini` defaults were applied, including `--cov=src --cov-fail-under=70 -m "not integration"`.
     - 42 tests passed, 3 integration tests were deselected, and total `src/` coverage measured 77.51% (reported as 78%), satisfying the sprint's non-integration coverage gate.

3. **Explicit non-integration coverage check**
   - Command: `python -m pytest tests/ -m "not integration" --cov=src --cov-report=term`
   - Result: Passed
   - Evidence summary:
     - 42 tests passed, 3 integration tests were deselected, and total `src/` coverage again measured 77.51% (reported as 78%).
     - Module coverage was `src/data_loader.py` 87%, `src/llm_agent.py` 78%, `src/mcp_tools.py` 72%, and `src/tool_registry.py` 80%.

4. **Integration-test skip contract**
   - Command: `python -m pytest tests/test_llm_agent.py -v -o addopts=''`
   - Result: Passed
   - Evidence summary:
     - 10 unit tests passed and the 3 Gemini-backed integration tests skipped cleanly because `GEMINI_API_KEY` is not set in the validation environment.
     - Confirms the repo still honors the task_07 contract for environment-gated integration coverage.

5. **Documentation and artifact inspection**
   - Command: manual review of `README.md`, `QUICK_START.md`, `.env.example`, `pytest.ini`, `tests/conftest.py`, `STATUS.md`, `.squad/sprint.md`, and the `task_07` / `task_08` backlog files
   - Result: Passed
   - Evidence summary:
     - `README.md` contains the required project description, prerequisites, installation, data-prep, CLI usage, example questions, test commands, project structure, and known limitations sections.
     - `QUICK_START.md` provides a 5-step startup flow, `.env.example` contains `GEMINI_API_KEY=your_key_here`, `tests/conftest.py` provides the required shared fixtures, and `pytest.ini` configures `testpaths`, the `integration` marker, and the ≥70% coverage threshold.
     - All acceptance boxes in `backlog/tasks/task_07_tests.md`, `backlog/tasks/task_08_docs.md`, and `backlog/README.md` are checked, and all 8 sprint tasks in `.squad/sprint.md` are complete.

## Blocked / Not Applicable Checks

- **Live Gemini-backed end-to-end validation:** Environment-blocked without `GEMINI_API_KEY`. This does not block validation because the integration tests are explicitly marked and skipped when the key is unavailable, and that skip contract was revalidated in this pass.
- **Lint / static type-check:** Not applicable. No repository-managed lint or type-check command is defined.

## Acceptance Criteria Review

- [x] Validation steps were run or explicitly documented as blocked
- [x] `.squad/validation_report.md` exists and records the validation evidence
- [x] `STATUS.md` records the outcome and machine-readable `Next Action`
- [x] Validation evidence is written to `.squad/decisions.md`
- [x] Remaining blockers or follow-up work are explicit

## Risks / Follow-up

- The upstream `google.generativeai` package still emits a deprecation `FutureWarning` from `src/llm_agent.py`; this remains a non-blocking follow-up item for a future build loop.
- A human or CI environment with `GEMINI_API_KEY` is still required for live Gemini-backed end-to-end validation beyond the skip-path contract verified here.
- Closeout should verify the final handoff package and decide whether the fully completed sprint can now be marked `Complete`.
