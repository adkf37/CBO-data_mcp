# CBO-data_mcp - Project Overview

Date: 2026-05-13
Status: Closeout complete for task_05; next up is Build for task_06

## Purpose

CBO-data_mcp is llm-powered system that makes access to CBO data more accessible for most users. The use of MCP plus an llm makes the system more deterministic and easy to update as models change. This project integrates Google's Gemini 2.5 Flash with **Model Context Protocol (MCP)** tools for intelligent querying of CBO's data. The system allows users to ask natural language questions about data and the llm automatically calls appropriate data analysis tools.

- **Intelligent Tool Calling**: Ask natural questions like "How many people are projected to be enrolled in Medicaid in 2029 according to the latest projections" and the LLM automatically calls the right tools
- **MCP Integration**: Uses Model Context Protocol for structured tool calling and data access  
- **Gemini 2.5 Flash Integration**: Uses Google's Gemini 2.5 Flash API for higher-quality responses
- **Interactive CLI**: User-friendly command-line interface with helpful commands
- **Robust Parsing**: Advanced JSON parsing for reliable tool call extraction
- **Rich Data Extraction**: export csv files of source data that respond to natural language queries

## Resources

CBO_data: https://github.com/adkf37/Data_friendly_CBO_Baseline_Detail

Prior mcp projects:
https://github.com/adkf37/chicago-zoning-mcp
https://github.com/adkf37/Gemini_Homicide_Bot

## Steps and Scope of CBO Data Analysis

- There are around 250 csv files in the repository. 
- There are around 30 types of files with multiple vintages
- The docs folder has schemas that explain the data.
- We should string together multiple vintages worth of data to more easily allow for cross vintage comparison

## Current Handoff Snapshot

- **Completed in this loop:** `task_05` interactive CLI closeout is complete. Independent review reran `python -m py_compile main.py`, `printf '/quit\n' | python main.py`, `python -m pytest tests/test_cli.py -q`, and `python -m pytest -q`; the CLI started cleanly, exited cleanly on `/quit`, task-specific tests passed (2/2), and the full suite passed with 40 tests green and 3 expected integration skips.
- **Current repo state:** the CLI slice is implemented, validated, and closed out, and the repo is ready to return to Build.
- **What is now available:** `main.py` provides a REPL with `/help`, `/types`, `/vintages <file_type>`, `/export [filename]`, and `/quit`/`/exit`; natural-language questions route through `CBOAgent.ask()` when `GEMINI_API_KEY` is configured; the CLI also preserves session state so `/export` can use the last query result without rerunning it.
- **Known gaps before project completion:** `task_06` through `task_08` remain open, including full CSV-export naming/metadata/directory handling, the broader test-and-coverage deliverables, and the final end-user docs (`README.md`, `QUICK_START.md`, `.env.example`).
- **Known environment limitations:** Live Gemini-backed querying still requires `GEMINI_API_KEY`, so the 3 integration tests in `tests/test_llm_agent.py` continue to skip in offline review environments. The upstream `google.generativeai` deprecation warning remains a non-blocking future migration item.
- **Next explicit task:** `task_06` — replace the current `export_csv` stub with the full CSV export implementation and wire the CLI `/export` output to the finalized path/metadata behavior.
