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

### 2026-05-12 — Decision D-010 (Task ID: task_03)
- **Validation evidence recorded:** `python -m pip install -r requirements.txt`, `python -m py_compile src/mcp_tools.py src/tool_registry.py`, `python -m pytest tests/test_mcp_tools.py -q`, and `python -m pytest -q` all passed in the independent validation environment.
- **Acceptance gate passed:** The evidence confirms all six MCP tools remain callable, required tool schemas are registered in `src/tool_registry.py`, invalid-input handling is covered, and the Task 03 `export_csv` stub writes a real file.
- **Validation scope boundary:** No repository-managed lint or static type-check command exists yet, and broader coverage thresholds remain owned by `task_07`, so validation stayed focused on the explicit `task_03` acceptance criteria plus regression coverage from the current repo test suite.
- **Next loop recommendation:** Advance to Closeout for `task_03`; if closeout agrees, return to Build for `task_04`.

### 2026-05-12 — Decision D-011 (Task ID: task_03)
- **Closeout outcome:** Reviewer confirmed `task_03` satisfies the sprint Definition of Done after rerunning the existing validation commands, checking the task checklist in `backlog/tasks/task_03_mcp_tools.md`, and verifying the review/validation artifacts align with the implemented MCP tools slice.
- **Explicit non-complete rationale:** `.squad/sprint.md` still shows `task_04` through `task_08` as unfinished, so the project cannot emit `Complete` during this closeout.
- **Handoff refresh:** `STATUS.md`, `.squad/review_report.md`, and `project_overview.md` now summarize the validated MCP tools slice and point the next loop at `task_04`.
- **Return-to-build target:** The next automatable task is `task_04` (Gemini 2.5 Flash Integration).

### 2026-05-12 — Decision D-012 (Task ID: task_04)
- **Routing applied:** Coordinator assigned `task_04` to Backend Dev (Gemini integration) and Tester (unit tests), per `.squad/routing.md`. Scribe logs this decision.
- **task_04 implementation completed:** Added `src/llm_agent.py` with `CBOAgent` class:
  - `CBOAgent(api_key: str | None)` constructor reads the API key from `GEMINI_API_KEY` env var (via python-dotenv); raises `ValueError` if absent; never hardcodes or logs the key.
  - `ask(question: str) -> str` runs the Gemini tool-calling loop, dispatching function calls through `get_tool()` from `tool_registry.py`, capping iterations at `_MAX_TOOL_ITERATIONS = 10`, and logging each call at DEBUG level.
  - `_build_genai_tools()` converts the `get_gemini_tool_declarations()` dict list to `genai.protos.Tool` / `FunctionDeclaration` objects for the Gemini SDK.
  - Graceful error handling: unknown or failing tool calls return `{"error": ...}` fed back to the model rather than raising.
- **Tests added:** `tests/test_llm_agent.py` — 10 offline unit tests (constructor validation, single-turn Q&A, tool dispatch with args, error wrapping, iteration cap) plus 3 benchmark integration tests (`@pytest.mark.integration`, auto-skipped without `GEMINI_API_KEY`).
- **pytest.ini added:** Registers the `integration` mark to silence `PytestUnknownMarkWarning`; aligns with `task_07` acceptance gate (`pytest tests/ -m "not integration"`).
- **SDK deprecation noted:** `google-generativeai` is deprecated upstream (replaced by `google-genai`). Per task spec requirement, `google-generativeai>=0.5.0` is retained; migration to `google-genai` is deferred to a future task.
- **Build-loop validation evidence:** `python -m py_compile src/llm_agent.py` — syntax OK; `python -m pytest tests/test_llm_agent.py -v` — 10 passed, 3 skipped; `python -m pytest -q` — 38 passed, 3 skipped.
- **Next task:** Validate for `task_04`.

### 2026-05-12 — Decision D-013 (Task ID: task_04)
- **Validation evidence recorded:** `python -m pip install -r requirements.txt`, `python -m py_compile src/llm_agent.py`, `python -m pytest tests/test_llm_agent.py -v`, and `python -m pytest -q` all passed in the independent validation environment.
- **Acceptance gate passed:** The evidence confirms `CBOAgent` reads `GEMINI_API_KEY`, registers Gemini tool declarations from the registry, runs the multi-turn tool loop with a 10-iteration cap, logs tool calls at DEBUG level, and keeps the benchmark Gemini queries covered in `tests/test_llm_agent.py`.
- **Blocked but acceptable validation scope:** Live Gemini benchmark execution remained blocked because `GEMINI_API_KEY` is absent in the validation environment; the integration tests were discovered and skipped as designed, which matches the task contract.
- **Non-blocking risk noted:** `google.generativeai` emits an upstream deprecation warning; task_04 explicitly defers migration, so validation records it as follow-up rather than a failure.
- **Next loop recommendation:** Advance to Closeout for `task_04`; if closeout agrees, return to Build for `task_05`.

