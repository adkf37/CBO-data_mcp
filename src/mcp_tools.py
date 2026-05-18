"""
mcp_tools.py — Task 03: MCP Tools Implementation

Core data tools exposed to the LLM/tool-calling layer.
All tool outputs are JSON-serializable dict/list structures.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.data_loader import DataLoader

_PROGRAM_COLUMNS = ("program", "program_name", "category", "name")
_YEAR_COLUMNS = ("fiscal_year", "year", "calendar_year", "projection_year")
_SAFE_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_-]+")
_AGG_FUNCS = {"sum", "mean", "min", "max", "count", "median"}
_CHART_KINDS = {"line", "bar", "stacked_bar"}

# CBO publishes its baseline workbooks under product IDs (e.g. 51301 = Medicaid,
# 51302 = Medicare, 51316 = Unemployment Insurance, etc.). Filenames in the
# upstream repo follow the pattern "<product_id>-YYYY-MM-<program>.xlsx".  We
# Link back to the specific CBO xlsx on the CBO file server when we have
# enough info, falling back to the canonical landing page.
_CBO_BASELINE_LANDING = "https://www.cbo.gov/about/products/baseline-projections-selected-programs"
_CBO_FILE_BASE = "https://www.cbo.gov/system/files"
_CBO_PRODUCT_ID_RE = re.compile(r"^(\d{4,6})-")


def _build_source_citation(
    source_file: Any,
    source_sheet: Any = None,
    vintage: Any = None,
) -> dict[str, Any]:
    """Return a citation dict for a (source_file, source_sheet, vintage) tuple.

    Always includes ``source_file``; populates ``source_sheet``, ``vintage`` and
    a best-effort ``cbo_product_id`` parsed from the filename. When both
    ``vintage`` and ``source_file`` are present, ``cbo_baseline_url`` points
    directly at the xlsx on the CBO file server; otherwise it falls back to
    the canonical landing page.
    """
    citation: dict[str, Any] = {
        "source_file": str(source_file) if source_file is not None else None,
    }
    if source_sheet is not None:
        citation["source_sheet"] = str(source_sheet)
    if vintage is not None:
        citation["vintage"] = str(vintage)
    if source_file:
        match = _CBO_PRODUCT_ID_RE.match(str(source_file))
        if match:
            citation["cbo_product_id"] = match.group(1)
    # Build a direct xlsx URL when we have vintage + filename, e.g.
    # https://www.cbo.gov/system/files/2024-02/51293-2024-02-childnutrition_0.xlsx
    if source_file and vintage:
        fname = str(source_file)
        if not fname.lower().endswith(".xlsx"):
            fname = fname + ".xlsx"
        citation["cbo_baseline_url"] = f"{_CBO_FILE_BASE}/{vintage}/{fname}"
    else:
        citation["cbo_baseline_url"] = _CBO_BASELINE_LANDING
    return citation


def _collect_sources(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return deduped source citations for a filtered DataFrame slice."""
    if df is None or df.empty:
        return []
    keep = [c for c in ("source_file", "source_sheet", "vintage") if c in df.columns]
    if not keep:
        return []
    sub = df[keep].dropna(subset=["source_file"]) if "source_file" in keep else df[keep]
    if sub.empty:
        return []
    sub = sub.drop_duplicates()
    citations: list[dict[str, Any]] = []
    for row in sub.to_dict(orient="records"):
        citations.append(
            _build_source_citation(
                row.get("source_file"),
                row.get("source_sheet"),
                row.get("vintage"),
            )
        )
    return citations


