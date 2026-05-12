"""
mcp_tools.py — Task 03: MCP Tools Implementation

Core data tools exposed to the LLM/tool-calling layer.
All tool outputs are JSON-serializable dict/list structures.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.data_loader import DataLoader

_PROGRAM_COLUMNS = ("program", "program_name", "category", "name")
_YEAR_COLUMNS = ("fiscal_year", "year", "calendar_year", "projection_year")


def _select_first_column(columns: list[str], candidates: tuple[str, ...]) -> Optional[str]:
    lowered = {col.lower(): col for col in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def _resolve_loader(loader: Optional[DataLoader]) -> DataLoader:
    return loader if loader is not None else DataLoader()


def list_file_types(*, loader: Optional[DataLoader] = None) -> list[dict[str, Any]] | dict[str, str]:
    """List all available CBO file types.

    Parameters
    ----------
    loader:
        Optional pre-configured ``DataLoader`` instance.

    Returns
    -------
    list[dict] | dict
        On success, returns a list of objects with ``file_type``, ``description``,
        and ``vintages`` fields. On failure, returns ``{"error": "...message..."}``.
    """
    try:
        dl = _resolve_loader(loader)
        rows: list[dict[str, Any]] = []
        for file_type in dl.list_file_types():
            entry = dl._index.get(file_type, {})
            rows.append(
                {
                    "file_type": file_type,
                    "description": entry.get("description", ""),
                    "vintages": entry.get("vintages", []),
                }
            )
        return rows
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to list file types: {exc}"}


def list_vintages(
    file_type: str, *, loader: Optional[DataLoader] = None
) -> dict[str, Any] | dict[str, str]:
    """List available vintages for a file type.

    Parameters
    ----------
    file_type:
        The CBO file type identifier (for example ``"medicaid"``).
    loader:
        Optional pre-configured ``DataLoader`` instance.

    Returns
    -------
    dict
        On success, ``{"file_type": str, "vintages": list[str]}``.
        On failure, ``{"error": "...message..."}``.
    """
    if not file_type:
        return {"error": "file_type is required."}
    try:
        dl = _resolve_loader(loader)
        return {"file_type": file_type, "vintages": dl.list_vintages(file_type)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to list vintages for '{file_type}': {exc}"}


def get_projection(
    file_type: str,
    *,
    program: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    vintage: Optional[str] = None,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any] | dict[str, str]:
    """Get projection rows filtered by file type, program, year range, and vintage.

    Parameters
    ----------
    file_type:
        The CBO file type identifier.
    program:
        Optional case-insensitive substring filter for program/category values.
    year_start:
        Optional inclusive lower bound for year filtering.
    year_end:
        Optional inclusive upper bound for year filtering.
    vintage:
        Optional exact vintage filter (``YYYY`` or ``YYYY-MM``).
    loader:
        Optional pre-configured ``DataLoader`` instance.

    Returns
    -------
    dict
        On success, returns ``{"rows": list[dict], "row_count": int}``.
        On failure, returns ``{"error": "...message..."}``.
    """
    if not file_type:
        return {"error": "file_type is required."}
    if year_start is not None and year_end is not None and year_start > year_end:
        return {"error": "year_start must be less than or equal to year_end."}

    try:
        dl = _resolve_loader(loader)
        df = dl.load_file_type(file_type).copy()

        if vintage:
            if "vintage" not in df.columns:
                return {"error": "Dataset does not include a 'vintage' column."}
            df = df[df["vintage"] == vintage]

        if program:
            program_col = _select_first_column(list(df.columns), _PROGRAM_COLUMNS)
            if not program_col:
                return {"error": "No program/category column found for program filter."}
            df = df[
                df[program_col]
                .astype(str)
                .str.contains(program, case=False, na=False, regex=False)
            ]

        year_col = _select_first_column(list(df.columns), _YEAR_COLUMNS)
        if (year_start is not None or year_end is not None) and not year_col:
            return {"error": "No supported year column found for year filtering."}
        if year_col:
            numeric_years = pd.to_numeric(df[year_col], errors="coerce")
            if year_start is not None:
                df = df[numeric_years >= year_start]
            if year_end is not None:
                df = df[numeric_years <= year_end]

        rows = df.to_dict(orient="records")
        return {"rows": rows, "row_count": len(rows)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to get projection for '{file_type}': {exc}"}


def compare_vintages(
    file_type: str,
    *,
    metric: str,
    vintage_a: str,
    vintage_b: str,
    program: Optional[str] = None,
    year: Optional[int] = None,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any] | dict[str, str]:
    """Compare one metric side-by-side for two vintages.

    Parameters
    ----------
    file_type:
        The CBO file type identifier.
    metric:
        Column name whose values should be compared.
    vintage_a:
        First vintage label (``YYYY`` or ``YYYY-MM``).
    vintage_b:
        Second vintage label (``YYYY`` or ``YYYY-MM``).
    program:
        Optional case-insensitive substring filter by program/category.
    year:
        Optional year filter applied to both vintages.
    loader:
        Optional pre-configured ``DataLoader`` instance.

    Returns
    -------
    dict
        On success, returns ``{"rows": list[dict], "row_count": int}`` where each
        row includes ``vintage_a``, ``value_a``, ``vintage_b``, and ``value_b``.
        On failure, returns ``{"error": "...message..."}``.
    """
    if not file_type:
        return {"error": "file_type is required."}
    if not metric:
        return {"error": "metric is required."}
    if not vintage_a or not vintage_b:
        return {"error": "vintage_a and vintage_b are required."}

    first = get_projection(
        file_type,
        program=program,
        year_start=year,
        year_end=year,
        vintage=vintage_a,
        loader=loader,
    )
    second = get_projection(
        file_type,
        program=program,
        year_start=year,
        year_end=year,
        vintage=vintage_b,
        loader=loader,
    )

    if "error" in first:
        return {"error": first["error"]}
    if "error" in second:
        return {"error": second["error"]}

    df_a = pd.DataFrame(first["rows"])
    df_b = pd.DataFrame(second["rows"])
    if metric not in df_a.columns or metric not in df_b.columns:
        return {"error": f"Metric column '{metric}' not found in one or both vintages."}

    key_col = _select_first_column(list(df_a.columns), _PROGRAM_COLUMNS) or "index"
    if key_col not in df_a.columns:
        df_a[key_col] = df_a.index
    if key_col not in df_b.columns:
        df_b[key_col] = df_b.index

    if year is not None and "fiscal_year" in df_a.columns:
        df_a = df_a[df_a["fiscal_year"] == year]
    if year is not None and "fiscal_year" in df_b.columns:
        df_b = df_b[df_b["fiscal_year"] == year]

    merged = df_a[[key_col, metric]].merge(
        df_b[[key_col, metric]],
        how="outer",
        on=key_col,
        suffixes=("_a", "_b"),
    )
    merged = merged.rename(
        columns={
            key_col: "program_or_category",
            f"{metric}_a": "value_a",
            f"{metric}_b": "value_b",
        }
    )
    merged["vintage_a"] = vintage_a
    merged["vintage_b"] = vintage_b
    rows = merged.to_dict(orient="records")
    return {"rows": rows, "row_count": len(rows)}


def search_programs(
    file_type: str,
    *,
    query: str,
    limit: int = 20,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any] | dict[str, str]:
    """Search program/category names in a file type.

    Parameters
    ----------
    file_type:
        The CBO file type identifier.
    query:
        Case-insensitive substring to search for.
    limit:
        Maximum number of unique matches to return.
    loader:
        Optional pre-configured ``DataLoader`` instance.

    Returns
    -------
    dict
        On success, returns ``{"matches": list[str], "match_count": int}``.
        On failure, returns ``{"error": "...message..."}``.
    """
    if not file_type:
        return {"error": "file_type is required."}
    if not query:
        return {"error": "query is required."}
    if limit <= 0:
        return {"error": "limit must be greater than 0."}

    try:
        dl = _resolve_loader(loader)
        df = dl.load_file_type(file_type)
        program_col = _select_first_column(list(df.columns), _PROGRAM_COLUMNS)
        if not program_col:
            return {"error": "No program/category column found for search."}

        mask = df[program_col].astype(str).str.contains(
            query, case=False, na=False, regex=False
        )
        values = (
            df.loc[mask, program_col]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .head(limit)
            .tolist()
        )
        return {"matches": values, "match_count": len(values)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to search programs in '{file_type}': {exc}"}


def export_csv(
    rows: list[dict[str, Any]] | dict[str, Any],
    *,
    output_dir: str = "./exports",
    filename: Optional[str] = None,
) -> dict[str, Any] | dict[str, str]:
    """Export query rows to CSV.

    Parameters
    ----------
    rows:
        Either a list of row dictionaries, or a dict containing a ``rows`` key.
    output_dir:
        Destination directory for the output file (created if needed).
    filename:
        Optional explicit filename. Defaults to ``cbo_export_<timestamp>.csv``.

    Returns
    -------
    dict
        On success, ``{"file_path": str, "row_count": int}``.
        On failure, ``{"error": "...message..."}``.
    """
    if isinstance(rows, dict):
        rows = rows.get("rows", [])
    if not isinstance(rows, list):
        return {"error": "rows must be a list of dictionaries."}

    try:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = filename or f"cbo_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        out_path = out_dir / safe_filename

        pd.DataFrame(rows).to_csv(out_path, index=False)
        return {"file_path": str(out_path.resolve()), "row_count": len(rows)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to export CSV: {exc}"}
