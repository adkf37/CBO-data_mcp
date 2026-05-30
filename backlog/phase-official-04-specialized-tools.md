# Phase 04: Specialized Tools (Spending Detail + Demographic)

**Status:** Not Started
**Depends on:** 02
**Estimated scope:** M

## Objective

Add format-aware tools for the two non-long datasets: the wide `spending_detail`
(~2,000 budget accounts) and the multi-dimensional `demographic` files.

## Tasks

- [ ] In `src/official_tools.py` add `query_budget_accounts(metric=None, tin=None,
  title_query=None, agency=None, function_code=None, disc_or_mand=None,
  group_by=None, top_n=None, date=None, vintage=None)`:
  - [ ] Lookup mode: filter by `tin`/`title_query`/`agency` and return
    `budget_authority` + `outlays` per account.
  - [ ] Ranking mode: when `top_n`/`group_by` set, aggregate by
    `agency|bureau|function_code|account` and rank by `metric`
    (`budget_authority`|`outlays`).
- [ ] Add `query_demographic(measure, year_start=None, year_end=None, age=None,
  sex=None, place_of_birth=None, immigration_status=None, migration_flow=None)`:
  - [ ] Resolve the correct file family from `measure`
    (population/fertility/mortality/migration).
  - [ ] Filter on supplied dimensions, return the measure column.
- [ ] Both tools return a `sources` citation block.
- [ ] Register both in `src/tool_registry.py`.
- [ ] Add brief usage guidance for both to `_SYSTEM_PROMPT` in `src/llm_agent.py`.

## Key Files

- `src/official_tools.py` — add `query_budget_accounts`, `query_demographic`.
- `src/official_data/loader.py` — back these with `query_spending` / `query_demographic`.
- `src/tool_registry.py` — register the two tools.
- `src/llm_agent.py` — short guidance on account/cohort queries.

## Acceptance Criteria

- "Which agency has the largest outlays in FY2026?" ranks agencies via
  `query_budget_accounts(group_by='agency', metric='outlays', top_n=...)`.
- "Find the Navy family housing construction account" returns the matching `tin`
  with `budget_authority`/`outlays`.
- "How many 16-year-old females are projected in 2030?" returns the cohort value
  via `query_demographic`.

## Notes

- `spending_detail` is wide — do NOT route it through the long-format `get_series`.
- Demographic key columns differ by file family; resolve columns per `measure`.