def _select_first_column(columns: list[str], candidates: tuple[str, ...]) -> Optional[str]:
    lowered = {col.lower(): col for col in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def _resolve_loader(loader: Optional[DataLoader]) -> DataLoader:
    return loader if loader is not None else DataLoader()


def _sanitize_filename_component(value: Any) -> str:
    token = _SAFE_TOKEN_RE.sub("_", str(value).strip())
    return token.strip("_")


def _build_auto_filename(
    *,
    file_type: Optional[str],
    vintage: Optional[str],
    query_params: Optional[dict[str, Any]],
    exported_at: datetime,
) -> str:
    parts: list[str] = []
    if file_type:
        sanitized = _sanitize_filename_component(file_type)
        if sanitized:
            parts.append(sanitized)
    if query_params:
        for value in query_params.values():
            sanitized = _sanitize_filename_component(value)
            if sanitized:
                parts.append(sanitized)
    if vintage:
        sanitized = _sanitize_filename_component(vintage)
        if sanitized:
            parts.append(sanitized)
    if not parts:
        parts.append("cbo_export")
    timestamp = exported_at.strftime("%Y%m%d_%H%M%S")
    return "_".join(parts + [timestamp]) + ".csv"


def list_file_types(*, loader: Optional[DataLoader] = None) -> list[dict[str, Any]] | dict[str, Any]:
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
) -> dict[str, Any]:
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
    category: Optional[str] = None,
    unit: Optional[str] = None,
    include_totals: bool = True,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
    """Get projection rows filtered by file type, program, year range, vintage,
    category, and unit.

    Parameters
    ----------
    file_type:
        The CBO file type identifier.
    program:
        Optional case-insensitive substring filter for program values.
    year_start:
        Optional inclusive lower bound for year filtering.
    year_end:
        Optional inclusive upper bound for year filtering.
    vintage:
        Optional exact vintage filter (``YYYY`` or ``YYYY-MM``).
    category:
        Optional case-insensitive substring filter on the ``category`` column,
        used to isolate a specific series within a program (e.g. only the
        enrollment rows of Medicaid).
    unit:
        Optional exact case-insensitive match on the ``unit`` column. Use this
        to guarantee that the returned rows share a single unit of measure.
    loader:
        Optional pre-configured ``DataLoader`` instance.

    Returns
    -------
    dict
        On success, returns ``{"rows": list[dict], "row_count": int}``.
        On failure, returns ``{"error": "...message..."}``.
    """
    df, _year_col, err = _filtered_frame(
        file_type,
        program=program,
        year_start=year_start,
        year_end=year_end,
        vintage=vintage,
        category=category,
        unit=unit,
        include_totals=include_totals,
        loader=loader,
    )
    if err is not None:
        return err
    assert df is not None
    rows = _json_records(df)
    return {
        "rows": rows,
        "row_count": len(rows),
        "sources": _collect_sources(df),
    }