### 2026-05-12 — Decision D-014 (Task ID: task_04)
- **Closeout outcome:** Reviewer confirmed `task_04` satisfies the sprint Definition of Done after rerunning the existing validation commands, checking the task checklist in `backlog/tasks/task_04_gemini_integration.md`, and verifying the closeout artifacts align with the implemented Gemini integration slice.
- **Explicit non-complete rationale:** `.squad/sprint.md` still shows `task_05` through `task_08` as unfinished, so the project cannot emit `Complete` during this closeout.
- **Handoff refresh:** `STATUS.md`, `.squad/review_report.md`, `project_overview.md`, and the `task_04` checklist now summarize the validated Gemini agent slice and point the next loop at `task_05`.
- **Known follow-up risk:** Live Gemini benchmark execution still requires `GEMINI_API_KEY`, and the upstream `google.generativeai` deprecation warning remains a non-blocking future migration item.
- **Return-to-build target:** The next automatable task is `task_05` (Interactive CLI Interface).

### 2026-05-12 — Decision D-015 (Task ID: task_05)
- **Routing applied:** Coordinator assigned CLI implementation to Backend Dev, CLI smoke test coverage to Tester, and lifecycle/decision updates to Scribe per `.squad/routing.md`.
- **task_05 implementation completed:** Added `main.py` with `CBOCLI` REPL entry point runnable via `python main.py`, startup banner, command handlers for `/help`, `/types`, `/vintages <file_type>`, `/export [filename]`, and `/quit`/`/exit`, plus natural-language routing to `CBOAgent.ask()`.
- **Session-state/export behavior:** Added in-memory `CLIState` (`last_question`, `last_answer`, `last_rows`) so `/export` can call `export_csv` without re-running a query.
- **Resilience and UX:** CLI catches input and tool errors, prints friendly messages, wraps output to configurable width (`CBO_CLI_WIDTH`, default 120), and gracefully degrades when `GEMINI_API_KEY` is missing.
- **Acceptance tests added:** Added `tests/test_cli.py` smoke tests covering a mock question + `/export` + `/quit` loop and clean `/quit` exit behavior.
- **Build-loop validation evidence:** `python -m pytest tests/test_cli.py -q` passed (2/2) and `python -m pytest -q` passed (40 passed, 3 skipped).

### 2026-05-13 — Decision D-016 (Task ID: task_05)
- **Validation evidence recorded:** `python -m pip install -r requirements.txt`, `python -m py_compile main.py`, `printf '/quit\n' | python main.py`, `python -m pytest tests/test_cli.py -q`, and `python -m pytest -q` all passed in the independent validation environment.
- **Acceptance gate passed:** The evidence confirms `main.py` starts a REPL, shows the welcome banner, implements the documented built-in commands, routes natural-language questions through `CBOAgent.ask()` when available, preserves session state for `/export`, and handles missing `GEMINI_API_KEY` without crashing.
- **Blocked but acceptable validation scope:** Live Gemini-backed question answering remains blocked because `GEMINI_API_KEY` is absent in the validation environment; task_05 explicitly supports graceful degradation in that case, and the repo's integration tests continue to skip as designed.
- **Known follow-up risk:** The current `/export` behavior is validated against the existing stub implementation from `task_03`; the fuller CSV naming and metadata requirements remain owned by `task_06`.
- **Next loop recommendation:** Advance to Closeout for `task_05`; if closeout agrees, return to Build for `task_06`.

### 2026-05-13 — Decision D-017 (Task ID: task_05)
- **Closeout outcome:** Reviewer confirmed `task_05` satisfies the sprint Definition of Done after rerunning the existing closeout commands, checking the task checklist in `backlog/tasks/task_05_cli_interface.md`, and verifying the closeout artifacts align with the implemented CLI slice.
- **Explicit non-complete rationale:** `.squad/sprint.md` still shows `task_06` through `task_08` as unfinished, so the project cannot emit `Complete` during this closeout.
- **Handoff refresh:** `STATUS.md`, `.squad/review_report.md`, and `project_overview.md` now summarize the validated CLI slice and point the next loop at `task_06`.
- **Known follow-up risks:** Live Gemini-backed querying still requires `GEMINI_API_KEY`, and the fuller CSV export naming/metadata/directory requirements remain owned by `task_06`.
- **Return-to-build target:** The next automatable task is `task_06` (CSV Export Capability).

