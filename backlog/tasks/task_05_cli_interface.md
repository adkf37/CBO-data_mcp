# Task 05 — Interactive CLI Interface

**Phase:** Build 4e  
**Owner:** Frontend Dev  
**Priority:** Medium  
**Depends on:** Task 04 (Gemini integration)

---

## Objective

Build a user-friendly interactive command-line interface so users can query the CBO bot, run built-in commands, and export results without writing any code.

## Acceptance Criteria

- [ ] Entry point `main.py` (or `src/cli.py`) starts an interactive REPL loop.
- [ ] The CLI displays a welcome banner with brief usage instructions on startup.
- [ ] Built-in commands are recognized and handled:
  - `/help` — print available commands and example questions
  - `/export` — export the last query result to CSV (calls `export_csv` tool)
  - `/vintages <file_type>` — list available vintages for a file type
  - `/types` — list all available CBO data file types
  - `/quit` or `/exit` — exit the bot
- [ ] Any other input is treated as a natural-language question and routed through `CBOAgent.ask()`.
- [ ] Errors (API failures, missing data) are caught and displayed as friendly messages without crashing.
- [ ] The CLI is runnable with: `python main.py`
- [ ] A smoke test in `tests/test_cli.py` verifies the REPL loop can process a mock question and a `/quit` command without error.

## Implementation Notes

- Use the built-in `readline` module (or `prompt_toolkit` for richer UX) for input.
- Color output with `colorama` or `rich` if available, but keep it optional.
- Keep each CLI response under a configurable max character width for readability.
