# FEEDBACK - CBO-data_mcp

> Drop feedback here for the project's Squad Lead to pick up.
> The Lead reads this file at the start of each work cycle.

## Format

```
### YYYY-MM-DD - [Your Name or "Human"]
Priority: [high | medium | low]
Scope: [direction | code | data | priority]

[Your feedback here]
```

## Feedback Log

### 2026-05-13 — Human
Priority: medium
Scope: code

Make sure the agent can answer somewhat complicated questions (multi-step
aggregations, rankings, growth rates), and add charting capabilities inspired
by the `Gemini_Homicide_Bot` repo. Reference `chicago-zoning-mcp` for the
multi-tool / discovery-first pattern that handles complex Q&A.

**Resolution (same day):**
- Added 5 new MCP tools: `aggregate_metric`, `top_n`, `growth_rate`,
  `summarize_file_type` (discovery), and `chart_projection` (matplotlib PNGs
  written to `./charts/`).
- `CBOAgent` now keeps a persistent chat session across `ask()` calls, exposes
  `last_trace` for tool-call introspection, and ships a strengthened
  system prompt that nudges schema discovery before aggregation.
- CLI gained `/chart`, `/reset`, and `/trace` commands.
- `matplotlib>=3.8.0` added to `requirements.txt`.
- 20 new unit tests added; full suite now 62 passed / 3 deselected /
  78.10% coverage.

_(No feedback yet - project just activated.)_
