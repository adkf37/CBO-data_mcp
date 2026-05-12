# Task 07 — Tests and Validation

**Phase:** Build 4g / Validate  
**Owner:** Tester  
**Priority:** Medium  
**Depends on:** Tasks 01–06

---

## Objective

Write a comprehensive test suite covering unit, integration, and smoke tests for all major modules.

## Acceptance Criteria

- [ ] `tests/` directory exists with a `conftest.py` and fixtures for mock data.
- [ ] Unit tests for:
  - `test_data_loader.py` — data loading and cross-vintage consolidation
  - `test_mcp_tools.py` — all 6 MCP tools with known inputs
  - `test_csv_export.py` — CSV export correctness
  - `test_cli.py` — CLI REPL commands (using mock agent)
- [ ] Integration tests (marked `@pytest.mark.integration`) for:
  - `test_llm_agent.py` — end-to-end with 3 benchmark queries (skipped if `GEMINI_API_KEY` not set)
- [ ] All unit tests pass with `pytest tests/ -m "not integration"`.
- [ ] Test coverage report generated with `pytest --cov=src tests/`.
- [ ] A `pytest.ini` or `pyproject.toml` configures `testpaths`, `markers`, and minimum coverage threshold (≥ 70%).

## Implementation Notes

- Use `pytest` as the test runner.
- Use `unittest.mock` / `pytest-mock` for mocking the Gemini API and filesystem.
- Provide a small set of synthetic/fixture CSV files in `tests/fixtures/` so tests run without the full data repo.
- Add `pytest` and `pytest-cov` to `requirements.txt`.
