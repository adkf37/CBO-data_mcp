# Data Sources — CBO-data_mcp

## Primary Data Source

| Name | URL | Availability | Notes |
|---|---|---|---|
| CBO Baseline Detail CSVs | https://github.com/adkf37/Data_friendly_CBO_Baseline_Detail | ✅ Public GitHub repo | ~250 CSV files, ~30 file types, multiple vintages; `docs/` folder contains schemas |

### Data Structure (known)

- **~250 CSV files** organized by program area and vintage year.
- **~30 distinct file types** (e.g., Medicaid enrollment, discretionary spending, mandatory outlays, revenue, etc.).
- **`docs/` folder** — schema documentation explaining column definitions for each file type.
- **Multiple vintages** — each file type has releases from different CBO baseline years (e.g., Jan 2023, May 2023, Jan 2024 …).

### Access Method

Clone or HTTP-download the repository. Files will be cached locally under `data/` in this repo (excluded from git via `.gitignore`).

```
git clone https://github.com/adkf37/Data_friendly_CBO_Baseline_Detail data/raw
```

Or, if the repo is too large, individual file types can be fetched via the GitHub raw content API:

```
https://raw.githubusercontent.com/adkf37/Data_friendly_CBO_Baseline_Detail/main/<path>/<file>.csv
```

---

## LLM / API Dependencies

| Service | Endpoint | Availability | Notes |
|---|---|---|---|
| Google Gemini 2.5 Flash | `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash` | ✅ Public API (key required) | Set `GEMINI_API_KEY` env var |
| Model Context Protocol (MCP) | local in-process library | ✅ Open-source (`pip install mcp`) | Used for structured tool calling |

---

## Reference / Prior Art

| Name | URL | Purpose |
|---|---|---|
| chicago-zoning-mcp | https://github.com/adkf37/chicago-zoning-mcp | Reference MCP + Gemini integration pattern |
| Gemini_Homicide_Bot | https://github.com/adkf37/Gemini_Homicide_Bot | Reference LLM bot CLI pattern |

---

## Availability Status Summary

| Source | Status |
|---|---|
| CBO CSV data (GitHub repo) | ✅ Available — no authentication needed |
| Gemini 2.5 Flash API | ✅ Available — requires `GEMINI_API_KEY` |
| MCP Python library | ✅ Available — `pip install mcp` |
| Schema docs | ✅ Available — inside CBO data repo `docs/` folder |
