# STATUS - CBO-data_mcp

| Field | Value |
|---|---|
| Phase | build |
| Last Updated | 2026-05-13 |
| Squad Template | web_app |
| Priority | medium |
| Blocking | None |
| GitHub Repo | https://github.com/adkf37/CBO-data_mcp |
| Next Action | Validate |

## Current Objective

**Task ID:** `feedback-2026-05-13`

Human feedback (2026-05-13) requested stronger support for complicated
questions and chart generation. Implemented 5 new MCP tools
(`aggregate_metric`, `top_n`, `growth_rate`, `summarize_file_type`,
`chart_projection`), persistent chat session + tool tracing on `CBOAgent`,
and `/chart`, `/reset`, `/trace` CLI commands. `matplotlib>=3.8.0` added.
Follow-up improvements for the same feedback slice added a prompt-based eval
suite (`evals/cbo_qa.xml`), a live eval runner (`scripts/run_eval_suite.py` +
`src/eval_runner.py`), and stronger vintage-comparison behavior so
`compare_vintages` now accepts `category` / `unit` filters and merges on a
series-aware key instead of comparing broad program rows. The eval runner now
handles a missing `GEMINI_API_KEY`, supports `--validate-only`, supports
`--base-url`, and records per-question agent/API failures instead of crashing.
A fix pass on `eval_suite_run_051326.json` added per-question eval session
resets, JSON-safe tool records, explicit multi-vintage chart filters, and
stronger routing guidance for SNAP, SSDI, UI, Social Security, and
multi-vintage chart prompts. Full regression now passes with 80 passed, 3
deselected, and 77% coverage. Awaiting Validate/redeploy/live re-eval.

## Recent Activity

