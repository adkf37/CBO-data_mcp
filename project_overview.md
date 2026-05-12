# CBO-data_mcp - Project Overview

Date: 2026-05-12
Status: Closeout complete for task_03; next up is Build for task_04

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

- **Completed in this loop:** `task_03` MCP tools are implemented and revalidated; `src/mcp_tools.py` and `src/tool_registry.py` compile cleanly, `python -m pytest tests/test_mcp_tools.py -q` passes 7/7 tests, and `python -m pytest -q` passes 28/28 regression tests.
- **Current repo state:** closeout is complete for the MCP-tools slice, and the repo is ready to return to Build.
- **What is now available:** Six callable MCP tools (`list_file_types`, `list_vintages`, `get_projection`, `compare_vintages`, `search_programs`, `export_csv`) plus registry helpers that expose tool lookup, tool names, and Gemini-ready function declarations for the next integration step.
- **Known gaps before project completion:** `task_04` through `task_08` remain open, including Gemini integration, CLI work, export hardening, broader test/coverage gates, and the final end-user docs (`README.md`, `QUICK_START.md`, `.env.example`).
- **Next explicit task:** `task_04` — implement `src/llm_agent.py` and wire Gemini 2.5 Flash to the MCP tool registry.
