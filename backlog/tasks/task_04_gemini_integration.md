# Task 04 — Gemini 2.5 Flash Integration

**Phase:** Build 4d  
**Owner:** Backend Dev  
**Priority:** High  
**Depends on:** Task 03 (MCP tools)

---

## Objective

Wire Google Gemini 2.5 Flash to the MCP tool registry so that natural-language user queries are automatically resolved by calling the appropriate tools and returning a coherent answer.

## Acceptance Criteria

- [ ] Module `src/llm_agent.py` implements a `CBOAgent` class with:
  - `CBOAgent(api_key: str)` constructor
  - `ask(question: str) -> str` method that runs the full tool-call loop
- [ ] The agent correctly handles multi-turn tool calling (Gemini calls a tool → result is fed back → Gemini produces final answer).
- [ ] The Gemini API key is read from the `GEMINI_API_KEY` environment variable; never hardcoded.
- [ ] The agent is tested end-to-end with at least 3 benchmark queries in `tests/test_llm_agent.py` (may be marked `@pytest.mark.integration` and skipped in CI if no key is present).
- [ ] Robust JSON parsing handles edge cases in Gemini's tool-call response format.
- [ ] Logging captures each tool call name and arguments at DEBUG level.

## Benchmark Queries

1. *"How many people are projected to be enrolled in Medicaid in 2029 according to the latest projections?"*
2. *"Compare CBO's 2023 and 2024 projections for Social Security outlays in 2030."*
3. *"What are the discretionary spending categories with the largest projected growth between 2025 and 2034?"*

## Implementation Notes

- Use `google-generativeai` Python SDK (`pip install google-generativeai`).
- Register all MCP tools from `tool_registry.py` as Gemini function declarations. The registry must expose a `get_gemini_tool_declarations()` helper that returns the list of `genai.protos.Tool` objects ready to pass to `GenerativeModel`.
- Handle `FUNCTION_CALL` and `FUNCTION_RESPONSE` content parts in the conversation loop. Dispatch each function call by name through `tool_registry.py` so no hard-coded `if/elif` chains are needed.
- Cap tool-call iterations at 10 to avoid infinite loops.
- The system prompt must instruct the model to always cite the file type and vintage used when answering.
- API key must come exclusively from the `GEMINI_API_KEY` environment variable; load it with `python-dotenv` if a `.env` file is present, but never hardcode or log it.