- 2026-05-12: Project activated by Maestro — GitHub repo created, initial task dispatched
- 2026-05-12: Planner phase completed — backlog artifacts created, repo ready for squad-init
- 2026-05-12: Squad initialized with role-specific charters and routing aligned to backlog domains
- 2026-05-12: Ralph retired from active roster and moved to `.squad/agents/_alumni/ralph/`
- 2026-05-12: Squad Review completed — task owners corrected, gaps filled, sprint plan created, repo ready for Build
- 2026-05-12: task_01 completed — `scripts/catalog_data.py` and `.gitignore` updates committed; 51 file types catalogued
- 2026-05-12: Validate completed for task_01 — catalog script rerun successfully, catalog structure verified, Next Action set to Closeout
- 2026-05-12: Closeout completed for task_01 — review report created, task_01 checklist aligned to evidence, and repo returned to Build for `task_02`
- 2026-05-12: task_02 Build completed — `src/data_loader.py` and `tests/test_data_loader.py` created; 21 unit tests pass
- 2026-05-12: Validate completed for task_02 — `src/data_loader.py` compiled cleanly and `python -m pytest tests/test_data_loader.py -v` passed all 21 tests; Next Action set to Closeout
- 2026-05-12: Closeout completed for task_02 — review report refreshed, task_02 checklist aligned to evidence, and repo returned to Build for `task_03`
- 2026-05-12: task_03 Build completed — `src/mcp_tools.py` and `src/tool_registry.py` created; `tests/test_mcp_tools.py` added; targeted and full pytest runs pass (7 and 28 tests)
- 2026-05-12: Validate completed for task_03 — dependency install, syntax validation, targeted MCP-tool tests, and full pytest regression checks all passed; Next Action set to Closeout
- 2026-05-12: task_04 Build completed — `src/llm_agent.py` and `tests/test_llm_agent.py` created; 10 unit tests pass, 3 integration tests skip without API key; `pytest.ini` added to register the `integration` mark; full regression suite: 38 pass, 3 skipped
- 2026-05-12: Validate completed for task_04 — dependency install, syntax validation, targeted LLM-agent tests, and full pytest regression checks all passed; Next Action set to Closeout
- 2026-05-12: Closeout completed for task_04 — review report refreshed, task_04 checklist aligned to evidence, and repo returned to Build for `task_05`
- 2026-05-12: task_05 Build completed — `main.py` and `tests/test_cli.py` added; CLI commands, export state handling, and REPL smoke tests validated (2 passed); full regression suite now 40 passed, 3 skipped
- 2026-05-13: Validate completed for task_05 — dependency install, CLI startup check, targeted CLI smoke tests, and full pytest regression checks all passed; Next Action set to Closeout
- 2026-05-13: Closeout completed for task_05 — review artifacts refreshed, task_05 Definition of Done confirmed, and the repo returned to Build for `task_06`
- 2026-05-13: task_06 Build completed — `src/mcp_tools.py` now performs full CSV export naming/metadata/directory handling, `tests/test_csv_export.py` added, export-related test expectations updated, and targeted/full pytest checks passed
- 2026-05-13: Validate completed for task_06 — dependency install, syntax validation, targeted export/CLI/MCP tests, full pytest regression, and non-integration coverage checks all passed; Next Action set to Closeout
- 2026-05-13: Closeout completed for task_06 — review artifacts refreshed, task_06 checklist aligned to evidence, and the repo returned to Build for `task_07`
- 2026-05-13: task_07 Build completed — `tests/conftest.py` added with shared fixtures (`sample_catalog`, `sample_df`, `mock_agent`), `pytest.ini` now sets `testpaths` plus default `--cov=src --cov-fail-under=70 -m "not integration"` options, task_07 checklist aligned, and targeted/acceptance/full pytest commands passed
- 2026-05-13: task_08 Build completed — `README.md`, `QUICK_START.md`, and `.env.example` created; `backlog/README.md` success criteria all checked; all 8 sprint tasks are now complete
- 2026-05-13: Validate completed for the full sprint — dependency install, default pytest contract, explicit coverage rerun, and LLM integration skip-path checks all passed; Next Action set to Closeout
- 2026-05-13: Closeout completed for the full sprint — final review confirmed every sprint task satisfies the Definition of Done, handoff artifacts were refreshed, and `Next Action` is now `Complete`
- 2026-05-13: Human feedback dispatched (`feedback-2026-05-13`) — added analytical tools (`aggregate_metric`, `top_n`, `growth_rate`, `summarize_file_type`), `chart_projection` (matplotlib PNGs), persistent chat + tracing on `CBOAgent`, and `/chart`, `/reset`, `/trace` CLI commands; pytest 62 passed / 3 deselected / 78.10% coverage; data catalog regenerated (51 file types); Next Action set to `Validate`
- 2026-05-13: Build follow-up for `feedback-2026-05-13` — `compare_vintages` now accepts `category` / `unit` filters and compares rows on year/program/category/unit keys, `evals/cbo_qa.xml` added with 18 prompt-level regressions, `src/eval_runner.py` + `scripts/run_eval_suite.py` added for live scoring against answer checks and tool traces, and focused/full pytest checks passed (67 passed, 3 deselected, 78.37% coverage)
- 2026-05-13: Eval-runner UX follow-up for `feedback-2026-05-13` — `scripts/run_eval_suite.py` now reports missing `GEMINI_API_KEY` as a clean blocked state instead of a traceback, supports `--validate-only` for offline suite validation, respects question selection in validation summaries, and added `tests/test_run_eval_suite.py`; pytest now passes at 70 passed / 3 deselected / 74% coverage
- 2026-05-13: Live-site eval follow-up for `feedback-2026-05-13` — `src/eval_runner.py` now includes a `WebEvalAgent` adapter for `/api/chat`, `scripts/run_eval_suite.py` supports `--base-url` / `CBO_EVAL_BASE_URL`, and the deployed Cloud Run service (`https://cbo-data-mcp-f36lbjyvaq-uc.a.run.app`) was exercised successfully. `/api/health` reported `api_key_configured=true`; a representative live eval slice on questions 2, 3, 4, and 10 produced 1 pass / 3 fails, confirming the production site still has routing gaps for latest-vintage charting and multi-vintage Medicaid comparisons. Full local pytest now passes at 73 passed / 3 deselected / 79% coverage
- 2026-05-13: Live-eval error-handling follow-up for `feedback-2026-05-13` — both Cloud Run hostnames were confirmed healthy, the public URL `https://cbo-data-mcp-367018855220.us-central1.run.app` was verified working with `/api/health` and `/api/chat`, and `src/eval_runner.py` now converts live HTTP failures into per-question eval failures with response details instead of aborting the whole run with a traceback. Focused eval-runner tests now pass at 11/11
- 2026-05-13: Eval-suite fix pass for `feedback-2026-05-13` — addressed attached 6/18 live eval results by resetting eval sessions per question, making `get_projection` / `compare_vintages` records JSON-safe, adding `vintages` and `vintage_start` filters to `chart_projection`, exposing those filters in `tool_registry.py`, and strengthening `CBOAgent` routing guidance for SNAP, SSDI, Unemployment Insurance, Social Security, latest-vintage, and multi-vintage chart prompts. Focused tests passed at 48 passed / 3 deselected; full `python -m pytest` passed at 80 passed / 3 deselected / 77% coverage

