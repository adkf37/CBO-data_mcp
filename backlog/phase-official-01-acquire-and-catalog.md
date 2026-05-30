# Phase 01: Acquire Official CBO Data + Normalized Catalog

**Status:** Not Started
**Depends on:** None
**Estimated scope:** M

## Objective

Pull the official `US-CBO/cbo-data` repository into the project and build a
normalized catalog our system can consume, capturing each dataset's domain,
shape (long/wide/demographic), frequency, vintages, and per-variable metadata
(from the official `schema.json` files).

## Tasks

- [ ] Create `scripts/fetch_cbo_official.py` that clones/pulls
  `https://github.com/US-CBO/cbo-data` into `data/cbo_official/`.
  - [ ] Reuse the `clone_or_update()` pattern from `scripts/catalog_data.py`
    (depth=1 clone, `git pull --ff-only` on update, graceful failure that
    proceeds with existing vendored data).
- [ ] Create `scripts/catalog_official.py` that reads the official root
  `catalog.json` plus each dataset directory's `schema.json` and emits
  `data/official_catalog.json`.
  - [ ] For each dataset record: `dataset`, `domain` (economic|budget|demographic),
    `format` (long|spending_detail|demographic), `frequency`, `date_format`
    (quarterly|FY|CY), `vintages` (label -> file path), `description`.
  - [ ] For long/economic datasets, record per-variable metadata from `fields`:
    `description`, `unit`, `aggregation`, `source_frequency`, `category`.
  - [ ] For `spending_detail` and `demographic`, record column-level metadata
    instead of variables.
- [ ] Add `.gitignore` entries for `data/cbo_official/` raw clone if it should
  not be committed (keep `data/official_catalog.json` tracked).

## Key Files

- `scripts/fetch_cbo_official.py` — new; clone/pull official repo into `data/cbo_official/`.
- `scripts/catalog_official.py` — new; normalize official catalog + schemas into `data/official_catalog.json`.
- `data/official_catalog.json` — new generated artifact (kept separate from existing `data/catalog.json`).
- `scripts/catalog_data.py` — reference only for the `clone_or_update()` pattern.

## Acceptance Criteria

- Running `python scripts/fetch_cbo_official.py` produces `data/cbo_official/`
  with the 14 dataset directories and their CSVs.
- Running `python scripts/catalog_official.py` produces a valid
  `data/official_catalog.json` listing every dataset with format, frequency,
  vintages, and variable metadata.
- The script degrades gracefully (logs a warning, reuses existing data) when
  offline.

## Notes

- Keep the official catalog file distinct from `data/catalog.json` so the
  existing program-detail pipeline is unaffected.
- The official repo already ships `catalog.json` + `schema.json`; prefer reading
  those over re-deriving metadata from CSV headers.
