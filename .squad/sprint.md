# Sprint Plan — CBO-data_mcp

**Created:** 2026-05-12  
**Phase:** Build (iterative — Phases 4a → 4h)  
**Sprint template:** web_app

---

## Execution Order

Tasks are listed in dependency order. Each task must be complete (all acceptance criteria checked) before the next dependent task begins. Independent tasks at the same dependency level may be run in parallel.

| # | Task ID | Title | Owner | Phase | Depends On | Priority |
|---|---------|-------|-------|-------|-----------|----------|
| 1 | task_01 | Catalog CBO Data Repository | Data Engineer | 4a | — | High |
| 2 | task_02 | Cross-Vintage Data Consolidation | Data Engineer | 4b | task_01 | High |
| 3 | task_03 | MCP Tools Implementation | Backend Dev | 4c | task_02 | High |
| 4 | task_04 | Gemini 2.5 Flash Integration | Backend Dev | 4d | task_03 | High |
| 5 | task_05 | Interactive CLI Interface | Backend Dev | 4e | task_04 | Medium |
| 6 | task_06 | CSV Export Capability | Backend Dev | 4f | task_03, task_05 | Medium |
| 7 | task_07 | Tests and Validation | Tester | 4g | task_01–task_06 | Medium |
| 8 | task_08 | Documentation | Scribe | 4h | task_01–task_07 | Low |

---

## Task Details

### Sprint 1 — Data Foundation (Blocking)

#### task_01 — Catalog CBO Data Repository
- **Owner:** Data Engineer
- **Inputs:** `https://github.com/adkf37/Data_friendly_CBO_Baseline_Detail` (cloned to `data/raw/`)
- **Outputs:** `scripts/catalog_data.py`, `data/catalog.json`
- **Acceptance gate:** `python scripts/catalog_data.py` runs without error; `data/catalog.json` lists ≥ 25 file types
- **Risk:** CBO data repo structure may not match expected naming patterns → Data Engineer to inspect repo before writing grouping logic

#### task_02 — Cross-Vintage Data Consolidation
- **Owner:** Data Engineer
- **Inputs:** `data/raw/` (from task_01), `data/catalog.json`
- **Outputs:** `src/data_loader.py` (`DataLoader` class), `data/consolidated/*.parquet`
- **Acceptance gate:** Unit tests in `tests/test_data_loader.py` pass; consolidated DataFrames contain `vintage` column
- **Risk:** Schema drift between vintages could cause unexpected column sets → handle with NaN fill and warning logs

---

### Sprint 2 — Core Application Logic

#### task_03 — MCP Tools Implementation
- **Owner:** Backend Dev
- **Inputs:** `src/data_loader.py` (from task_02)
- **Outputs:** `src/mcp_tools.py`, `src/tool_registry.py`
- **Acceptance gate:** All 6 tools callable; unit tests in `tests/test_mcp_tools.py` pass; `export_csv` stub writes a file
- **Risk:** MCP library API may differ between versions → pin `mcp>=1.0.0` and test against installed version

#### task_04 — Gemini 2.5 Flash Integration
- **Owner:** Backend Dev
- **Inputs:** `src/tool_registry.py` (from task_03), `GEMINI_API_KEY` env var
- **Outputs:** `src/llm_agent.py` (`CBOAgent` class)
- **Acceptance gate:** Agent resolves benchmark queries via tool calls; integration tests in `tests/test_llm_agent.py` (skip if no API key)
- **Risk:** Gemini tool-call response format may change → parse defensively and log raw responses at DEBUG level

---

### Sprint 3 — User-Facing Features

#### task_05 — Interactive CLI Interface
- **Owner:** Backend Dev
- **Inputs:** `src/llm_agent.py` (from task_04)
- **Outputs:** `main.py` (or `src/cli.py`), CLI REPL with built-in commands
- **Acceptance gate:** `python main.py` starts; all built-in commands work; smoke test in `tests/test_cli.py` passes
- **Risk:** readline unavailable on Windows → fall back to plain `input()`

#### task_06 — CSV Export Capability
- **Owner:** Backend Dev
- **Inputs:** `src/mcp_tools.py` (export_csv stub from task_03), CLI `/export` command (from task_05)
- **Outputs:** Full `export_csv` implementation with naming convention and metadata headers; `./exports/` directory auto-created
- **Acceptance gate:** Unit tests in `tests/test_csv_export.py` pass; exported file is valid CSV with expected columns
- **Risk:** None significant

---

### Sprint 4 — Quality & Handoff

#### task_07 — Tests and Validation
- **Owner:** Tester
- **Inputs:** All modules from tasks_01–06
- **Outputs:** `tests/conftest.py`, full test suite in `tests/`, `pytest.ini`, coverage report ≥ 70%
- **Acceptance gate:** `pytest tests/ -m "not integration"` passes; `--cov=src` reports ≥ 70% coverage
- **Risk:** Integration tests blocked without `GEMINI_API_KEY` → mark with `@pytest.mark.integration` and skip in CI

#### task_08 — Documentation
- **Owner:** Scribe
- **Inputs:** All completed modules, tests, and CLI
- **Outputs:** `README.md`, `QUICK_START.md`, `.env.example`, inline docstrings in `src/`
- **Acceptance gate:** README covers all sections listed in task file; `QUICK_START.md` is ≤ 5 steps; `.env.example` present
- **Risk:** None

---

## Handoff Policy

- **Build → Validate:** Tester prepares evidence (test run output, coverage report) and hands off to Reviewer.
- **Validate → Closeout:** Reviewer approves or returns to Build with a specific task ID and blocking reason.
- **Scribe** updates `.squad/decisions.md` and `STATUS.md` after each completed sprint task.

---

## Definition of Done (per task)

1. All acceptance criteria boxes checked.
2. No failing unit tests (integration tests may be skipped).
3. Scribe has logged the completion in `.squad/decisions.md`.
4. `STATUS.md` updated to reflect the next task in the sprint.