## Artifacts

| Artifact | Location | Status |
|---|---|---|
| STATUS.md | `./STATUS.md` | updated |
| FEEDBACK.md | `./FEEDBACK.md` | existing |
| Backlog README | `./backlog/README.md` | existing |
| Backlog Tasks | `./backlog/tasks/` | reviewed; all sprint task checklists complete |
| Squad Team | `./.squad/team.md` | existing |
| Squad Routing | `./.squad/routing.md` | existing |
| Squad Decisions | `./.squad/decisions.md` | updated (D-024 added) |
| Validation Report | `./.squad/validation_report.md` | updated (final sprint validation) |
| Review Report | `./.squad/review_report.md` | updated (final closeout decision: `Complete`) |
| Project Overview | `./project_overview.md` | updated (final handoff snapshot) |
| Agent Charters | `./.squad/agents/*/charter.md` | existing |
| Sprint Plan | `./.squad/sprint.md` | existing |
| Catalog Script | `./scripts/catalog_data.py` | existing (task_01) |
| Data Catalog | `./data/catalog.json` | generated at runtime (gitignored) |
| Data Loader | `./src/data_loader.py` | created (task_02) |
| Data Loader Tests | `./tests/test_data_loader.py` | created (task_02) |
| MCP Tools | `./src/mcp_tools.py` | created (task_03) |
| Tool Registry | `./src/tool_registry.py` | created (task_03) |
| LLM Agent | `./src/llm_agent.py` | created (task_04) |
| Eval Runner | `./src/eval_runner.py` | created (feedback-2026-05-13 follow-up) |
| LLM Agent Tests | `./tests/test_llm_agent.py` | created (task_04) |
| Eval Suite | `./evals/cbo_qa.xml` | created (feedback-2026-05-13 follow-up) |
| Eval Runner Script | `./scripts/run_eval_suite.py` | created (feedback-2026-05-13 follow-up) |
| Live Eval Adapter | `./src/eval_runner.py` | updated (`WebEvalAgent` for deployed-site evals) |
| Multi-Vintage Charting | `./src/mcp_tools.py` | updated (`vintages` / `vintage_start` filters) |
| Pytest Config | `./pytest.ini` | created (task_04) |
| Pytest Fixtures | `./tests/conftest.py` | created (task_07) |
| Eval Runner Tests | `./tests/test_eval_runner.py` | created (feedback-2026-05-13 follow-up) |
| Live Runner CLI Tests | `./tests/test_run_eval_suite.py` | updated (`--base-url` coverage) |
| CLI Entry Point | `./main.py` | created (task_05) |
| CLI Tests | `./tests/test_cli.py` | created (task_05) |
| README | `./README.md` | created (task_08) |
| Quick Start | `./QUICK_START.md` | created (task_08) |
| Env Example | `./.env.example` | created (task_08) |

## Needs Human Input

- None. All 8 sprint tasks are complete, validated, and closed out. `Next Action` is `Complete`.