### 2026-05-13 — Decision D-018 (Task ID: task_06)
- **Routing applied:** Coordinator routed the implementation slice to Backend Dev (CSV export + CLI export wiring), Tester (targeted export regression coverage), and Scribe (status/decision refresh) per `.squad/routing.md`.
- **task_06 implementation advanced:** `src/mcp_tools.py` now writes export metadata headers (`# file_type`, `# vintage`, `# export_timestamp`), sanitizes filename components, auto-generates filenames containing file type/query/timestamp when no filename is supplied, and always creates the output directory (`Path.mkdir(parents=True, exist_ok=True)`).
- **CLI alignment:** `main.py` `/export` now forwards `file_type="cli_session"` and query context so CLI-triggered exports produce the enhanced metadata-aware output without changing command semantics.
- **Coverage updates:** Added `tests/test_csv_export.py` to assert file creation, metadata headers, valid parseability with `pandas.read_csv(comment="#")`, expected columns, auto-name content, directory creation, and filename sanitization; updated existing export assertions in `tests/test_mcp_tools.py` and `tests/test_cli.py` to read metadata-commented CSV output.
- **Git hygiene:** Added `exports/` to `.gitignore` so runtime CSV outputs are not committed.
- **Build-loop validation evidence:** `python -m pytest tests/test_csv_export.py tests/test_cli.py tests/test_mcp_tools.py -q` passed (11/11) and `python -m pytest -q` passed (42 passed, 3 skipped). Recommended next step is Validate for `task_06`.

### 2026-05-13 — Decision D-019 (Task ID: task_06)
- **Validation evidence recorded:** `python -m pip install -r requirements.txt`, `python -m py_compile main.py src/mcp_tools.py`, `python -m pytest tests/test_csv_export.py tests/test_cli.py tests/test_mcp_tools.py -q`, `python -m pytest -q`, and `python -m pytest tests/ -m "not integration" --cov=src --cov-report=term` all passed in the independent validation environment.
- **Acceptance gate passed:** The evidence confirms `export_csv` writes parseable CSV files with metadata comment headers, auto-generated filenames include sanitized task context plus timestamp data, missing export directories are created automatically, CLI `/export` still works against the enhanced format, and `exports/` remains gitignored.
- **Additional quality signal:** The non-integration coverage run measured 78% total `src/` coverage (`mcp_tools.py` 72%), which is a strong indicator that the task_06 slice is adequately exercised while the broader testing contract remains owned by `task_07`.
- **Blocked but acceptable validation scope:** Live Gemini-backed execution remains blocked because `GEMINI_API_KEY` is absent; the repo's integration tests continue to skip or deselect cleanly by design.
- **Known non-blocking risk:** `google.generativeai` still emits an upstream deprecation warning during test collection. This is already tracked as follow-up work rather than a validation failure.
- **Next loop recommendation:** Advance to Closeout for `task_06`; if closeout agrees, return to Build for `task_07`.

### 2026-05-13 — Decision D-020 (Task ID: task_06)
- **Closeout outcome:** Reviewer confirmed `task_06` satisfies the sprint Definition of Done after rerunning the existing repository checks in a fresh clone, checking the task checklist in `backlog/tasks/task_06_csv_export.md`, and aligning the closeout artifacts with the validated CSV export implementation.
- **Explicit non-complete rationale:** `.squad/sprint.md` still shows `task_07` and `task_08` as unfinished. `task_07` still lacks the required `tests/conftest.py` fixtures and fuller `pytest.ini` defaults, and `task_08` still lacks the required root-level handoff docs, so the project cannot emit `Complete`.
- **Handoff refresh:** `STATUS.md`, `.squad/review_report.md`, `project_overview.md`, and the `task_06` checklist now summarize the validated CSV export slice and point the next loop at `task_07`.
- **Known follow-up risks:** Live Gemini-backed validation still requires `GEMINI_API_KEY`, and the upstream `google.generativeai` deprecation warning remains a non-blocking future migration item.
- **Return-to-build target:** The next automatable task is `task_07` (Tests and Validation).

### 2026-05-13 — Decision D-021 (Task ID: task_07)
- **Routing applied:** Coordinator routed this Build slice to Tester as the primary owner per `.squad/routing.md` (test authoring + validation evidence), with Scribe updating lifecycle artifacts after implementation.
- **task_07 implementation completed:** Added `tests/conftest.py` with the required reusable fixtures (`sample_catalog`, `sample_df`, `mock_agent`) so test modules can share synthetic data and a patched canned-response agent without depending on external CBO/Gemini services.
- **Pytest contract completed:** Expanded `pytest.ini` to include `testpaths = tests`, a default non-integration run marker (`-m "not integration"`), and coverage guardrails (`--cov=src --cov-fail-under=70`) while retaining the registered `integration` marker.
- **Checklist alignment:** Updated `backlog/tasks/task_07_tests.md` acceptance checkboxes to match the implemented and validated test/coverage configuration.
- **Build-loop validation evidence:** `python -m pytest tests/test_cli.py tests/test_csv_export.py tests/test_mcp_tools.py -q --no-cov` passed (11/11), `python -m pytest tests/ -m "not integration" --cov=src --cov-report=term` passed (42 passed, 3 deselected, 78% `src/` coverage), and `python -m pytest -q` passed (42 passed, 3 deselected).
- **Next task:** `task_08` — Documentation.

- Significant implementation and validation choices must cite the related task ID or feedback ID.
- Reviewer owns independent Validate and Closeout decisions.
