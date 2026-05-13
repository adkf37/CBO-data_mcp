# Task 07 — Tests and Validation

**Phase:** Build 4g / Validate  
**Owner:** Tester  
**Priority:** Medium  
**Depends on:** Tasks 01–06

---

## Objective

Write a comprehensive test suite covering unit, integration, and smoke tests for all major modules.

## Acceptance Criteria

- [x] `tests/` directory exists with a `conftest.py` and fixtures for mock data.
- [x] Unit tests for:
  - `test_data_loader.py` — data loading and cross-vintage consolidation
  - `test_mcp_tools.py` — all 6 MCP tools with known inputs
  - `test_csv_export.py` — CSV export correctness
  - `test_cli.py` — CLI REPL commands (using mock agent)
- [x] Integration tests (marked `@pytest.mark.integration`) for:
  - `test_llm_agent.py` — end-to-end with 3 benchmark queries (skipped if `GEMINI_API_KEY` not set)
- [x] All unit tests pass with `pytest tests/ -m "not integration"`.
- [x] Test coverage report generated with `pytest --cov=src tests/`.
- [x] A `pytest.ini` or `pyproject.toml` configures `testpaths`, `markers`, and minimum coverage threshold (≥ 70%).

## Implementation Notes

- Use `pytest` as the test runner.
- Use `unittest.mock` / `pytest-mock` for mocking the Gemini API and filesystem.
- Provide a small set of synthetic/fixture CSV files in `tests/fixtures/` so tests run without the full data repo.
- Add `pytest` and `pytest-cov` to `requirements.txt` (already present; confirm versions remain current).
- Configuration goes in `pytest.ini` (preferred) or `pyproject.toml [tool.pytest.ini_options]`. Include: `testpaths = tests`, `markers = integration: marks tests that require GEMINI_API_KEY`, and `addopts = --cov=src --cov-fail-under=70 -m "not integration"` (integration tests excluded from the default run).
- The `conftest.py` must expose at least: `sample_catalog` fixture (a minimal `data/catalog.json` dict), `sample_df` fixture (a small DataFrame with a `vintage` column), and `mock_agent` fixture (a patched `CBOAgent` that returns a canned string).