def compare_vintages(
    file_type: str,
    *,
    metric: str,
    vintage_a: str,
    vintage_b: str,
    program: Optional[str] = None,
    year: Optional[int] = None,
    category: Optional[str] = None,
    unit: Optional[str] = None,
    include_totals: bool = True,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
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
    category:
        Optional case-insensitive substring filter on the ``category`` column,
        used to isolate one series within a program before comparing vintages.
    unit:
        Optional exact case-insensitive match on the ``unit`` column so both
        vintages are compared within the same unit of measure.
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
        category=category,
        unit=unit,
        include_totals=include_totals,
        loader=loader,
    )
    second = get_projection(
        file_type,
        program=program,
        year_start=year,
        year_end=year,
        vintage=vintage_b,
        category=category,
        unit=unit,
        include_totals=include_totals,
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

    unit_err_a = _check_unit_consistency(df_a)
    if unit_err_a is not None:
        return unit_err_a
    unit_err_b = _check_unit_consistency(df_b)
    if unit_err_b is not None:
        return unit_err_b

    join_keys: list[str] = []
    year_col = _select_first_column(list(df_a.columns), _YEAR_COLUMNS)
    if year_col and year_col in df_b.columns:
        join_keys.append(year_col)
    for candidate in ("program", "program_name", "name", "category", "unit"):
        if candidate in df_a.columns and candidate in df_b.columns and candidate not in join_keys:
            join_keys.append(candidate)

    if not join_keys:
        join_keys = ["comparison_index"]
        df_a = df_a.copy()
        df_b = df_b.copy()
        df_a["comparison_index"] = range(len(df_a))
        df_b["comparison_index"] = range(len(df_b))

    merged = df_a[join_keys + [metric]].merge(
        df_b[join_keys + [metric]],
        how="outer",
        on=join_keys,
        suffixes=("_a", "_b"),
    )
    merged = merged.rename(columns={f"{metric}_a": "value_a", f"{metric}_b": "value_b"})
    merged["vintage_a"] = vintage_a
    merged["vintage_b"] = vintage_b
    rows = _json_records(merged)
    sources = (first.get("sources") or []) + (second.get("sources") or [])
    # Dedup
    seen: set[tuple] = set()
    deduped: list[dict[str, Any]] = []
    for c in sources:
        key = (c.get("source_file"), c.get("source_sheet"), c.get("vintage"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return {"rows": rows, "row_count": len(rows), "sources": deduped}


def search_programs(
    file_type: str,
    *,
    query: str,
    limit: int = 20,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
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
    file_type: Optional[str] = None,
    vintage: Optional[str] = None,
    query_params: Optional[dict[str, Any]] = None,
    source_question: Optional[str] = None,
    tool_calls: Optional[list[dict[str, Any]]] = None,
    sources: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Export query rows to CSV.

    Parameters
    ----------
    rows:
        Either a list of row dictionaries, or a dict containing a ``rows`` key.
    output_dir:
        Destination directory for the output file (created if needed).
    filename:
        Optional explicit filename. Defaults to an auto-generated filename that
        includes file type, query parameters, and timestamp.
    file_type:
        Optional dataset identifier used for metadata headers and auto filenames.
    vintage:
        Optional vintage label used for metadata headers and auto filenames.
    query_params:
        Optional query-parameter mapping used for auto filenames.
    source_question:
        Optional natural-language question that produced this export. Recorded
        in the CSV header as a provenance trail.
    tool_calls:
        Optional list of ``{"tool": str, "args": dict}`` entries describing the
        tool calls the LLM made to produce ``rows``. Recorded in the CSV header
        so reviewers can reproduce the slice.
    sources:
        Optional list of source-citation dicts (from ``_collect_sources``)
        recorded in the CSV header so each export carries the originating CBO
        workbook(s) and sheet name(s).

    Returns
    -------
    dict
        On success, ``{"file_path": str, "row_count": int}``.
        On failure, ``{"error": "...message..."}``.
    """
    if isinstance(rows, dict):
        # Allow callers to pipe a full tool result; pull provenance fields from
        # the wrapper if not supplied explicitly.
        sources = sources if sources is not None else rows.get("sources")
        rows = rows.get("rows", [])
    if not isinstance(rows, list):
        return {"error": "rows must be a list of dictionaries."}

    try:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        exported_at = datetime.now(timezone.utc)
        if filename:
            incoming = Path(filename).name
            stem = _sanitize_filename_component(Path(incoming).stem) or "cbo_export"
            safe_filename = f"{stem}.csv"
        else:
            safe_filename = _build_auto_filename(
                file_type=file_type,
                vintage=vintage,
                query_params=query_params,
                exported_at=exported_at,
            )
        out_path = out_dir / safe_filename

        metadata = {
            "file_type": file_type or "unknown",
            "vintage": vintage or "unknown",
            "export_timestamp": exported_at.isoformat(),
        }
        frame = pd.DataFrame(rows)
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            for key, value in metadata.items():
                handle.write(f"# {key}: {value}\n")
            if source_question:
                # Strip newlines so the CSV header stays single-line per field.
                cleaned = " ".join(str(source_question).split())
                handle.write(f"# source_question: {cleaned}\n")
            if tool_calls:
                for idx, call in enumerate(tool_calls, start=1):
                    name = call.get("tool") or call.get("name") or "?"
                    args = call.get("args") or {}
                    # Keep arg dump compact and one-line.
                    args_str = ", ".join(
                        f"{k}={v!r}" for k, v in args.items() if v is not None
                    )
                    handle.write(f"# tool_call_{idx}: {name}({args_str})\n")
            if sources:
                for idx, citation in enumerate(sources, start=1):
                    parts = [
                        f"source_file={citation.get('source_file')}",
                    ]
                    if citation.get("source_sheet"):
                        parts.append(f"sheet={citation.get('source_sheet')}")
                    if citation.get("vintage"):
                        parts.append(f"vintage={citation.get('vintage')}")
                    if citation.get("cbo_product_id"):
                        parts.append(f"cbo_product_id={citation.get('cbo_product_id')}")
                    handle.write(f"# source_{idx}: {' '.join(parts)}\n")
            frame.to_csv(handle, index=False)
        return {"file_path": str(out_path.resolve()), "row_count": len(rows)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to export CSV: {exc}"}


# ---------------------------------------------------------------------------
# Analytical helpers
# ---------------------------------------------------------------------------


def _filtered_frame(
    file_type: str,
    *,
    program: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    vintage: Optional[str] = None,
    category: Optional[str] = None,
    unit: Optional[str] = None,
    include_totals: bool = True,
    loader: Optional[DataLoader] = None,
) -> tuple[Optional[pd.DataFrame], Optional[str], Optional[dict[str, Any]]]:
    """Shared filtering pipeline used by aggregation/charting tools.

    Returns ``(dataframe, year_column, error_dict)``. On any failure ``error_dict``
    is populated and the other two values are ``None``.

    ``program`` matches against the first available program column (``program``
    or ``program_name``).  ``category`` matches against the ``category`` column
    specifically (so callers can filter the slice of a program — e.g. only
    enrollment rows of Medicaid).  ``unit`` does an exact case-insensitive
    match against the ``unit`` column to guarantee unit-consistent slices.

    When ``include_totals=False`` and the dataset has an ``is_total`` boolean
    column, rows marked as totals are dropped. Aggregation/charting tools pass
    ``include_totals=False`` by default to prevent double counting subtotals
    alongside their subcomponents.
    """
    if not file_type:
        return None, None, {"error": "file_type is required."}
    if year_start is not None and year_end is not None and year_start > year_end:
        return None, None, {"error": "year_start must be less than or equal to year_end."}
    try:
        dl = _resolve_loader(loader)
        df = dl.load_file_type(file_type).copy()
    except Exception as exc:  # noqa: BLE001
        return None, None, {"error": f"Failed to load '{file_type}': {exc}"}

    if vintage:
        if "vintage" not in df.columns:
            return None, None, {"error": "Dataset does not include a 'vintage' column."}
        df = df[df["vintage"] == vintage]

    if program:
        # Filter against the *program* column only (not category) so callers
        # can independently filter by category below.
        program_col = _select_first_column(list(df.columns), ("program", "program_name", "name"))
        if not program_col:
            # Fall back to category if there is no real program column.
            program_col = _select_first_column(list(df.columns), ("category",))
        if not program_col:
            return None, None, {"error": "No program/category column found for program filter."}
        df = df[
            df[program_col]
            .astype(str)
            .str.contains(program, case=False, na=False, regex=False)
        ]

    if category:
        if "category" not in df.columns:
            return None, None, {"error": "Dataset does not include a 'category' column."}
        df = df[
            df["category"]
            .astype(str)
            .str.contains(category, case=False, na=False, regex=False)
        ]

    if unit:
        if "unit" not in df.columns:
            return None, None, {"error": "Dataset does not include a 'unit' column."}
        df = df[df["unit"].astype(str).str.lower() == unit.lower()]

    if not include_totals and "is_total" in df.columns:
        # Drop subtotal/total rows so sums and charts don't double-count
        # the same dollars (e.g. "Total Mandatory Outlays" + its components).
        totals_mask = df["is_total"].astype("boolean").fillna(False)
        df = df[~totals_mask.astype(bool)]

    year_col = _select_first_column(list(df.columns), _YEAR_COLUMNS)
    if (year_start is not None or year_end is not None) and not year_col:
        return None, None, {"error": "No supported year column found for year filtering."}
    if year_col:
        numeric_years = pd.to_numeric(df[year_col], errors="coerce")
        if year_start is not None:
            df = df[numeric_years >= year_start]
        if year_end is not None:
            df = df[numeric_years <= year_end]

    return df, year_col, None


def _check_unit_consistency(df: pd.DataFrame) -> Optional[dict[str, Any]]:
    """Return an error dict if the filtered frame mixes incompatible units.

    Many CBO datasets pack outlays, enrollment counts, and per-enrollee dollar
    figures into the same file under different ``unit`` values.  Summing or
    plotting across mixed units produces nonsense, so we refuse and tell the
    caller exactly how to disambiguate.
    """
    if "unit" not in df.columns or df.empty:
        return None
    units = sorted(u for u in df["unit"].dropna().astype(str).unique() if u.strip())
    if len(units) <= 1:
        return None
    available_categories: list[str] = []
    if "category" in df.columns:
        available_categories = sorted(
            df["category"].dropna().astype(str).unique().tolist()
        )
    return {
        "error": (
            "Filtered slice mixes multiple units of measure: "
            f"{units}. Aggregating or charting across different units is not "
            "meaningful. Narrow the slice by passing `unit=` (one of the units "
            "above) or `category=` to select a specific series."
        ),
        "available_units": units,
        "available_categories": available_categories,
    }


# ---------------------------------------------------------------------------
# New analytical tools
# ---------------------------------------------------------------------------


def aggregate_metric(
    file_type: str,
    *,
    metric: str,
    agg: str = "sum",
    group_by: Optional[str] = None,
    program: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    vintage: Optional[str] = None,
    category: Optional[str] = None,
    unit: Optional[str] = None,
    include_totals: bool = False,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
    """Aggregate a numeric metric across rows, optionally grouped.

    When the filtered slice contains rows with multiple ``unit`` values the
    call is rejected (units are not commensurable). Pass ``unit=`` or
    ``category=`` to narrow the slice. Aggregations that group by ``unit``
    itself are allowed and skip the consistency check.

    Parameters
    ----------
    file_type:
        CBO file type identifier.
    metric:
        Numeric column name to aggregate.
    agg:
        One of ``sum``, ``mean``, ``min``, ``max``, ``median``, ``count``.
    group_by:
        Optional column name to group by (for example ``"fiscal_year"`` or
        ``"program"``). When omitted, returns a single overall aggregate.
    program, year_start, year_end, vintage, category, unit:
        Optional filters applied before aggregation.

    Returns
    -------
    dict
        On success either ``{"aggregate": float, "agg": str, "row_count": int}``
        (no group) or ``{"rows": [...], "agg": str, "group_by": str}`` (grouped).
        On failure ``{"error": str}``.
    """
    if not metric:
        return {"error": "metric is required."}
    agg_lower = agg.lower()
    if agg_lower not in _AGG_FUNCS:
        return {"error": f"Unsupported agg '{agg}'. Supported: {sorted(_AGG_FUNCS)}."}

    df, _year_col, err = _filtered_frame(
        file_type,
        program=program,
        year_start=year_start,
        year_end=year_end,
        vintage=vintage,
        category=category,
        unit=unit,
        include_totals=include_totals,
        loader=loader,
    )
    if err is not None:
        return err
    assert df is not None

    if metric not in df.columns:
        return {"error": f"Metric column '{metric}' not found. Available: {list(df.columns)}"}

    # Block silent cross-unit aggregation unless caller is explicitly grouping
    # by unit (which keeps results per-unit and therefore meaningful).
    if group_by != "unit" and agg_lower != "count":
        unit_err = _check_unit_consistency(df)
        if unit_err is not None:
            return unit_err

    series = pd.to_numeric(df[metric], errors="coerce")
    if group_by:
        if group_by not in df.columns:
            return {"error": f"group_by column '{group_by}' not found."}
        grouped = series.groupby(df[group_by]).agg(agg_lower)
        rows = [
            {"group": _coerce_scalar(idx), "value": _coerce_scalar(val)}
            for idx, val in grouped.items()
        ]
        return {
            "rows": rows,
            "row_count": len(rows),
            "agg": agg_lower,
            "group_by": group_by,
            "metric": metric,
            "sources": _collect_sources(df),
        }

    if agg_lower == "count":
        value: Any = int(series.notna().sum())
    else:
        value = getattr(series, agg_lower)()
        value = _coerce_scalar(value)
    return {
        "aggregate": value,
        "agg": agg_lower,
        "metric": metric,
        "row_count": int(series.notna().sum()),
        "sources": _collect_sources(df),
    }


def top_n(
    file_type: str,
    *,
    metric: str,
    n: int = 5,
    group_by: Optional[str] = None,
    agg: str = "sum",
    ascending: bool = False,
    program: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    vintage: Optional[str] = None,
    category: Optional[str] = None,
    unit: Optional[str] = None,
    include_totals: bool = False,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
    """Return the top (or bottom) N groups ranked by an aggregated metric.

    When ``group_by`` is omitted, defaults to the first available program/category
    column.
    """
    if n <= 0:
        return {"error": "n must be greater than 0."}

    df, _year_col, err = _filtered_frame(
        file_type,
        program=program,
        year_start=year_start,
        year_end=year_end,
        vintage=vintage,
        category=category,
        unit=unit,
        include_totals=include_totals,
        loader=loader,
    )
    if err is not None:
        return err
    assert df is not None

    effective_group = group_by or _select_first_column(list(df.columns), _PROGRAM_COLUMNS)
    if not effective_group:
        return {"error": "No group_by column provided and no program/category column found."}

    aggregated = aggregate_metric(
        file_type,
        metric=metric,
        agg=agg,
        group_by=effective_group,
        program=program,
        year_start=year_start,
        year_end=year_end,
        vintage=vintage,
        category=category,
        unit=unit,
        include_totals=include_totals,
        loader=loader,
    )
    if "error" in aggregated:
        return aggregated

    rows = [r for r in aggregated["rows"] if r["value"] is not None]
    rows.sort(key=lambda r: (r["value"] is None, r["value"]), reverse=not ascending)
    rows = rows[:n]
    return {
        "rows": rows,
        "row_count": len(rows),
        "metric": metric,
        "agg": agg.lower(),
        "group_by": effective_group,
        "ascending": ascending,
        "sources": aggregated.get("sources", []),
    }


def growth_rate(
    file_type: str,
    *,
    metric: str,
    year_start: int,
    year_end: int,
    program: Optional[str] = None,
    vintage: Optional[str] = None,
    category: Optional[str] = None,
    unit: Optional[str] = None,
    include_totals: bool = False,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
    """Compute absolute change and CAGR for a metric between two years.

    Values for each endpoint year are summed across remaining rows after filters,
    so callers should narrow ``program`` / ``category`` / ``unit`` to a single
    coherent series before calling.  Mixed-unit slices are rejected. By default,
    rows flagged as subtotals (``is_total=True``) are excluded so the sum does
    not double-count totals and their subcomponents.
    """
    if year_start >= year_end:
        return {"error": "year_start must be strictly less than year_end."}

    df, year_col, err = _filtered_frame(
        file_type,
        program=program,
        year_start=year_start,
        year_end=year_end,
        vintage=vintage,
        category=category,
        unit=unit,
        include_totals=include_totals,
        loader=loader,
    )
    if err is not None:
        return err
    assert df is not None
    if not year_col:
        return {"error": "No supported year column found for growth calculation."}
    if metric not in df.columns:
        return {"error": f"Metric column '{metric}' not found."}

    unit_err = _check_unit_consistency(df)
    if unit_err is not None:
        return unit_err

    numeric_years = pd.to_numeric(df[year_col], errors="coerce")
    series = pd.to_numeric(df[metric], errors="coerce")
    start_total = float(series[numeric_years == year_start].sum())
    end_total = float(series[numeric_years == year_end].sum())
    absolute_change = end_total - start_total
    if start_total == 0:
        cagr = None
        pct_change = None
    else:
        years = year_end - year_start
        cagr = (end_total / start_total) ** (1 / years) - 1 if end_total > 0 else None
        pct_change = absolute_change / start_total

    return {
        "metric": metric,
        "year_start": year_start,
        "year_end": year_end,
        "start_value": start_total,
        "end_value": end_total,
        "absolute_change": absolute_change,
        "pct_change": pct_change,
        "cagr": cagr,
        "vintage": vintage,
        "program": program,
        "sources": _collect_sources(df),
    }


def summarize_file_type(
    file_type: str,
    *,
    vintage: Optional[str] = None,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
    """Return a schema + content snapshot for a file type.

    Useful as a "discovery" tool the LLM can call before issuing aggregations on
    unfamiliar datasets.
    """
    df, year_col, err = _filtered_frame(file_type, vintage=vintage, loader=loader)
    if err is not None:
        return err
    assert df is not None

    columns_meta = [
        {"name": col, "dtype": str(df[col].dtype)} for col in df.columns
    ]
    numeric_columns = [
        col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])
    ]
    program_col = _select_first_column(list(df.columns), _PROGRAM_COLUMNS)
    top_programs: list[str] = []
    if program_col:
        top_programs = (
            df[program_col]
            .dropna()
            .astype(str)
            .value_counts()
            .head(10)
            .index.tolist()
        )
    year_range: Optional[list[int]] = None
    if year_col:
        years = pd.to_numeric(df[year_col], errors="coerce").dropna()
        if not years.empty:
            year_range = [int(years.min()), int(years.max())]
    vintages: list[str] = []
    if "vintage" in df.columns:
        vintages = sorted(df["vintage"].dropna().astype(str).unique().tolist())

    # Discovery aids: list categories and units so the LLM can pick a
    # unit-consistent slice before charting/aggregating.
    categories: list[str] = []
    if "category" in df.columns:
        categories = sorted(df["category"].dropna().astype(str).unique().tolist())
    units: list[str] = []
    if "unit" in df.columns:
        units = sorted(df["unit"].dropna().astype(str).unique().tolist())

    # For each unit, list categories that report in that unit. This is the
    # most useful breadcrumb when the user asks for a specific metric like
    # "enrollment" (Millions of people) vs "outlays" (Billions of dollars).
    categories_by_unit: dict[str, list[str]] = {}
    if "unit" in df.columns and "category" in df.columns:
        for u, sub in df.dropna(subset=["unit", "category"]).groupby("unit"):
            categories_by_unit[str(u)] = sorted(
                sub["category"].astype(str).unique().tolist()
            )

    return {
        "file_type": file_type,
        "row_count": int(len(df)),
        "columns": columns_meta,
        "numeric_columns": numeric_columns,
        "program_column": program_col,
        "year_column": year_col,
        "year_range": year_range,
        "vintages": vintages,
        "top_programs": top_programs,
        "categories": categories,
        "units": units,
        "categories_by_unit": categories_by_unit,
        "sources": _collect_sources(df),
    }


def chart_projection(
    file_type: str,
    *,
    metric: str,
    program: Optional[str] = None,
    vintage: Optional[str] = None,
    vintages: Optional[list[str]] = None,
    vintage_start: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    kind: str = "line",
    group_by: Optional[str] = None,
    title: Optional[str] = None,
    category: Optional[str] = None,
    unit: Optional[str] = None,
    include_totals: bool = False,
    loader: Optional[DataLoader] = None,
    # legacy params kept for backward-compat; no longer used
    output_dir: str = "./charts",
    filename: Optional[str] = None,
) -> dict[str, Any]:
    """Build Chart.js-compatible JSON for an interactive browser chart.

    For ``kind="line"``, one dataset per ``group_by`` value (defaults to
    ``vintage`` when present).  For ``kind="bar"``, one bar per group with
    bars sorted descending.  Returns ``chart_data`` which the web layer
    forwards to the frontend for interactive rendering with download support.

    Mixed-unit slices are rejected — pass ``unit=`` or ``category=`` to pick
    one series.  When the filtered slice resolves to a single unit, the
    chart's y-axis label automatically includes that unit.
    """
    kind_lower = kind.lower()
    if kind_lower not in _CHART_KINDS:
        return {"error": f"Unsupported chart kind '{kind}'. Supported: {sorted(_CHART_KINDS)}."}

    df, year_col, err = _filtered_frame(
        file_type,
        program=program,
        year_start=year_start,
        year_end=year_end,
        vintage=vintage if not vintages and not vintage_start else None,
        category=category,
        unit=unit,
        include_totals=include_totals,
        loader=loader,
    )
    if err is not None:
        return err
    assert df is not None
    if vintages:
        if "vintage" not in df.columns:
            return {"error": "Dataset does not include a 'vintage' column."}
        wanted = {str(item) for item in vintages}
        df = df[df["vintage"].astype(str).isin(wanted)]
    if vintage_start:
        if "vintage" not in df.columns:
            return {"error": "Dataset does not include a 'vintage' column."}
        df = df[df["vintage"].astype(str) >= vintage_start]
    if df.empty:
        return {"error": "No rows matched the chart filters."}
    if metric not in df.columns:
        return {"error": f"Metric column '{metric}' not found."}

    unit_err = _check_unit_consistency(df)
    if unit_err is not None:
        return unit_err

    # Derive a single resolved unit (if any) to label the y-axis.
    resolved_unit: Optional[str] = None
    if "unit" in df.columns and not df.empty:
        unique_units = [u for u in df["unit"].dropna().astype(str).unique() if u.strip()]
        if len(unique_units) == 1:
            resolved_unit = unique_units[0]

    series = pd.to_numeric(df[metric], errors="coerce")
    chart_title = title or f"{file_type} — {metric}"
    if category:
        chart_title += f" · {category}"
    if vintage:
        chart_title += f" (vintage {vintage})"
    if vintages:
        chart_title += f" (vintages {', '.join(str(item) for item in vintages)})"
    elif vintage_start:
        chart_title += f" (vintages since {vintage_start})"

    points: list[dict[str, Any]] = []
    datasets: list[dict[str, Any]] = []
    labels: list[Any] = []

    if kind_lower == "line":
        if not year_col:
            return {"error": "No year column available; line charts need one."}
        line_group = group_by or ("vintage" if "vintage" in df.columns else None)
        df_plot = df.assign(
            _year=pd.to_numeric(df[year_col], errors="coerce"),
            _val=series,
        ).dropna(subset=["_year", "_val"])

        if line_group and line_group in df_plot.columns:
            all_years: set[int] = set()
            grouped_series: list[tuple[str, "pd.Series"]] = []
            for lbl, grp in df_plot.groupby(line_group):
                summed = grp.groupby("_year")["_val"].sum().sort_index()
                grouped_series.append((str(lbl), summed))
                all_years.update(int(float(str(y))) for y in summed.index)
            labels = sorted(all_years)
            for lbl, summed in grouped_series:
                year_map = {int(float(str(y))): float(v) for y, v in summed.items()}
                datasets.append({
                    "label": lbl,
                    "data": [year_map.get(yr) for yr in labels],
                })
                points.extend(
                    {"group": lbl, "year": yr, "value": year_map[yr]}
                    for yr in labels if yr in year_map
                )
        else:
            summed = df_plot.groupby("_year")["_val"].sum().sort_index()
            labels = [int(float(str(y))) for y in summed.index]
            datasets = [{"label": metric, "data": [float(v) for v in summed.values]}]
            points = [{"year": yr, "value": float(v)} for yr, v in zip(labels, summed.values)]

        x_label = year_col or "year"
        if metric.strip().lower() in ("value", "values", "_val"):
            y_label = resolved_unit or ""
        else:
            y_label = f"{metric} ({resolved_unit})" if resolved_unit else metric

    elif kind_lower == "bar":
        bar_group = group_by or _select_first_column(list(df.columns), _PROGRAM_COLUMNS)
        if not bar_group:
            return {"error": "No group_by column provided and no program column found for bar chart."}
        grouped = series.groupby(df[bar_group]).sum().sort_values(ascending=False).head(15)
        labels = [str(i) for i in grouped.index]
        datasets = [{"label": f"sum({metric})", "data": [float(v) for v in grouped.values]}]
        points = [{"group": lbl, "value": float(v)} for lbl, v in zip(labels, grouped.values)]
        x_label = bar_group
        if metric.strip().lower() in ("value", "values", "_val"):
            y_label = resolved_unit or ""
        else:
            y_label = f"{metric} ({resolved_unit})" if resolved_unit else metric

    else:  # stacked_bar
        if not year_col:
            return {"error": "No year column available; stacked bar charts need one."}
        # Default: stack by program/category to show composition over time.
        # If group_by is explicitly supplied (e.g. 'vintage'), honour it.
        stack_group = group_by or _select_first_column(
            list(df.columns), _PROGRAM_COLUMNS
        ) or ("vintage" if "vintage" in df.columns else None)
        df_plot = df.assign(
            _year=pd.to_numeric(df[year_col], errors="coerce"),
            _val=series,
        ).dropna(subset=["_year", "_val"])

        if stack_group and stack_group in df_plot.columns:
            all_years_sb: set[int] = set()
            grouped_series_sb: list[tuple[str, "pd.Series"]] = []
            for lbl, grp in df_plot.groupby(stack_group):
                summed = grp.groupby("_year")["_val"].sum().sort_index()
                grouped_series_sb.append((str(lbl), summed))
                all_years_sb.update(int(float(str(y))) for y in summed.index)
            labels = sorted(all_years_sb)
            for lbl, summed in grouped_series_sb:
                year_map = {int(float(str(y))): float(v) for y, v in summed.items()}
                datasets.append({
                    "label": lbl,
                    "data": [year_map.get(yr, 0) for yr in labels],
                })
                points.extend(
                    {"group": lbl, "year": yr, "value": year_map[yr]}
                    for yr in labels if yr in year_map
                )
        else:
            summed = df_plot.groupby("_year")["_val"].sum().sort_index()
            labels = [int(float(str(y))) for y in summed.index]
            datasets = [{"label": metric, "data": [float(v) for v in summed.values]}]
            points = [{"year": yr, "value": float(v)} for yr, v in zip(labels, summed.values)]

        x_label = year_col or "year"
        if metric.strip().lower() in ("value", "values", "_val"):
            y_label = resolved_unit or ""
        else:
            y_label = f"{metric} ({resolved_unit})" if resolved_unit else metric

    chart_data: dict[str, Any] = {
        "type": kind_lower,
        "title": chart_title,
        "x_label": x_label,
        "y_label": y_label,
        "labels": labels,
        "datasets": datasets,
    }

    return {
        "chart_data": chart_data,
        "chart_kind": kind_lower,
        "metric": metric,
        "unit": resolved_unit,
        "vintage": vintage,
        "vintages": sorted(df["vintage"].dropna().astype(str).unique().tolist()) if "vintage" in df.columns else [],
        "category": category,
        "point_count": len(points),
        "points": points,
        "sources": _collect_sources(df),
    }


def _json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return DataFrame rows with pandas/numpy scalars converted for JSON tools."""
    return [
        {str(key): _coerce_scalar(value) for key, value in row.items()}
        for row in df.to_dict(orient="records")
    ]


def _coerce_scalar(value: Any) -> Any:
    """Convert pandas/numpy scalars to plain Python types for JSON-friendly output."""
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and pd.isna(value):
            return None
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            pass
    return str(value)
