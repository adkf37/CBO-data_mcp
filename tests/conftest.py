from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pytest


@pytest.fixture()
def sample_catalog() -> dict[str, list[dict[str, object]]]:
    """Minimal catalog-like structure for tests that need synthetic metadata."""
    return {
        "entries": [
            {
                "file_type": "medicaid",
                "description": "Medicaid projections.",
                "columns": ["program", "fiscal_year", "value", "vintage"],
                "vintages": ["2024-01"],
                "file_paths": ["data/raw/data/processed/medicaid_2024_01.csv"],
            }
        ]
    }


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Small synthetic projection dataset with the required vintage column."""
    return pd.DataFrame(
        [
            {
                "program": "Medicaid",
                "fiscal_year": 2029,
                "value": 110.0,
                "vintage": "2024-01",
            }
        ]
    )


@dataclass
class _MockAgent:
    response: str = "Mocked CBO response"

    def ask(self, question: str) -> str:
        return self.response


@pytest.fixture()
def mock_agent(monkeypatch) -> _MockAgent:
    """Patched CBOAgent fixture returning a canned answer for CLI/agent tests."""
    agent = _MockAgent()

    monkeypatch.setattr("src.llm_agent.CBOAgent", lambda *args, **kwargs: agent)
    monkeypatch.setattr("main.CBOAgent", lambda *args, **kwargs: agent)

    return agent


# ---------------------------------------------------------------------------
# Official US-CBO/cbo-data fixtures (offline synthetic DuckDB)
# ---------------------------------------------------------------------------

import json as _json
from pathlib import Path as _Path


def _write_official_tree(root: _Path) -> tuple[_Path, _Path]:
    """Create a tiny synthetic official-data tree and return (catalog, official_dir)."""
    official_dir = root / "cbo_official"
    raw_base = "https://raw.githubusercontent.com/US-CBO/cbo-data/main"

    def _csv(relpath: str, text: str) -> None:
        p = official_dir / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    # 1) economic long (fiscal annual)
    _csv(
        "data/economic/economic_projections/fiscal_2026-02.csv",
        "date,variable,value,estimate_type\n"
        "2023,unemployment_rate,3.6,actual\n"
        "2024,unemployment_rate,4.0,projected\n"
        "2025,unemployment_rate,4.2,projected\n"
        "2023,real_gdp,23000,actual\n"
        "2024,real_gdp,23500,projected\n"
        "2025,real_gdp,24000,projected\n",
    )
    # also an older vintage for compare
    _csv(
        "data/economic/economic_projections/fiscal_2025-01.csv",
        "date,variable,value,estimate_type\n"
        "2023,unemployment_rate,3.7,actual\n"
        "2024,unemployment_rate,4.3,projected\n"
        "2025,unemployment_rate,4.5,projected\n",
    )
    # 2) budget long (fiscal)
    _csv(
        "data/budget/ten_year_budget/fiscal_2026-02.csv",
        "date,variable,value\n"
        "FY2024,deficit,-1800\n"
        "FY2025,deficit,-1900\n"
        "FY2026,deficit,-2000\n",
    )
    # 3) spending_detail (wide)
    _csv(
        "data/budget/spending_detail/spending_2026-02.csv",
        "date,tin,title,disc_or_mand,category,agency,bureau,function_code,"
        "subfunction_code,off_budget,budget_authority,outlays\n"
        "FY2026,012-3456,Sample Health Account,mand,health,"
        "Department of Health and Human Services,CMS,550,551,0,1000,950\n"
        "FY2026,028-1111,Sample SSA Account,mand,income,"
        "Social Security Administration,OASI,650,651,1,800,790\n",
    )
    # 4) demographic
    _csv(
        "data/economic/demographic/population_bls_2026-02.csv",
        "year,age,sex,number_of_people\n"
        "2030,30,male,1000\n"
        "2030,30,female,1010\n"
        "2031,30,male,1005\n",
    )

    def _file(relpath: str, file_type: str, vintage: str, date_basis: str) -> dict:
        return {
            "file_type": file_type,
            "vintage": vintage,
            "relpath": relpath,
            "raw_url": f"{raw_base}/{relpath}",
            "date_basis": date_basis,
        }

    catalog = {
        "datasets": [
            {
                "dataset": "economic_projections",
                "domain": "economic",
                "format": "long",
                "title": "Economic Projections",
                "description": "Macro projections.",
                "publication_id": "51135",
                "landing_page": "https://www.cbo.gov/publication/51135",
                "frequency": "annual",
                "date_format": "fiscal",
                "notes": "",
                "vintages": ["2026-02", "2025-01"],
                "file_types": ["fiscal"],
                "variables": {
                    "unemployment_rate": {
                        "description": "Unemployment rate",
                        "unit": "Percent",
                        "category": "labor",
                    },
                    "real_gdp": {
                        "description": "Real GDP",
                        "unit": "Billions of chained dollars",
                        "category": "output",
                    },
                },
                "files": [
                    _file(
                        "data/economic/economic_projections/fiscal_2026-02.csv",
                        "fiscal", "2026-02", "fiscal",
                    ),
                    _file(
                        "data/economic/economic_projections/fiscal_2025-01.csv",
                        "fiscal", "2025-01", "fiscal",
                    ),
                ],
            },
            {
                "dataset": "ten_year_budget",
                "domain": "budget",
                "format": "long",
                "title": "10-Year Budget Projections",
                "description": "Budget totals.",
                "publication_id": "51118",
                "landing_page": "https://www.cbo.gov/publication/51118",
                "frequency": "annual",
                "date_format": "fiscal",
                "notes": "",
                "vintages": ["2026-02"],
                "file_types": ["fiscal"],
                "variables": {
                    "deficit": {
                        "description": "Total deficit (-) or surplus",
                        "unit": "Billions of dollars",
                        "category": "budget",
                    }
                },
                "files": [
                    _file(
                        "data/budget/ten_year_budget/fiscal_2026-02.csv",
                        "fiscal", "2026-02", "fiscal",
                    )
                ],
            },
            {
                "dataset": "spending_detail",
                "domain": "budget",
                "format": "spending_detail",
                "title": "Spending Detail",
                "description": "Budget accounts.",
                "publication_id": "51119",
                "landing_page": "https://www.cbo.gov/publication/51119",
                "frequency": "annual",
                "date_format": "fiscal",
                "notes": "",
                "vintages": ["2026-02"],
                "file_types": ["spending"],
                "columns": ["tin", "title", "agency", "outlays", "budget_authority"],
                "files": [
                    _file(
                        "data/budget/spending_detail/spending_2026-02.csv",
                        "spending", "2026-02", "fiscal",
                    )
                ],
            },
            {
                "dataset": "demographic",
                "domain": "economic",
                "format": "demographic",
                "title": "Demographic Projections",
                "description": "Population data.",
                "publication_id": "51123",
                "landing_page": "https://www.cbo.gov/publication/51123",
                "frequency": "annual",
                "date_format": "calendar",
                "notes": "",
                "vintages": ["2026-02"],
                "file_types": ["population_bls"],
                "domains": {"population_bls": {"columns": ["year", "age", "sex"]}},
                "files": [
                    _file(
                        "data/economic/demographic/population_bls_2026-02.csv",
                        "population_bls", "2026-02", "calendar",
                    )
                ],
            },
        ]
    }

    catalog_path = root / "official_catalog.json"
    catalog_path.write_text(_json.dumps(catalog), encoding="utf-8")
    return catalog_path, official_dir


@pytest.fixture(scope="session")
def official_db(tmp_path_factory) -> tuple[_Path, _Path]:
    """Build a synthetic official DuckDB and return (db_path, catalog_path)."""
    from src.official_data.build import build_database

    root = tmp_path_factory.mktemp("official")
    catalog_path, official_dir = _write_official_tree(root)
    db_path = root / "cbo_official.duckdb"
    build_database(catalog_path=catalog_path, official_dir=official_dir, db_path=db_path)
    return db_path, catalog_path


@pytest.fixture()
def official_loader(official_db):
    """An OfficialDataLoader bound to the synthetic DuckDB (no auto-build)."""
    from src.official_data.loader import OfficialDataLoader

    db_path, catalog_path = official_db
    loader = OfficialDataLoader(db_path=db_path, catalog_path=catalog_path, auto_build=False)
    yield loader
    loader.close()


@pytest.fixture()
def official_tools(official_loader):
    """Inject the synthetic loader into src.official_tools and restore after."""
    import src.official_tools as ot

    prev = ot._LOADER
    ot.set_loader(official_loader)
    yield ot
    ot.set_loader(prev)  # type: ignore[arg-type]
