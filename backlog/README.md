# CBO-data_mcp — Project Background & Goals

## Background

The Congressional Budget Office (CBO) publishes detailed baseline budget projections across dozens of program areas and multiple vintages (years). While the raw data is publicly available, it is spread across ~250 CSV files and requires significant domain knowledge to navigate. Most users cannot easily query it with natural language.

**CBO-data_mcp** is an LLM-powered web app / CLI bot that makes CBO's baseline projection data accessible to anyone. It pairs Google's **Gemini 2.5 Flash** model with **Model Context Protocol (MCP)** tools so that natural-language questions are automatically routed to the right data tools, returning structured answers and optionally exporting CSV results.

Prior reference projects by the same author:
- [`chicago-zoning-mcp`](https://github.com/adkf37/chicago-zoning-mcp)
- [`Gemini_Homicide_Bot`](https://github.com/adkf37/Gemini_Homicide_Bot)

## Core Research Question / Deliverable

> **Given a natural-language question about CBO budget projections, return a precise, citation-ready answer drawn from the authoritative CBO baseline CSV data — across any vintage the user specifies.**

Example query: *"How many people are projected to be enrolled in Medicaid in 2029 according to the latest projections?"*

## Goals

1. **Catalog** the ~250 CBO CSV files, group them by the ~30 file types, and document their schemas.
2. **Consolidate** multiple vintages of each file type into a single queryable dataset to enable cross-vintage comparison.
3. **Expose MCP tools** that let an LLM call structured data functions (filter by program, year, vintage, metric).
4. **Integrate Gemini 2.5 Flash** to orchestrate tool calls and produce natural-language answers.
5. **CLI interface** for interactive querying with helpful commands (help, export, quit).
6. **CSV export** — allow any query result to be saved as a CSV file.

## Success Criteria

- [x] All ~30 CBO file types are catalogued and schemas documented.
- [x] Cross-vintage consolidated datasets are generated and queryable.
- [x] At least 5 MCP tools are implemented and tested (e.g., `search_programs`, `get_projection`, `list_vintages`, `compare_vintages`, `export_csv`).
- [x] Gemini 2.5 Flash integration responds correctly to ≥ 3 benchmark natural-language queries.
- [x] CLI boots, accepts user input, and returns answers end-to-end.
- [x] CSV export produces a valid, correctly-named file.
- [x] Unit tests cover core data-loading and tool logic.
- [x] README / QUICK_START documents how to run the bot locally.
