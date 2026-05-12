# Project Phases — CBO-data_mcp

Aligned to the **Maestro** lifecycle.

---

## Phase 1 — Planner ✅ (current)

**Goal:** Survey the repo, define the deliverable, identify data sources, and create the backlog.

**Outputs:**
- `backlog/README.md` — project background, goals, success criteria
- `backlog/data_sources.md` — sources and availability
- `backlog/phases.md` — this file
- `backlog/tasks/` — discrete task definitions
- `STATUS.md` — updated objective
- `requirements.txt` — Python dependencies listed

---

## Phase 2 — Squad Init

**Goal:** Bootstrap `.squad/`, define team roles, and align responsibilities to backlog tasks.

**Outputs:**
- `.squad/team.md` — roster with roles (Lead, Frontend Dev, Backend Dev, Tester, Scribe)
- `.squad/routing.md` — ownership and routing rules
- `.squad/decisions.md` — decision log initialized
- `.squad/agents/*/charter.md` — one charter per agent
- `STATUS.md` — updated to show team is initialized, ready for squad-review

---

## Phase 3 — Squad Review

**Goal:** Tighten task specs, surface risks, and produce an ordered execution plan.

**Outputs:**
- `backlog/tasks/` — fully specified task files with acceptance criteria
- `.squad/sprint.md` — ordered sprint plan with ownership and dependencies
- `STATUS.md` — updated to ready-for-build

---

## Phase 4 — Build (iterative)

Each build cycle implements exactly one sprint task. Cycles include:

| Build Slice | Task File | Description |
|---|---|---|
| 4a | `task_01_catalog_data.md` | Clone CBO data repo, catalog file types, document schemas |
| 4b | `task_02_consolidate_vintages.md` | Build cross-vintage consolidation pipeline |
| 4c | `task_03_mcp_tools.md` | Implement core MCP tools |
| 4d | `task_04_gemini_integration.md` | Wire Gemini 2.5 Flash to MCP tool loop |
| 4e | `task_05_cli_interface.md` | Build interactive CLI |
| 4f | `task_06_csv_export.md` | Add CSV export capability |
| 4g | `task_07_tests.md` | Write unit and integration tests |
| 4h | `task_08_docs.md` | Write README, QUICK_START, and usage docs |

**Outputs per cycle:**
- Working code committed to branch
- `STATUS.md` updated with progress
- `.squad/decisions.md` updated

---

## Phase 5 — Validate

**Goal:** Run tests, lint, type checks, and benchmark queries; capture evidence.

**Outputs:**
- `.squad/validation_report.md` — commands run, results, pass/fail recommendation
- `STATUS.md` — updated with outcome
- `.squad/decisions.md` — validation evidence recorded

---

## Phase 6 — Closeout

**Goal:** Final review, refresh handoff artifacts, determine if project is complete or needs another build cycle.

**Outputs:**
- `.squad/review_report.md` — final decision (Complete / Human Blocked / return-to-build)
- `STATUS.md` — final status
- `.squad/decisions.md` — handoff notes
- `README.md` / `QUICK_START.md` refreshed for end users
