"""
data_loader.py — Task 02: Cross-Vintage Data Consolidation

Reads the CBO data catalog (data/catalog.json) produced by Task 01 and
consolidates multiple vintage CSV files for each file type into a single
pandas DataFrame, adding a ``vintage`` column that identifies the source release.

Usage
-----
    from src.data_loader import DataLoader

    loader = DataLoader()
    df = loader.load_file_type("medicaid")
    print(loader.list_file_types())
    print(loader.list_vintages("medicaid"))
"""

from __future__ import annotations

import json
import logging
import re
import warnings
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_DEFAULT_CATALOG = _PROJECT_ROOT / "data" / "catalog.json"
_DEFAULT_CONSOLIDATED_DIR = _PROJECT_ROOT / "data" / "consolidated"

# Same regex as catalog_data.py — strip trailing _{YYYY}_{MM} or _{YYYY}
_VINTAGE_RE = re.compile(r"^(.+?)_(\d{4})(?:_(\d{2}))?$")

# Memory guard threshold in bytes (500 MB)
_MEMORY_GUARD_BYTES = 500 * 1024 * 1024

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vintage extraction helper
# ---------------------------------------------------------------------------


def _extract_vintage(stem: str) -> Optional[str]:
    """Return the vintage string (``YYYY-MM`` or ``YYYY``) from a CSV filename stem.

    Returns ``None`` if no vintage pattern is found.
    """
    m = _VINTAGE_RE.match(stem)
    if not m:
        return None
    year = m.group(2)
    month = m.group(3)
    return f"{year}-{month}" if month else year


# ---------------------------------------------------------------------------
# DataLoader
# ---------------------------------------------------------------------------


class DataLoader:
    """Reads the CBO data catalog and consolidates multi-vintage CSV files.

    Parameters
    ----------
    catalog_path:
        Path to ``data/catalog.json``.  Defaults to the project-level file.
    consolidated_dir:
        Directory where cached ``.parquet`` files are written.
        Defaults to ``data/consolidated/``.
    """

    def __init__(
        self,
        catalog_path: Optional[Path] = None,
        consolidated_dir: Optional[Path] = None,
    ) -> None:
        self._catalog_path = Path(catalog_path) if catalog_path else _DEFAULT_CATALOG
        self._consolidated_dir = (
            Path(consolidated_dir) if consolidated_dir else _DEFAULT_CONSOLIDATED_DIR
        )

        self._catalog: list[dict] = self._load_catalog()
        # Index catalog by file_type for O(1) lookup
        self._index: dict[str, dict] = {
            entry["file_type"]: entry for entry in self._catalog
        }

        # In-memory cache: file_type -> DataFrame
        self._cache: dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # Catalog helpers
    # ------------------------------------------------------------------

    def _load_catalog(self) -> list[dict]:
        """Parse and return the catalog JSON."""
        if not self._catalog_path.exists():
            raise FileNotFoundError(
                f"Catalog not found at {self._catalog_path}. "
                "Run `python scripts/catalog_data.py` first."
            )
        with self._catalog_path.open(encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_file_types(self) -> list[str]:
        """Return all available CBO file type identifiers (sorted)."""
        return sorted(self._index.keys())

    def list_vintages(self, file_type: str) -> list[str]:
        """Return available vintage labels for *file_type* (sorted).

        Parameters
        ----------
        file_type:
            A file type identifier as returned by :meth:`list_file_types`.

        Raises
        ------
        KeyError
            If *file_type* is not present in the catalog.
        """
        if file_type not in self._index:
            raise KeyError(
                f"File type '{file_type}' not found in catalog. "
                f"Available: {self.list_file_types()}"
            )
        return sorted(self._index[file_type].get("vintages", []))

    def load_file_type(self, file_type: str) -> pd.DataFrame:
        """Return a consolidated DataFrame for *file_type* across all vintages.

        Each row carries a ``vintage`` column (``YYYY-MM`` or ``YYYY``) that
        identifies its source release.  DataFrames are cached in memory after
        the first load.  If the consolidated DataFrame exceeds 500 MB, it is
        written to parquet but **not** kept in memory.

        Parameters
        ----------
        file_type:
            A file type identifier as returned by :meth:`list_file_types`.

        Returns
        -------
        pd.DataFrame
            Consolidated DataFrame with a ``vintage`` column.

        Raises
        ------
        KeyError
            If *file_type* is not present in the catalog.
        ValueError
            If no readable CSV files are found for *file_type*.
        """
        if file_type not in self._index:
            raise KeyError(
                f"File type '{file_type}' not found in catalog. "
                f"Available: {self.list_file_types()}"
            )

        # Return cached copy if available
        if file_type in self._cache:
            log.debug("Returning cached DataFrame for '%s'.", file_type)
            return self._cache[file_type]

        # Try to load from parquet cache on disk
        parquet_path = self._consolidated_dir / f"{file_type}.parquet"
        if parquet_path.exists():
            log.info("Loading '%s' from parquet cache: %s", file_type, parquet_path)
            df = pd.read_parquet(parquet_path)
            self._maybe_cache(file_type, df)
            return df

        # Build from raw CSVs
        entry = self._index[file_type]
        file_paths: list[str] = entry.get("file_paths", [])

        if not file_paths:
            raise ValueError(
                f"No file paths recorded in catalog for file type '{file_type}'."
            )

        frames: list[pd.DataFrame] = []
        column_sets: list[frozenset] = []

        for rel_path in file_paths:
            abs_path = _PROJECT_ROOT / rel_path
            if not abs_path.exists():
                log.warning("CSV not found, skipping: %s", abs_path)
                continue

            vintage = _extract_vintage(abs_path.stem)
            if vintage is None:
                log.warning(
                    "Could not extract vintage from filename '%s'; using 'unknown'.",
                    abs_path.name,
                )
                vintage = "unknown"

            try:
                chunk = pd.read_csv(abs_path, low_memory=False)
            except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
                log.warning(
                    "Failed to read '%s' (%s: %s) — skipping.",
                    abs_path,
                    type(exc).__name__,
                    exc,
                )
                continue

            chunk = chunk.copy()
            chunk["vintage"] = vintage
            frames.append(chunk)
            column_sets.append(frozenset(chunk.columns) - {"vintage"})

        if not frames:
            raise ValueError(
                f"No readable CSV files found for file type '{file_type}'."
            )

        # Warn if schemas differ across vintages
        if len(set(column_sets)) > 1:
            log.warning(
                "Column sets differ across vintages for file type '%s'. "
                "Missing columns will be filled with NaN.",
                file_type,
            )

        consolidated = pd.concat(frames, ignore_index=True, sort=False)

        # Write parquet cache
        self._consolidated_dir.mkdir(parents=True, exist_ok=True)
        try:
            consolidated.to_parquet(parquet_path, index=False)
            log.info("Wrote parquet cache: %s", parquet_path)
        except (OSError, Exception) as exc:  # noqa: BLE001
            log.warning(
                "Could not write parquet for '%s' (%s: %s).",
                file_type,
                type(exc).__name__,
                exc,
            )

        self._maybe_cache(file_type, consolidated)
        return consolidated

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _maybe_cache(self, file_type: str, df: pd.DataFrame) -> None:
        """Cache *df* in memory only if it is smaller than the memory guard."""
        size_bytes = df.memory_usage(deep=True).sum()
        if size_bytes > _MEMORY_GUARD_BYTES:
            log.warning(
                "Consolidated DataFrame for '%s' is %.1f MB — too large to cache in memory.",
                file_type,
                size_bytes / (1024 * 1024),
            )
        else:
            self._cache[file_type] = df
