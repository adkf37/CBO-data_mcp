"""
build.py — Ingest the vendored official CBO CSVs into a single DuckDB database.

Produces ``data/cbo_official.duckdb`` with the following tables:

- ``economic_long`` / ``budget_long`` — long format
  (dataset, vintage, file_type, date, year, quarter, freq, basis, variable,
  value, estimate_type)
- ``spending_detail`` — wide budget-account format + vintage
- ``demographic`` — generic multi-dimensional format
  (dataset, vintage, year, age, sex, place_of_birth, marital,
  immigration_status, migration_flow, measure_name, measure_value)
- ``variable_catalog`` — per-variable metadata for the long datasets
  (dataset, variable, description, unit, category, aggregation, source_frequency)

The build reads the normalized ``data/official_catalog.json`` produced by
``scripts/catalog_official.py`` and the vendored CSVs under
``data/cbo_official/``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

from .dates import parse_period

_PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_CATALOG = _PROJECT_ROOT / "data" / "official_catalog.json"
DEFAULT_OFFICIAL_DIR = _PROJECT_ROOT / "data" / "cbo_official"
DEFAULT_DB_PATH = _PROJECT_ROOT / "data" / "cbo_official.duckdb"

log = logging.getLogger(__name__)

# Known demographic dimension columns (union across file families).
_DEMO_DIMENSIONS = [
    "age",
    "age_group",
    "sex",
    "place_of_birth",
    "marital",
    "immigration_status",
    "migration_flow",
]


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


def load_catalog(catalog_path: Path) -> dict:
    if not catalog_path.exists():
        raise FileNotFoundError(
            f"{catalog_path} not found. Run "
            "`python scripts/fetch_cbo_official.py` then "
            "`python scripts/catalog_official.py` first."
        )
    with catalog_path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Per-format readers
# ---------------------------------------------------------------------------


def _read_long_file(path: Path, ds: dict, file_meta: dict) -> Optional[pd.DataFrame]:
    df = pd.read_csv(path, dtype={"date": str})
    if "variable" not in df.columns or "value" not in df.columns:
        log.debug("%s is not canonical long format; routing to demographic", path.name)
        return None

    basis = file_meta.get("date_basis", "annual")
    periods = [parse_period(d, basis) for d in df["date"]]
    out = pd.DataFrame(
        {
            "dataset": ds["dataset"],
            "vintage": file_meta.get("vintage"),
            "file_type": file_meta.get("file_type"),
            "date": df["date"].astype(str),
            "year": [p.year for p in periods],
            "quarter": [p.quarter for p in periods],
            "freq": [p.freq for p in periods],
            "basis": [p.basis for p in periods],
            "variable": df["variable"].astype(str),
            "value": pd.to_numeric(df["value"], errors="coerce"),
            "estimate_type": df["estimate_type"].astype(str)
            if "estimate_type" in df.columns
            else None,
        }
    )
    return out


def _read_spending_file(path: Path, file_meta: dict) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"date": str, "tin": str})
    df = df.copy()
    df["vintage"] = file_meta.get("vintage")
    periods = [parse_period(d, "fiscal") for d in df["date"]]
    df["year"] = [p.year for p in periods]
    return df


def _read_demographic_file(path: Path, file_meta: dict) -> pd.DataFrame:
    """Read a multi-dimensional (demographic-style) file into the generic table.

    Works for the ``demographic`` dataset files and any other multi-column file
    that has a ``year`` key plus demographic dimensions and a single measure
    column (e.g. ``long_term_economic``'s ``lfp_rates``).
    """
    # Family name = filename stem without the trailing _YYYY-MM vintage.
    stem = path.stem
    vintage = file_meta.get("vintage") or ""
    family = stem[: -(len(vintage) + 1)] if vintage and stem.endswith(vintage) else stem

    df = pd.read_csv(path)
    measure_cols = [c for c in df.columns if c not in (["year"] + _DEMO_DIMENSIONS)]
    measure_name = measure_cols[0] if measure_cols else "value"

    n = len(df)
    out = pd.DataFrame(index=range(n))
    out["dataset"] = family
    out["vintage"] = vintage
    out["year"] = pd.to_numeric(df["year"], errors="coerce") if "year" in df.columns else None
    for dim in _DEMO_DIMENSIONS:
        out[dim] = df[dim].astype(str) if dim in df.columns else None
    out["measure_name"] = measure_name
    out["measure_value"] = (
        pd.to_numeric(df[measure_name], errors="coerce") if measure_name in df.columns else None
    )
    return out


# ---------------------------------------------------------------------------
# Variable catalog
# ---------------------------------------------------------------------------


def _variable_catalog_frame(catalog: dict) -> pd.DataFrame:
    rows: list[dict] = []
    for ds in catalog["datasets"]:
        if ds.get("format") != "long":
            continue
        for var, meta in (ds.get("variables") or {}).items():
            rows.append(
                {
                    "dataset": ds["dataset"],
                    "variable": var,
                    "description": meta.get("description"),
                    "unit": meta.get("unit"),
                    "category": meta.get("category"),
                    "aggregation": meta.get("aggregation"),
                    "source_frequency": meta.get("source_frequency"),
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=[
                "dataset",
                "variable",
                "description",
                "unit",
                "category",
                "aggregation",
                "source_frequency",
            ]
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _write_table(con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> int:
    con.execute(f"DROP TABLE IF EXISTS {name}")
    con.register("_df_tmp", df)
    con.execute(f"CREATE TABLE {name} AS SELECT * FROM _df_tmp")
    con.unregister("_df_tmp")
    return len(df)


def build_database(
    catalog_path: Optional[Path] = None,
    official_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Build the DuckDB database from the vendored CSVs. Returns row-count stats."""
    catalog_path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG
    official_dir = Path(official_dir) if official_dir else DEFAULT_OFFICIAL_DIR
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH

    catalog = load_catalog(catalog_path)

    economic_long: list[pd.DataFrame] = []
    budget_long: list[pd.DataFrame] = []
    spending: list[pd.DataFrame] = []
    demographic: list[pd.DataFrame] = []

    for ds in catalog["datasets"]:
        fmt = ds.get("format")
        domain = ds.get("domain")
        for file_meta in ds.get("files", []):
            path = official_dir / file_meta["relpath"]
            if not path.exists():
                log.warning("missing file: %s", path)
                continue
            try:
                if fmt == "long":
                    frame = _read_long_file(path, ds, file_meta)
                    if frame is None:
                        # Non-canonical long file (multi-dimensional, e.g.
                        # long_term_economic/lfp_rates) -> demographic table.
                        demographic.append(_read_demographic_file(path, file_meta))
                        continue
                    (economic_long if domain == "economic" else budget_long).append(
                        frame
                    )
                elif fmt == "spending_detail":
                    spending.append(_read_spending_file(path, file_meta))
                elif fmt == "demographic":
                    demographic.append(_read_demographic_file(path, file_meta))
            except Exception as exc:  # noqa: BLE001 - log and continue per file
                log.warning("failed to read %s: %s", path, exc)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    stats: dict[str, int] = {}
    con = duckdb.connect(str(db_path))
    try:
        def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
            return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

        eco = _concat(economic_long)
        bud = _concat(budget_long)
        spd = _concat(spending)
        dem = _concat(demographic)
        varcat = _variable_catalog_frame(catalog)

        if not eco.empty:
            stats["economic_long"] = _write_table(con, "economic_long", eco)
            con.execute(
                "CREATE INDEX idx_eco ON economic_long(dataset, variable, vintage)"
            )
        if not bud.empty:
            stats["budget_long"] = _write_table(con, "budget_long", bud)
            con.execute(
                "CREATE INDEX idx_bud ON budget_long(dataset, variable, vintage)"
            )
        if not spd.empty:
            stats["spending_detail"] = _write_table(con, "spending_detail", spd)
            con.execute("CREATE INDEX idx_spd_tin ON spending_detail(tin)")
            con.execute("CREATE INDEX idx_spd_agency ON spending_detail(agency)")
        if not dem.empty:
            stats["demographic"] = _write_table(con, "demographic", dem)
            con.execute("CREATE INDEX idx_dem ON demographic(dataset, year)")
        stats["variable_catalog"] = _write_table(con, "variable_catalog", varcat)
        con.execute("CREATE INDEX idx_var ON variable_catalog(dataset, variable)")
    finally:
        con.close()

    log.info("Built %s: %s", db_path, stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    build_database()
