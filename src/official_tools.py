"""
official_tools.py — MCP tools for the official US-CBO/cbo-data datasets.

A parallel, format-aware tool surface that complements the existing
program-detail tools in ``src/mcp_tools.py``.  These tools cover the official
CBO economic, budget, and demographic datasets stored in DuckDB
(``data/cbo_official.duckdb``) via :class:`OfficialDataLoader`.

Design mirrors ``src/mcp_tools.py``: every tool returns JSON-friendly records
plus a deduped ``sources`` citation block, and ``chart_series`` emits the same
``chart_data`` payload shape consumed by the web UI.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

from src.mcp_tools import _coerce_scalar, _json_records
from src.official_data.loader import OfficialDataLoader

log = logging.getLogger(__name__)

# Preference order when a dataset offers several frequencies and the caller did
# not pin one. Annual fiscal-year views are the most common ask.
_FILE_TYPE_PRIORITY = [
    "annual_fy",
    "fiscal",
    "annual_cy",
    "calendar",
    "annual",
    "quarterly",
]

# Module-level lazy singleton so the DuckDB connection is shared across calls.
_LOADER: Optional[OfficialDataLoader] = None


def _loader() -> OfficialDataLoader:
    global _LOADER
    if _LOADER is None:
        _LOADER = OfficialDataLoader()
    return _LOADER


def set_loader(loader: OfficialDataLoader) -> None:
    """Inject a loader (used by tests)."""
    global _LOADER
    _LOADER = loader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_file_type(loader: OfficialDataLoader, dataset: str) -> Optional[str]:
    available = loader.list_file_types(dataset)
    if not available:
        return None
    for pref in _FILE_TYPE_PRIORITY:
        if pref in available:
            return pref
    return available[0]


def _official_sources(
    loader: OfficialDataLoader, dataset: str, vintage: Optional[str], file_type: Optional[str]
) -> list[dict[str, Any]]:
    """Build a citation block pointing at the official repo + CBO publication."""
    try:
        meta = loader.dataset_meta(dataset)
    except KeyError:
        return []
    vintage = vintage or (meta.get("vintages") or [None])[0]
    files = meta.get("files", [])
    chosen = None
    for f in files:
        if f.get("vintage") == vintage and (not file_type or f.get("file_type") == file_type):
            chosen = f
            break
    if chosen is None and files:
        chosen = next((f for f in files if f.get("vintage") == vintage), files[0])
    src: dict[str, Any] = {
        "dataset": dataset,
        "vintage": vintage,
        "cbo_publication_id": meta.get("publication_id"),
        "cbo_landing_page": meta.get("landing_page"),
        "source_repo": "https://github.com/US-CBO/cbo-data",
    }
    if chosen:
        src["source_file"] = chosen.get("relpath")
        src["raw_url"] = chosen.get("raw_url")
    return [src]


def _var_meta(loader: OfficialDataLoader, dataset: str, variable: str) -> dict[str, Any]:
    df = loader.list_variables(dataset)
    if df.empty:
        return {}
    hit = df[df["variable"] == variable]
    if hit.empty:
        return {}
    row = hit.iloc[0]
    return {
        "variable": variable,
        "description": _coerce_scalar(row.get("description")),
        "unit": _coerce_scalar(row.get("unit")),
        "category": _coerce_scalar(row.get("category")),
    }


# ---------------------------------------------------------------------------
# Discovery tools
# ---------------------------------------------------------------------------


def list_official_datasets(domain: Optional[str] = None) -> dict[str, Any]:
    """List the official CBO datasets (economic / budget / demographic)."""
    loader = _loader()
    datasets = loader.list_datasets(domain=domain)
    return {"count": len(datasets), "domain": domain, "datasets": datasets}


def summarize_official_dataset(
    dataset: str, vintage: Optional[str] = None
) -> dict[str, Any]:
    """Describe one official dataset: format, frequency, vintages, and variables.

    This is the discovery tool to call first when you are unsure which variable
    name or vintage to use.
    """
    loader = _loader()
    try:
        meta = loader.dataset_meta(dataset)
    except KeyError as exc:
        return {"error": str(exc)}

    out: dict[str, Any] = {
        "dataset": dataset,
        "domain": meta.get("domain"),
        "format": meta.get("format"),
        "title": meta.get("title"),
        "description": meta.get("description"),
        "frequency": meta.get("frequency"),
        "date_format": meta.get("date_format"),
        "file_types": meta.get("file_types"),
        "vintages": meta.get("vintages"),
        "notes": meta.get("notes"),
        "landing_page": meta.get("landing_page"),
    }
    if meta.get("format") == "long":
        var_df = loader.list_variables(dataset)
        out["variable_count"] = len(var_df)
        out["variables_sample"] = _json_records(var_df.head(40))
    elif meta.get("format") == "demographic":
        out["domains"] = meta.get("domains")
    elif meta.get("format") == "spending_detail":
        out["columns"] = meta.get("columns")
    out["sources"] = _official_sources(loader, dataset, vintage, None)
    return out


def search_variables(
    query: str, dataset: Optional[str] = None, limit: int = 50
) -> dict[str, Any]:
    """Search official variable names + descriptions (e.g. 'unemployment', 'deficit')."""
    loader = _loader()
    df = loader.search_variables(query, dataset=dataset, limit=limit)
    return {"query": query, "dataset": dataset, "count": len(df), "matches": _json_records(df)}


# ---------------------------------------------------------------------------
# Long-format series tools
# ---------------------------------------------------------------------------


def get_series(
    dataset: str,
    variables: list[str] | str,
    date_start: Optional[int] = None,
    date_end: Optional[int] = None,
    vintage: Optional[str] = None,
    estimate_type: Optional[str] = None,
    file_type: Optional[str] = None,
) -> dict[str, Any]:
    """Retrieve one or more long-format series (date, variable, value).

    ``date_start`` / ``date_end`` are 4-digit years. ``file_type`` selects the
    frequency view (e.g. 'quarterly', 'fiscal', 'calendar'); when omitted an
    annual view is preferred. ``estimate_type`` can be 'actual' or 'projected'.
    """
    loader = _loader()
    try:
        meta = loader.dataset_meta(dataset)
    except KeyError as exc:
        return {"error": str(exc)}
    if meta.get("format") != "long":
        return {
            "error": (
                f"Dataset '{dataset}' is '{meta.get('format')}' format. Use "
                "query_budget_accounts (spending_detail) or query_demographic."
            )
        }
    if isinstance(variables, str):
        variables = [variables]
    if file_type is None:
        file_type = _default_file_type(loader, dataset)
    vintage = vintage or (meta.get("vintages") or [None])[0]

    df = loader.query_series(
        dataset,
        variables,
        date_start=date_start,
        date_end=date_end,
        vintage=vintage,
        estimate_type=estimate_type,
        file_type=file_type,
    )
    if df.empty:
        return {
            "dataset": dataset,
            "variables": variables,
            "vintage": vintage,
            "file_type": file_type,
            "row_count": 0,
            "rows": [],
            "note": (
                "No rows. Call summarize_official_dataset or search_variables to "
                "confirm the variable name, vintage, and file_type."
            ),
        }
    var_meta = {v: _var_meta(loader, dataset, v) for v in variables}
    return {
        "dataset": dataset,
        "variables": variables,
        "variable_metadata": var_meta,
        "vintage": vintage,
        "file_type": file_type,
        "row_count": len(df),
        "rows": _json_records(df),
        "sources": _official_sources(loader, dataset, vintage, file_type),
    }


def compare_official_vintages(
    dataset: str,
    variable: str,
    vintage_a: str,
    vintage_b: str,
    date_start: Optional[int] = None,
    date_end: Optional[int] = None,
    file_type: Optional[str] = None,
) -> dict[str, Any]:
    """Compare one variable across two vintages (e.g. how the deficit projection moved)."""
    loader = _loader()
    try:
        meta = loader.dataset_meta(dataset)
    except KeyError as exc:
        return {"error": str(exc)}
    if meta.get("format") != "long":
        return {"error": f"compare_official_vintages supports long datasets only, not '{meta.get('format')}'."}
    if file_type is None:
        file_type = _default_file_type(loader, dataset)

    def _frame(v: str) -> pd.DataFrame:
        return loader.query_series(
            dataset, [variable], date_start=date_start, date_end=date_end,
            vintage=v, file_type=file_type,
        )[["date", "year", "value"]]

    a = _frame(vintage_a).rename(columns={"value": f"value_{vintage_a}"})
    b = _frame(vintage_b).rename(columns={"value": f"value_{vintage_b}"})
    merged = pd.merge(a, b, on=["date", "year"], how="outer").sort_values("year")
    if not merged.empty:
        merged["delta"] = merged[f"value_{vintage_b}"] - merged[f"value_{vintage_a}"]
    return {
        "dataset": dataset,
        "variable": variable,
        "vintage_a": vintage_a,
        "vintage_b": vintage_b,
        "file_type": file_type,
        "unit": _var_meta(loader, dataset, variable).get("unit"),
        "row_count": len(merged),
        "rows": _json_records(merged),
        "sources": (
            _official_sources(loader, dataset, vintage_a, file_type)
            + _official_sources(loader, dataset, vintage_b, file_type)
        ),
    }


def series_growth_rate(
    dataset: str,
    variable: str,
    date_start: int,
    date_end: int,
    vintage: Optional[str] = None,
    file_type: Optional[str] = None,
) -> dict[str, Any]:
    """Absolute change, percent change, and CAGR for a variable between two years."""
    loader = _loader()
    try:
        meta = loader.dataset_meta(dataset)
    except KeyError as exc:
        return {"error": str(exc)}
    if meta.get("format") != "long":
        return {"error": f"series_growth_rate supports long datasets only, not '{meta.get('format')}'."}
    if file_type is None:
        file_type = _default_file_type(loader, dataset)
    vintage = vintage or (meta.get("vintages") or [None])[0]

    df = loader.query_series(
        dataset, [variable], date_start=date_start, date_end=date_end,
        vintage=vintage, file_type=file_type,
    )
    if df.empty:
        return {"error": f"No data for {variable} in {dataset} ({vintage})."}

    def _val(year: int) -> Optional[float]:
        sub = df[df["year"] == year]["value"].dropna()
        return float(sub.mean()) if not sub.empty else None

    start_val, end_val = _val(date_start), _val(date_end)
    if start_val is None or end_val is None:
        return {"error": f"Missing endpoint value(s) for years {date_start}/{date_end}."}

    span = max(date_end - date_start, 0)
    abs_change = end_val - start_val
    pct_change = (abs_change / start_val * 100) if start_val else None
    cagr = (
        ((end_val / start_val) ** (1 / span) - 1) * 100
        if span > 0 and start_val > 0 and end_val > 0
        else None
    )
    return {
        "dataset": dataset,
        "variable": variable,
        "vintage": vintage,
        "file_type": file_type,
        "unit": _var_meta(loader, dataset, variable).get("unit"),
        "year_start": date_start,
        "year_end": date_end,
        "value_start": start_val,
        "value_end": end_val,
        "absolute_change": abs_change,
        "percent_change": pct_change,
        "cagr_percent": cagr,
        "sources": _official_sources(loader, dataset, vintage, file_type),
    }


def chart_series(
    dataset: str,
    variable: str,
    vintage: Optional[str] = None,
    vintages: Optional[list[str]] = None,
    date_start: Optional[int] = None,
    date_end: Optional[int] = None,
    kind: str = "line",
    file_type: Optional[str] = None,
    title: Optional[str] = None,
) -> dict[str, Any]:
    """Build a Chart.js ``chart_data`` payload for an official long-format series.

    Pass ``vintages`` to overlay multiple releases of the same variable.
    """
    loader = _loader()
    try:
        meta = loader.dataset_meta(dataset)
    except KeyError as exc:
        return {"error": str(exc)}
    if meta.get("format") != "long":
        return {"error": f"chart_series supports long datasets only, not '{meta.get('format')}'."}
    if file_type is None:
        file_type = _default_file_type(loader, dataset)

    vmeta = _var_meta(loader, dataset, variable)
    unit = vmeta.get("unit")
    kind_lower = (kind or "line").lower()

    vintage_list = vintages or [vintage or (meta.get("vintages") or [None])[0]]
    all_dates: list[str] = []
    datasets_payload: list[dict[str, Any]] = []
    points: list[dict[str, Any]] = []
    used_vintages: list[str] = []

    for v in vintage_list:
        df = loader.query_series(
            dataset, [variable], date_start=date_start, date_end=date_end,
            vintage=v, file_type=file_type,
        )
        if df.empty:
            continue
        used_vintages.append(str(v))
        for d in df["date"].astype(str):
            if d not in all_dates:
                all_dates.append(d)
        label = f"{variable} ({v})" if len(vintage_list) > 1 else variable
        date_to_val = {str(r.date): _coerce_scalar(r.value) for r in df.itertuples()}
        datasets_payload.append({"label": label, "_map": date_to_val})
        points.extend(
            {"vintage": str(v), "date": str(r.date), "value": _coerce_scalar(r.value)}
            for r in df.itertuples()
        )

    if not datasets_payload:
        return {"error": f"No data to chart for {variable} in {dataset}."}

    # Order x-axis by (year, quarter) parsed from the date strings.
    def _date_key(d: str) -> tuple[int, int]:
        import re as _re
        m = _re.match(r"(?:FY|CY)?(\d{4})(?:[qQ]([1-4]))?", d)
        if not m:
            return (0, 0)
        return (int(m.group(1)), int(m.group(2)) if m.group(2) else 0)

    labels = sorted(all_dates, key=_date_key)
    for ds_payload in datasets_payload:
        dmap = ds_payload.pop("_map")
        ds_payload["data"] = [dmap.get(lbl) for lbl in labels]

    y_label = f"{variable} ({unit})" if unit else variable
    chart_title = title or f"{meta.get('title', dataset)}: {variable}"

    chart_data = {
        "type": kind_lower,
        "title": chart_title,
        "x_label": meta.get("date_format") or "date",
        "y_label": y_label,
        "labels": labels,
        "datasets": datasets_payload,
    }
    sources: list[dict[str, Any]] = []
    for v in used_vintages:
        sources.extend(_official_sources(loader, dataset, v, file_type))
    return {
        "chart_data": chart_data,
        "chart_kind": kind_lower,
        "dataset": dataset,
        "variable": variable,
        "unit": unit,
        "vintages": used_vintages,
        "file_type": file_type,
        "point_count": len(points),
        "points": points,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Specialized format tools (spending_detail + demographic)
# ---------------------------------------------------------------------------


def query_budget_accounts(
    metric: Optional[str] = None,
    tin: Optional[str] = None,
    title_query: Optional[str] = None,
    agency: Optional[str] = None,
    function_code: Optional[str] = None,
    disc_or_mand: Optional[str] = None,
    group_by: Optional[str] = None,
    top_n: Optional[int] = None,
    date: Optional[str] = None,
    vintage: Optional[str] = None,
) -> dict[str, Any]:
    """Query the wide ``spending_detail`` dataset (~2,000 budget accounts).

    Two modes:
    - Lookup: filter by ``tin`` / ``title_query`` / ``agency`` to read an
      account's ``budget_authority`` and ``outlays``.
    - Ranking: set ``group_by`` (agency|bureau|function_code|title|category) and
      ``top_n`` with ``metric`` (outlays|budget_authority) to rank.
    ``date`` is a fiscal-year label like 'FY2026'.
    """
    loader = _loader()
    if group_by or top_n:
        try:
            df = loader.rank_spending(
                metric=metric or "outlays",
                group_by=group_by or "agency",
                top_n=top_n or 10,
                date=date,
                vintage=vintage,
                disc_or_mand=disc_or_mand,
            )
        except ValueError as exc:
            return {"error": str(exc)}
        return {
            "mode": "ranking",
            "metric": metric or "outlays",
            "group_by": group_by or "agency",
            "date": date,
            "row_count": len(df),
            "rows": _json_records(df),
            "unit": "Millions of dollars",
            "sources": _official_sources(loader, "spending_detail", vintage, None),
        }

    df = loader.query_spending(
        tin=tin, title_query=title_query, agency=agency,
        function_code=function_code, disc_or_mand=disc_or_mand,
        date=date, vintage=vintage,
    )
    return {
        "mode": "lookup",
        "filters": {
            "tin": tin, "title_query": title_query, "agency": agency,
            "function_code": function_code, "disc_or_mand": disc_or_mand, "date": date,
        },
        "row_count": len(df),
        "rows": _json_records(df),
        "unit": "Millions of dollars",
        "sources": _official_sources(loader, "spending_detail", vintage, None),
    }


def query_demographic(
    measure: str,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    age: Optional[str] = None,
    sex: Optional[str] = None,
    place_of_birth: Optional[str] = None,
    immigration_status: Optional[str] = None,
    migration_flow: Optional[str] = None,
    vintage: Optional[str] = None,
) -> dict[str, Any]:
    """Look up demographic cohorts (population_bls, population_census, fertility,
    mortality, migration, ss_area_population, lfp_rates).

    ``measure`` is the file family; remaining args filter the demographic
    dimensions. Returns the measure value (e.g. number_of_people).
    """
    loader = _loader()
    dims = {
        "age": age,
        "sex": sex,
        "place_of_birth": place_of_birth,
        "immigration_status": immigration_status,
        "migration_flow": migration_flow,
    }
    df = loader.query_demographic(
        measure, year_start=year_start, year_end=year_end, vintage=vintage, **dims,
    )
    # Drop all-null dimension columns for a cleaner payload.
    if not df.empty:
        df = df.dropna(axis=1, how="all")
    return {
        "measure": measure,
        "filters": {k: v for k, v in dims.items() if v is not None},
        "year_start": year_start,
        "year_end": year_end,
        "row_count": len(df),
        "rows": _json_records(df),
        "sources": _official_sources(loader, "demographic", vintage, None),
    }
