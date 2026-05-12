# Work Routing

How to decide who handles what in CBO-data_mcp.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| Scope, sequencing, and trade-offs | Lead | Select next sprint slice, resolve dependencies, decide build-vs-validate transitions |
| Data cataloging and vintage consolidation | Data Engineer | `scripts/catalog_data.py`, `src/data_loader.py`, schema normalization, parquet caching |
| MCP tools and Gemini integration | Backend Dev | `src/mcp_tools.py`, `src/tool_registry.py`, `src/llm_agent.py`, API/tool loop logic |
| CLI behavior and user interaction flow | Backend Dev | `main.py`, command routing, error handling for REPL |
| Test authoring and validation evidence | Tester | `tests/`, pytest strategy, validation reports, regression checks |
| Status/history/decision updates and handoff docs | Scribe | `STATUS.md`, `.squad/decisions.md`, closeout and handoff artifact refresh |
| Code review readiness checks | Tester | Sanity review before Reviewer validation/closeout |

## Rules

1. Route each task to the single primary owner based on core domain.
2. Keep implementation aligned to `.squad/sprint.md` and `backlog/tasks/`.
3. Scribe updates logs after substantial work and does not block coding progress.
4. Reviewer remains independent for Validate/Closeout; coordinator prepares evidence.
