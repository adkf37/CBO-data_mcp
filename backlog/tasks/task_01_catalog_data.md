# Task 01 — Catalog CBO Data Repository

**Phase:** Build 4a  
**Owner:** Data Engineer  
**Priority:** High (blocker for all subsequent tasks)  
**Depends on:** None

---

## Objective

Clone (or programmatically fetch) the CBO baseline detail data repository and produce a machine-readable catalog of all CSV file types, their schemas, and available vintages.

## Data Source

```
https://github.com/adkf37/Data_friendly_CBO_Baseline_Detail
```

- ~250 CSV files
- ~30 distinct file types
- `docs/` folder contains schema documentation

## Acceptance Criteria

- [x] A script `scripts/catalog_data.py` clones/updates the data repo into `data/raw/`.
- [x] The script produces `data/catalog.json` with entries for each unique file type, listing:
  - `file_type` (string identifier)
  - `description` (from `docs/` schema)
  - `columns` (list of column names and types)
  - `vintages` (list of available release years/dates)
  - `file_paths` (list of matching CSV file paths)
- [x] At least 25 of the ~30 file types are catalogued.
- [x] Script runs without errors: `python scripts/catalog_data.py`
- [x] `data/raw/` and `data/catalog.json` are excluded from git (added to `.gitignore`).

## Implementation Notes

- Group files by naming pattern (e.g., `medicaid_enrollment_*.csv`).
- Parse the `docs/` schema markdown/CSV to extract column definitions. If the `docs/` folder uses mixed formats (markdown and CSV), detect the format per file and handle each accordingly.
- Store vintage info from filenames or embedded metadata. Canonical vintage format: `YYYY-MM` (e.g., `2024-01`). Fall back to `YYYY` if no month is determinable.
- Use `pandas` for CSV inspection and `pathlib` for file traversal.
- If `data/raw/` already exists, perform a `git pull` update instead of a fresh clone.
- If network access is unavailable, the script should log a warning and proceed with whatever data is already present in `data/raw/`.
