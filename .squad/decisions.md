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

- Significant implementation and validation choices must cite the related task ID or feedback ID.
- Reviewer owns independent Validate and Closeout decisions.
