# Phase 05: Data Overlap Routing + Crosswalk

**Status:** Not Started
**Depends on:** 03, 04
**Estimated scope:** S

## Objective

Make the agent choose correctly between the existing program-detail data and the
new official datasets where they overlap, and document the relationship.

## Tasks

- [ ] Author `docs/data_crosswalk.md` mapping concepts across the two data
  families:
  - [ ] Where they overlap (new `spending_detail`/`ten_year_budget` totals vs
    existing program outlay detail) and the granularity difference.
  - [ ] Recommended source per question type (headline totals -> official;
    program category breakdowns -> existing).
- [ ] Add alias/routing guidance to `_SYSTEM_PROMPT` in `src/llm_agent.py`:
  - [ ] Term -> dataset aliases: deficit/debt held by public -> `ten_year_budget`/
    `historical_budget`; GDP/real GDP -> economic datasets; unemployment rate;
    revenue by source -> `revenue_detail`; tax brackets -> `tax_parameters`;
    Social Security trust fund -> `trust_fund`.
  - [ ] Tie-break rule when both families could answer (prefer official for
    macro/headline totals; existing for program-level category detail).
- [ ] Add a short "data families" note to `README.md` / `project_overview.md`.

## Key Files

- `docs/data_crosswalk.md` — new; concept crosswalk + source-selection guidance.
- `src/llm_agent.py` — alias + tie-break routing additions.
- `README.md`, `project_overview.md` — brief mention of the two data families.

## Acceptance Criteria

- For "What's the total deficit in 2030?" the agent uses official budget tools.
- For "Break down Medicaid enrollment by category" the agent uses the existing
  program-detail tools.
- The crosswalk doc clearly states which source to trust for overlapping metrics.

## Notes

- Keep routing guidance concise to avoid bloating the system prompt and harming
  tool selection.
