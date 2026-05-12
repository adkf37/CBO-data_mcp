# CBO-data_mcp - Project Overview

Date: 2026-05-12
Status: Closeout complete for task_01; next up is Build for task_02

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

- **Completed in this loop:** `task_01` cataloging is implemented and revalidated; `python scripts/catalog_data.py` regenerates `data/catalog.json` with 51 file types.
- **Current repo state:** closeout is complete for the cataloging slice, and the repo is ready to return to Build.
- **Next explicit task:** `task_02` — create `src/data_loader.py` to consolidate multi-vintage CSVs and expose file type / vintage listing methods.
