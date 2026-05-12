# Squad Decisions

## Active Decisions

### 2026-05-12 — Decision D-001 (Task ID: SQUAD-INIT-2026-05-12)
- Adopt a 5-member working roster (Lead, Backend Dev, Data Engineer, Tester, Scribe) aligned to backlog domains.
- Retire Ralph from active roster and move artifacts to `.squad/agents/_alumni/ralph/` to comply with Maestro guidance.
- Keep Squad artifacts lightweight in-repo: team, routing, decisions, and agent charters as the core tracked files for initialization.

### 2026-05-12 — Decision D-002 (Task ID: SQUAD-REVIEW-2026-05-12)
- **Owner corrections:** Tasks 01 and 02 (data cataloging/consolidation) reassigned from Backend Dev → Data Engineer to align with routing rules. Task 05 (CLI interface) reassigned from Frontend Dev → Backend Dev because the squad has no Frontend Dev role; CLI/REPL work sits in the Backend Dev domain per `routing.md`.
- **Vintage format standardized:** All tasks now specify `YYYY-MM` as the canonical vintage label, falling back to `YYYY` when no month is determinable.
- **export_csv scope boundary clarified:** Task 03 delivers a working stub; Task 06 owns the full implementation (naming convention, metadata headers, directory creation). Both tasks update `src/mcp_tools.py` in place.
- **tool_registry.py contract added:** Task 03 must expose `get_gemini_tool_declarations()` so Task 04 can register all tools without hard-coded function references.
- **Test fixtures contract added:** Task 07 `conftest.py` must expose `sample_catalog`, `sample_df`, and `mock_agent` fixtures so each test module can run in isolation without the full data repo.
- **Sprint plan created:** `.squad/sprint.md` ordered 8 tasks across 4 sprints with explicit owner, inputs, outputs, acceptance gates, and risk notes for each task.

### 2026-05-12 — Decision D-003 (Task ID: task_01)
- **task_01 completed:** `scripts/catalog_data.py` implemented and verified.
- **Data source:** `https://github.com/adkf37/Data_friendly_CBO_Baseline_Detail` cloned to `data/raw/` with shallow depth; subsequent runs perform `git pull --ff-only`.
- **File type grouping strategy:** Strip the trailing `_{YYYY}_{MM}` (or `_{YYYY}`) suffix from each CSV stem using a regex; the remainder is the `file_type` key. Variants such as `aatf_0` and `aatf` are intentionally kept as separate file types because they have distinct schema files.
- **Schema description source:** Per-dataset `.md` files in `docs/schemas/` parsed for the `## Purpose` section. Glob candidates are filtered so that a file type's glob only matches schema files whose stem round-trips back to the same file type (prevents `aatf_0_*.md` from polluting the `aatf` entry).
- **Column metadata:** Derived by reading the CSV header row only (`pd.read_csv(..., nrows=0)`); all datasets share the common 8-column schema documented in `docs/schemas/README.md`.
- **Vintage format:** `YYYY-MM` when the month token is present; plain `YYYY` as fallback.
- **Output:** 51 distinct file types catalogued (acceptance criterion: ≥ 25). `data/raw/` and `data/catalog.json` added to `.gitignore`.
- **Network failure handling:** If the clone fails, the script logs a warning and continues with whatever data is already present in `data/raw/`.

### 2026-05-12 — Decision D-004 (Task ID: task_01)
- **Validation evidence recorded:** After installing the existing dependencies from `requirements.txt`, `python scripts/catalog_data.py` ran successfully in a clean clone and regenerated `data/catalog.json`.
- **Acceptance gate passed:** Manual structure validation confirmed 51 catalog entries, with every entry exposing `file_type`, `description`, `columns`, `vintages`, and `file_paths`.
- **Validation scope boundary:** No repo-managed lint, type-check, or pytest configuration exists yet, so validation for this slice focused on task_01's explicit acceptance criteria plus Python syntax compilation.
- **Next loop recommendation:** Advance to Closeout for task_01, then return to Build for `task_02` if closeout agrees.

### 2026-05-12 — Decision D-005 (Task ID: task_01)
- **Closeout outcome:** Reviewer confirmed `task_01` satisfies the sprint Definition of Done for this loop after rerunning the existing validation commands and aligning the task checklist with the validated implementation.
- **Explicit non-complete rationale:** `.squad/sprint.md` still shows `task_02` through `task_08` as unfinished, so the project cannot emit `Complete` during this closeout.
- **Handoff refresh:** `STATUS.md`, `.squad/review_report.md`, and `project_overview.md` now point the next loop at `task_02` and summarize the validated state of the cataloging slice for humans picking up the repo.
- **Return-to-build target:** The next automatable task is `task_02` (Cross-Vintage Data Consolidation).

