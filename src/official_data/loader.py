"""
loader.py — Read-only query layer over the official CBO DuckDB database.

``OfficialDataLoader`` wraps a lazily-opened, read-only DuckDB connection plus
the normalized ``data/official_catalog.json``.  It auto-builds the database on
first use if it is missing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

from .build import (
    DEFAULT_CATALOG,
    DEFAULT_DB_PATH,
    DEFAULT_OFFICIAL_DIR,
    build_database,
)

log = logging.getLogger(__name__)

_LONG_TABLE_BY_DOMAIN = {"economic": "economic_long", "budget": "budget_long"}


class OfficialDataLoader:
    """Query the official CBO datasets stored in DuckDB."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        catalog_path: Optional[Path] = None,
        auto_build: bool = True,
    ) -> None:
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._catalog_path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG
        self._auto_build = auto_build
        self._con: Optional[duckdb.DuckDBPyConnection] = None
        self._catalog: Optional[dict] = None
        self._index: Optional[dict] = None

    # ------------------------------------------------------------------
    # Connection / catalog
    # ------------------------------------------------------------------

    def _connection(self) -> duckdb.DuckDBPyConnection:
        if self._con is not None:
            return self._con
        if not self._db_path.exists():
            if not self._auto_build:
                raise FileNotFoundError(
                    f"{self._db_path} not found. Run "
                    "`python scripts/build_official_db.py`."
                )
            log.info("DuckDB missing; building %s …", self._db_path)
            build_database(
                catalog_path=self._catalog_path,
                official_dir=DEFAULT_OFFICIAL_DIR,
                db_path=self._db_path,
            )
        self._con = duckdb.connect(str(self._db_path), read_only=True)
        return self._con

    def _catalog_data(self) -> dict:
        if self._catalog is None:
            with self._catalog_path.open(encoding="utf-8") as fh:
                self._catalog = json.load(fh)
            self._index = {d["dataset"]: d for d in self._catalog["datasets"]}
        return self._catalog

    def _dataset_meta(self, dataset: str) -> dict:
        self._catalog_data()
        assert self._index is not None
        if dataset not in self._index:
            raise KeyError(
                f"Unknown dataset '{dataset}'. Available: "
                f"{sorted(self._index.keys())}"
            )
        return self._index[dataset]

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_datasets(self, domain: Optional[str] = None) -> list[dict]:
        catalog = self._catalog_data()
        out = []
        for ds in catalog["datasets"]:
            if domain and ds["domain"] != domain:
                continue
            out.append(
                {
                    "dataset": ds["dataset"],
                    "domain": ds["domain"],
                    "format": ds["format"],
                    "title": ds["title"],
                    "description": ds["description"],
                    "frequency": ds.get("frequency"),
                    "date_format": ds.get("date_format"),
                    "vintages": ds.get("vintages", []),
                    "publication_id": ds.get("publication_id"),
                    "landing_page": ds.get("landing_page"),
                }
            )
        return out

    def list_vintages(self, dataset: str) -> list[str]:
        return list(self._dataset_meta(dataset).get("vintages", []))

    def list_file_types(self, dataset: str) -> list[str]:
        return list(self._dataset_meta(dataset).get("file_types", []))

    def dataset_meta(self, dataset: str) -> dict:
        """Public read-only access to a dataset's normalized catalog entry."""
        return dict(self._dataset_meta(dataset))

    def list_variables(self, dataset: str) -> pd.DataFrame:
        con = self._connection()
        return con.execute(
            "SELECT variable, description, unit, category "
            "FROM variable_catalog WHERE dataset = ? ORDER BY variable",
            [dataset],
        ).df()

    def search_variables(
        self, query: str, dataset: Optional[str] = None, limit: int = 50
    ) -> pd.DataFrame:
        con = self._connection()
        like = f"%{query.lower()}%"
        sql = (
            "SELECT dataset, variable, description, unit, category "
            "FROM variable_catalog "
            "WHERE (lower(variable) LIKE ? OR lower(coalesce(description,'')) LIKE ?)"
        )
        params: list = [like, like]
        if dataset:
            sql += " AND dataset = ?"
            params.append(dataset)
        sql += " ORDER BY dataset, variable LIMIT ?"
        params.append(limit)
        return con.execute(sql, params).df()

    # ------------------------------------------------------------------
    # Long-format series
    # ------------------------------------------------------------------

    def _resolve_vintage(self, dataset: str, vintage: Optional[str]) -> Optional[str]:
        if vintage:
            return vintage
        vintages = self.list_vintages(dataset)
        return vintages[0] if vintages else None  # vintages are sorted newest-first

    def query_series(
        self,
        dataset: str,
        variables: list[str] | str,
        date_start: Optional[int] = None,
        date_end: Optional[int] = None,
        vintage: Optional[str] = None,
        estimate_type: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> pd.DataFrame:
        meta = self._dataset_meta(dataset)
        if meta["format"] != "long":
            raise ValueError(
                f"Dataset '{dataset}' is format '{meta['format']}', not long. "
                "Use query_spending() or query_demographic()."
            )
        table = _LONG_TABLE_BY_DOMAIN.get(meta["domain"])
        if table is None:
            raise ValueError(f"No long table for domain '{meta['domain']}'.")

        if isinstance(variables, str):
            variables = [variables]
        vintage = self._resolve_vintage(dataset, vintage)

        con = self._connection()
        placeholders = ", ".join(["?"] * len(variables))
        sql = (
            f"SELECT dataset, vintage, file_type, date, year, quarter, freq, basis, "
            f"variable, value, estimate_type FROM {table} "
            f"WHERE dataset = ? AND variable IN ({placeholders})"
        )
        params: list = [dataset, *variables]
        if vintage:
            sql += " AND vintage = ?"
            params.append(vintage)
        if file_type:
            sql += " AND file_type = ?"
            params.append(file_type)
        if date_start is not None:
            sql += " AND year >= ?"
            params.append(date_start)
        if date_end is not None:
            sql += " AND year <= ?"
            params.append(date_end)
        if estimate_type:
            sql += " AND estimate_type = ?"
            params.append(estimate_type)
        sql += " ORDER BY variable, year, quarter NULLS FIRST"
        return con.execute(sql, params).df()

    # ------------------------------------------------------------------
    # Spending detail (wide)
    # ------------------------------------------------------------------

    def query_spending(
        self,
        tin: Optional[str] = None,
        title_query: Optional[str] = None,
        agency: Optional[str] = None,
        function_code: Optional[str] = None,
        disc_or_mand: Optional[str] = None,
        date: Optional[str] = None,
        vintage: Optional[str] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        vintage = self._resolve_vintage("spending_detail", vintage)
        con = self._connection()
        sql = "SELECT * FROM spending_detail WHERE 1=1"
        params: list = []
        if vintage:
            sql += " AND vintage = ?"
            params.append(vintage)
        if tin:
            sql += " AND tin = ?"
            params.append(tin)
        if title_query:
            sql += " AND lower(title) LIKE ?"
            params.append(f"%{title_query.lower()}%")
        if agency:
            sql += " AND lower(agency) LIKE ?"
            params.append(f"%{agency.lower()}%")
        if function_code:
            sql += " AND CAST(function_code AS VARCHAR) = ?"
            params.append(str(function_code))
        if disc_or_mand:
            sql += " AND lower(disc_or_mand) = ?"
            params.append(disc_or_mand.lower())
        if date:
            sql += " AND date = ?"
            params.append(date)
        sql += " LIMIT ?"
        params.append(limit)
        return con.execute(sql, params).df()

    def rank_spending(
        self,
        metric: str = "outlays",
        group_by: str = "agency",
        top_n: int = 10,
        ascending: bool = False,
        date: Optional[str] = None,
        vintage: Optional[str] = None,
        disc_or_mand: Optional[str] = None,
    ) -> pd.DataFrame:
        if metric not in {"outlays", "budget_authority"}:
            raise ValueError("metric must be 'outlays' or 'budget_authority'")
        allowed_groups = {"agency", "bureau", "function_code", "title", "category"}
        if group_by not in allowed_groups:
            raise ValueError(f"group_by must be one of {sorted(allowed_groups)}")
        vintage = self._resolve_vintage("spending_detail", vintage)
        con = self._connection()
        sql = f"SELECT {group_by} AS group_key, SUM({metric}) AS total "
        sql += "FROM spending_detail WHERE 1=1"
        params: list = []
        if vintage:
            sql += " AND vintage = ?"
            params.append(vintage)
        if date:
            sql += " AND date = ?"
            params.append(date)
        if disc_or_mand:
            sql += " AND lower(disc_or_mand) = ?"
            params.append(disc_or_mand.lower())
        order = "ASC" if ascending else "DESC"
        sql += f" GROUP BY {group_by} ORDER BY total {order} LIMIT ?"
        params.append(top_n)
        return con.execute(sql, params).df()

    # ------------------------------------------------------------------
    # Demographic
    # ------------------------------------------------------------------

    def query_demographic(
        self,
        measure: str,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        vintage: Optional[str] = None,
        limit: int = 1000,
        **dimensions: object,
    ) -> pd.DataFrame:
        con = self._connection()
        vintage = self._resolve_vintage("demographic", vintage)
        sql = (
            "SELECT dataset, vintage, year, age, age_group, sex, place_of_birth, "
            "marital, immigration_status, migration_flow, measure_name, measure_value "
            "FROM demographic WHERE dataset = ?"
        )
        params: list = [measure]
        if vintage:
            sql += " AND vintage = ?"
            params.append(vintage)
        if year_start is not None:
            sql += " AND year >= ?"
            params.append(year_start)
        if year_end is not None:
            sql += " AND year <= ?"
            params.append(year_end)
        for dim, val in dimensions.items():
            if val is None:
                continue
            sql += f" AND CAST({dim} AS VARCHAR) = ?"
            params.append(str(val))
        sql += " ORDER BY year LIMIT ?"
        params.append(limit)
        return con.execute(sql, params).df()
