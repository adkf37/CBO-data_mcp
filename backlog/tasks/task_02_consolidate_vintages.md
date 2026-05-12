# Task 02 — Cross-Vintage Data Consolidation

**Phase:** Build 4b  
**Owner:** Backend Dev  
**Priority:** High  
**Depends on:** Task 01 (data catalog)

---

## Objective

Build a data pipeline that reads the raw CSVs for each file type and concatenates multiple vintages into a single unified DataFrame per file type, adding a `vintage` column to track the source release.

## Acceptance Criteria

- [ ] Module `src/data_loader.py` is created with a `DataLoader` class.
- [ ] `DataLoader.load_file_type(file_type: str) -> pd.DataFrame` returns a consolidated DataFrame with a `vintage` column.
- [ ] `DataLoader.list_file_types() -> list[str]` returns all available file type identifiers.
- [ ] `DataLoader.list_vintages(file_type: str) -> list[str]` returns vintages for a given file type.
- [ ] Consolidated DataFrames are cached in memory (and optionally written to `data/consolidated/<file_type>.parquet`).
- [ ] Unit tests in `tests/test_data_loader.py` cover:
  - Loading a known file type returns a non-empty DataFrame.
  - The `vintage` column is present and non-null.
  - `list_vintages` returns at least 2 vintages for a multi-vintage file type.

## Implementation Notes

- Use `pandas.concat` with `ignore_index=True`.
- Derive the `vintage` label from the filename or folder structure.
- Handle schema differences between vintages gracefully (fill missing columns with NaN).
- Use `parquet` for efficient caching (`pyarrow` or `fastparquet`).