### 2026-05-12 — Decision D-006 (Task ID: task_02)
- **task_02 completed:** `src/data_loader.py` (`DataLoader` class) and `tests/test_data_loader.py` (21 unit tests) implemented.
- **Catalog dependency:** `DataLoader` reads `data/catalog.json` (Task 01 output) at construction time and indexes entries by `file_type` for O(1) lookup. Raises `FileNotFoundError` with a clear message if the catalog is absent.
- **Vintage extraction:** Reuses the same `VINTAGE_RE` regex as `catalog_data.py` (`^(.+?)_(\d{4})(?:_(\d{2}))?$`). Vintage is derived from each CSV filename stem; falls back to `"unknown"` if no pattern matches.
- **Schema drift handling:** `pd.concat(..., sort=False)` across vintage frames fills missing columns with NaN. A `log.warning` is emitted per file type where column sets differ.
- **Memory guard:** If a consolidated DataFrame's deep memory usage exceeds 500 MB the DataFrame is written to parquet but **not** stored in `self._cache`. A warning is logged.
- **Parquet caching:** Consolidated files written to `data/consolidated/<file_type>.parquet` (directory auto-created). A fresh `DataLoader` instance loads from parquet if the file exists, bypassing CSV re-reads.
- **In-memory cache:** `self._cache[file_type]` stores the DataFrame after the first load (if within memory guard); subsequent calls return the same object.
- **Test isolation:** Tests use `tmp_path` fixtures and `monkeypatch` to redirect `_PROJECT_ROOT` so no real `data/raw/` or `data/catalog.json` is required. All 21 tests pass without network access.
- **Next task:** `task_03` — MCP Tools Implementation (`src/mcp_tools.py`, `src/tool_registry.py`).

### 2026-05-12 — Decision D-007 (Task ID: task_02)
- **Validation evidence recorded:** After installing the declared dependencies from `requirements.txt`, `python -m pytest tests/test_data_loader.py -v` passed all 21 tests and `python -m py_compile src/data_loader.py` completed successfully.
- **Acceptance gate passed:** The validation evidence confirms `DataLoader` exposes the required public API, returns consolidated DataFrames with a non-null `vintage` column, handles schema drift, writes parquet cache files, and supports in-memory reuse plus missing-catalog error handling.
- **Validation scope boundary:** No repository lint, type-check, or repo-wide pytest configuration exists yet, so validation remained scoped to the explicit `task_02` acceptance criteria and current targeted tests.
- **Next loop recommendation:** Advance to Closeout for `task_02`; if closeout agrees, return to Build for `task_03`.

### 2026-05-12 — Decision D-008 (Task ID: task_02)
- **Closeout outcome:** Reviewer confirmed `task_02` satisfies the sprint Definition of Done after rerunning the existing validation commands and aligning `backlog/tasks/task_02_consolidate_vintages.md` with the verified implementation.
- **Explicit non-complete rationale:** `.squad/sprint.md` still shows `task_03` through `task_08` as unfinished, so the project cannot emit `Complete` during this closeout.
- **Handoff refresh:** `STATUS.md`, `.squad/review_report.md`, and `project_overview.md` now summarize the validated `DataLoader` slice and point the next loop at `task_03`.
- **Return-to-build target:** The next automatable task is `task_03` (MCP Tools Implementation).

### 2026-05-12 — Decision D-009 (Task ID: task_03)
- **Routing applied:** Coordinator followed `.squad/routing.md` by assigning MCP implementation to Backend Dev, test coverage to Tester, and status/decision updates to Scribe within the same build slice.
- **task_03 implementation completed:** Added `src/mcp_tools.py` with six callable MCP tools (`list_file_types`, `list_vintages`, `get_projection`, `compare_vintages`, `search_programs`, `export_csv`) that return JSON-serializable structures and graceful `{"error": ...}` messages for invalid inputs.
- **Registry contract delivered:** Added `src/tool_registry.py` with a string→callable map, `get_tool`, `list_tool_names`, and `get_gemini_tool_declarations()` so Task 04 can resolve tool calls dynamically without hard-coded function references.
- **Acceptance tests added:** Added `tests/test_mcp_tools.py` covering required behaviors (`list_file_types`, `get_projection`, `compare_vintages`, `export_csv`) plus registry/declaration checks and invalid year-range error handling.
- **Build-loop validation evidence:** `python -m pytest tests/test_mcp_tools.py -q` passed (7/7) and `python -m pytest -q` passed (28/28). Recommended next step is Validate for `task_03`.

- Significant implementation and validation choices must cite the related task ID or feedback ID.
- Reviewer owns independent Validate and Closeout decisions.
