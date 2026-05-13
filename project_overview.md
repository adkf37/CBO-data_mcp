# CBO-data_mcp - Project Overview

Date: 2026-05-13
Status: Closeout complete for task_06; next up is Build for task_07

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

- **Completed in this loop:** `task_06` CSV export closeout is complete. Independent review reran `python -m pytest -q` and `python -m pytest tests/ -m "not integration" --cov=src --cov-report=term`; the repo passed with 42 tests green, 3 expected integration skips, and 78% total `src/` coverage.
- **Current repo state:** the CSV export slice is implemented, validated, and closed out, and the repo is ready to return to Build.
- **What is now available:** `src/mcp_tools.py` now writes metadata-commented CSV exports with sanitized auto-generated filenames and auto-created export directories; `main.py` `/export` remains wired to the enhanced export path; the repo already has targeted tests for data loading, MCP tools, Gemini orchestration, CLI behavior, and CSV export behavior.
- **Known gaps before project completion:** `task_07` and `task_08` remain open. The repo still needs `tests/conftest.py` plus fuller `pytest.ini` defaults to satisfy the testing contract, and the root-level end-user docs (`README.md`, `QUICK_START.md`, `.env.example`) are still absent.
- **Known environment limitations:** Live Gemini-backed querying still requires `GEMINI_API_KEY`, so the 3 integration tests in `tests/test_llm_agent.py` continue to skip in offline review environments. The upstream `google.generativeai` deprecation warning remains a non-blocking future migration item.
- **Next explicit task:** `task_07` — finish the repository-wide testing contract by adding `tests/conftest.py` fixtures and completing the `pytest.ini` defaults while preserving the passing non-integration and coverage runs.
