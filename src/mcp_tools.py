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
_CHART_KINDS = {"line", "bar"}


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
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
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
    loader: Optional[DataLoader] = None,
) -> tuple[Optional[pd.DataFrame], Optional[str], Optional[dict[str, Any]]]:
    """Shared filtering pipeline used by aggregation/charting tools.

    Returns ``(dataframe, year_column, error_dict)``. On any failure ``error_dict``
    is populated and the other two values are ``None``.
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
        program_col = _select_first_column(list(df.columns), _PROGRAM_COLUMNS)
        if not program_col:
            return None, None, {"error": "No program/category column found for program filter."}
        df = df[
            df[program_col]
            .astype(str)
            .str.contains(program, case=False, na=False, regex=False)
        ]

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
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
    """Aggregate a numeric metric across rows, optionally grouped.

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
    program, year_start, year_end, vintage:
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
        loader=loader,
    )
    if err is not None:
        return err
    assert df is not None

    if metric not in df.columns:
        return {"error": f"Metric column '{metric}' not found. Available: {list(df.columns)}"}

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
    }


def growth_rate(
    file_type: str,
    *,
    metric: str,
    year_start: int,
    year_end: int,
    program: Optional[str] = None,
    vintage: Optional[str] = None,
    loader: Optional[DataLoader] = None,
) -> dict[str, Any]:
    """Compute absolute change and CAGR for a metric between two years.

    Values for each endpoint year are summed across remaining rows after filters,
    so callers should narrow ``program`` (and optionally ``vintage``) when they
    want a per-program growth rate.
    """
    if year_start >= year_end:
        return {"error": "year_start must be strictly less than year_end."}

    df, year_col, err = _filtered_frame(
        file_type,
        program=program,
        year_start=year_start,
        year_end=year_end,
        vintage=vintage,
        loader=loader,
    )
    if err is not None:
        return err
    assert df is not None
    if not year_col:
        return {"error": "No supported year column found for growth calculation."}
    if metric not in df.columns:
        return {"error": f"Metric column '{metric}' not found."}

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
    }


def chart_projection(
    file_type: str,
    *,
    metric: str,
    program: Optional[str] = None,
    vintage: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    kind: str = "line",
    group_by: Optional[str] = None,
    title: Optional[str] = None,
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
    """
    kind_lower = kind.lower()
    if kind_lower not in _CHART_KINDS:
        return {"error": f"Unsupported chart kind '{kind}'. Supported: {sorted(_CHART_KINDS)}."}

    df, year_col, err = _filtered_frame(
        file_type,
        program=program,
        year_start=year_start,
        year_end=year_end,
        vintage=vintage,
        loader=loader,
    )
    if err is not None:
        return err
    assert df is not None
    if metric not in df.columns:
        return {"error": f"Metric column '{metric}' not found."}

    series = pd.to_numeric(df[metric], errors="coerce")
    chart_title = title or f"{file_type} — {metric}"
    if vintage:
        chart_title += f" (vintage {vintage})"

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
        y_label = metric

    else:  # bar
        bar_group = group_by or _select_first_column(list(df.columns), _PROGRAM_COLUMNS)
        if not bar_group:
            return {"error": "No group_by column provided and no program column found for bar chart."}
        grouped = series.groupby(df[bar_group]).sum().sort_values(ascending=False).head(15)
        labels = [str(i) for i in grouped.index]
        datasets = [{"label": f"sum({metric})", "data": [float(v) for v in grouped.values]}]
        points = [{"group": lbl, "value": float(v)} for lbl, v in zip(labels, grouped.values)]
        x_label = bar_group
        y_label = f"sum({metric})"

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
        "point_count": len(points),
        "points": points,
    }


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
