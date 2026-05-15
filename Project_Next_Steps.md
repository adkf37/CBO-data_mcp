Differentiation ideas
Your moat isn't going to be "we have the data" — frontier models can scrape CBO. It has to be specialized analysis that's annoying to do ad-hoc, trust, and workflow integration. Concrete ideas, roughly ranked by leverage:

Tier 1 — domain-specific tools no general model has

"What changed and why" diff tool (vintage_diff_attribution): given two vintages, decompose the delta into (a) updated baseline assumptions (economic, demographic), (b) legislative changes scored between vintages, (c) technical re-estimates. CBO publishes a "Changes to Projections" appendix in every update — parse it and join. No LLM will know to do this.
Reconciliation across publications: cross-validate a number against the Budget and Economic Outlook, the Long-Term Budget Outlook, the Monthly Budget Review, and program-specific reports. Flag inconsistencies (they happen). This is your trust differentiator.
Forecast-error tracker: for every closed fiscal year, score how each historical vintage projected that year. Surface CBO's typical bias by program ("Medicare projections have been revised down by an average X% per vintage in the last 5 cycles"). Powerful and zero competitors do it.
Sensitivity / what-if: built-in shock multipliers — "What if interest rates are 100bp higher than baseline?" — using CBO's published sensitivity tables (they exist in the Budget Outlook appendix).
Composition decomposer: programmatically separate enrollment-driven vs per-capita-cost-driven growth for entitlement programs. Today the LLM can't decompose this without doing fragile multi-step math.
Tier 2 — workflow / UX

Built-in chart/table polish: chart annotations (legislation markers, recession bars), branded export presets, side-by-side small multiples for vintage comparison. Currently you have one Chart.js view.
Snapshot/share links + versioned reports: every answer becomes a citable, permalink-able page with frozen tool calls — analysts paste these in memos and Slack.
CSV export with provenance trace: already partially built; extend to "show the exact tool calls" so the output is auditable. Hill staffers and journalists care about this.
Tier 3 — combine with other datasets (highest ceiling, highest cost)

Treasury MTS / Daily Treasury Statement: actual outlays vs CBO baseline, updated daily. Lets you answer "is FY26 tracking above or below baseline?"
JCT revenue scores: pair with CBO outlay baselines for full fiscal-impact analysis.
BLS/BEA macro series for the economic assumptions side (real GDP growth, unemployment, 10Y rate).
OMB Mid-Session Review: lets users compare CBO vs administration projections — a common analyst task that nobody automates.
State-level Medicaid expenditure data (CMS-64) joined to CBO federal Medicaid totals.

Tier 4 — model/agent design

Multi-step planner: today the agent is reactive. Add a planning step for ambiguous questions ("compare Medicare spending") that enumerates which categories/units to pull and which charts to build, then executes — explicit chain-of-thought you can show the user.
Eval-driven prompt tuning: build out cbo_qa.xml with adversarial cases (the totals bug you just hit, mixed units, vintage naming traps) and run regression on every change. This is how you stay ahead of GPT-5.5 base — you optimize for this domain, they can't.
Citations with hyperlinks back to the original CBO PDF page — trivial to add since the catalog has source files, and it's the #1 thing a policy analyst will check.

My recommendation for next sprint: pick (1) vintage-diff attribution, (3) forecast-error tracker, and (15) eval expansion. Those three turn the product from "fast CBO lookup" into "the CBO analytics tool" and are defensible because they require domain plumbing the base models won't build.