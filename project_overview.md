# CBO-data_mcp - Project Overview

Date: 2026-05-13
Status: Sprint closeout complete; project marked Complete

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

- **Completed in this loop:** Final validation and closeout for the completed sprint. Independent review reran `python -m pytest -q`, `python -m pytest tests/ -m "not integration" --cov=src --cov-report=term`, and `python -m pytest tests/test_llm_agent.py -v -o addopts=''`; the repo passed with 42 non-integration tests green, 3 expected integration deselections in the default contract, 10 LLM-agent unit tests green, and 77.51% total `src/` coverage.
- **Current repo state:** The sprint is fully implemented, validated, and closed out. The project is ready for human handoff and local use.
- **What is now available:** Cataloging (`scripts/catalog_data.py`), cross-vintage data loading (`src/data_loader.py`), MCP tools and registry (`src/mcp_tools.py`, `src/tool_registry.py`), Gemini orchestration (`src/llm_agent.py`), the interactive CLI (`main.py`), CSV export support, shared pytest fixtures/config, and root-level handoff docs (`README.md`, `QUICK_START.md`, `.env.example`).
- **Known environment limitations:** Live Gemini-backed querying still requires `GEMINI_API_KEY`, so the 3 integration tests in `tests/test_llm_agent.py` skip in offline review environments. The upstream `google.generativeai` deprecation warning remains a non-blocking future migration item.
- **Next explicit action:** `Complete` — no queued sprint tasks remain in `.squad/sprint.md`.
