# Task 08 — Documentation

**Phase:** Build 4h / Closeout  
**Owner:** Scribe  
**Priority:** Low  
**Depends on:** Tasks 01–07 (all implementation complete)

---

## Objective

Write user-facing and developer-facing documentation so that the project can be handed off, run locally, and understood by external contributors.

## Acceptance Criteria

- [ ] `README.md` at repo root includes:
  - Project description and purpose
  - Prerequisites (Python version, Gemini API key, data repo)
  - Installation steps (`pip install -r requirements.txt`)
  - How to fetch/prepare CBO data (`python scripts/catalog_data.py`)
  - How to run the CLI (`python main.py`)
  - Example questions and expected outputs
  - How to run tests
- [ ] `QUICK_START.md` provides a 5-step "zero to first answer" guide.
- [ ] Inline docstrings are present on all public classes and functions in `src/`.
- [ ] `.env.example` file shows required environment variables:
  ```
  GEMINI_API_KEY=your_key_here
  ```
- [ ] `backlog/README.md` is up to date with final success criteria checked off.

## Implementation Notes

- Use Markdown for all documentation.
- Keep the README concise — link to `docs/` or `backlog/` for deeper dives.
- Include a "Known Limitations" section noting which CBO file types may have schema inconsistencies across vintages.
