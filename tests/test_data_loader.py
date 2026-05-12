"""
tests/test_data_loader.py — Unit tests for src/data_loader.py (Task 02)

Tests run without the real CBO data repo.  All filesystem interaction is
either patched with pytest-mock or directed at a temporary directory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import DataLoader, _extract_vintage


# ---------------------------------------------------------------------------
# _extract_vintage unit tests
# ---------------------------------------------------------------------------


class TestExtractVintage:
    def test_year_and_month(self):
        assert _extract_vintage("medicaid_2026_02") == "2026-02"

    def test_year_only(self):
        assert _extract_vintage("snap_2019") == "2019"

    def test_with_prefix_underscores(self):
        assert _extract_vintage("aatf_0_2023_05") == "2023-05"

    def test_multi_word_type(self):
        assert _extract_vintage("premium_tax_credit_2024_07") == "2024-07"

    def test_no_vintage_returns_none(self):
        assert _extract_vintage("no_date_here") is None

    def test_four_digit_suffix_treated_as_year(self):
        # Stem with only a 4-digit year at the end
        assert _extract_vintage("some_type_2020") == "2020"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_catalog(tmp_path: Path):
    """Create a minimal catalog.json with two file types and two vintages each."""
    raw_dir = tmp_path / "data" / "raw" / "data" / "processed"
    raw_dir.mkdir(parents=True)

    # File type A — two vintages, same schema
    csv_a1 = raw_dir / "widget_2023_01.csv"
    csv_a2 = raw_dir / "widget_2024_03.csv"
    df_a = pd.DataFrame(
        {
            "program": ["prog_a"],
            "fiscal_year": [2023],
            "value": [100.0],
        }
    )
    df_a.to_csv(csv_a1, index=False)
    df_a["fiscal_year"] = [2024]
    df_a.to_csv(csv_a2, index=False)

    # File type B — two vintages, different schemas (schema drift)
    csv_b1 = raw_dir / "gadget_2022_06.csv"
    csv_b2 = raw_dir / "gadget_2023_06.csv"
    pd.DataFrame({"program": ["prog_b"], "value": [5.0]}).to_csv(csv_b1, index=False)
    pd.DataFrame(
        {"program": ["prog_b"], "value": [6.0], "extra_col": ["x"]}
    ).to_csv(csv_b2, index=False)

    # Build catalog entries using paths relative to tmp_path
    catalog = [
        {
            "file_type": "gadget",
            "description": "Gadget data.",
            "columns": [{"name": "program", "type": "string"}],
            "vintages": ["2022-06", "2023-06"],
            "file_paths": [
                str(csv_b1.relative_to(tmp_path)),
                str(csv_b2.relative_to(tmp_path)),
            ],
        },
        {
            "file_type": "widget",
            "description": "Widget data.",
            "columns": [{"name": "program", "type": "string"}],
            "vintages": ["2023-01", "2024-03"],
            "file_paths": [
                str(csv_a1.relative_to(tmp_path)),
                str(csv_a2.relative_to(tmp_path)),
            ],
        },
    ]

    catalog_path = tmp_path / "data" / "catalog.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    consolidated_dir = tmp_path / "data" / "consolidated"
    return catalog_path, consolidated_dir, tmp_path


@pytest.fixture()
def loader(tmp_catalog, monkeypatch):
    """Return a DataLoader pointing at the temp catalog and CSV files."""
    catalog_path, consolidated_dir, tmp_path = tmp_catalog

    # Patch _PROJECT_ROOT so relative paths in catalog resolve to tmp_path
    import src.data_loader as dl_mod

    monkeypatch.setattr(dl_mod, "_PROJECT_ROOT", tmp_path)

    return DataLoader(catalog_path=catalog_path, consolidated_dir=consolidated_dir)


# ---------------------------------------------------------------------------
# DataLoader.list_file_types
# ---------------------------------------------------------------------------


class TestListFileTypes:
    def test_returns_all_types(self, loader):
        types = loader.list_file_types()
        assert set(types) == {"widget", "gadget"}

    def test_returns_sorted(self, loader):
        types = loader.list_file_types()
        assert types == sorted(types)


# ---------------------------------------------------------------------------
# DataLoader.list_vintages
# ---------------------------------------------------------------------------


class TestListVintages:
    def test_widget_has_two_vintages(self, loader):
        vintages = loader.list_vintages("widget")
        assert len(vintages) == 2

    def test_vintages_are_sorted(self, loader):
        vintages = loader.list_vintages("widget")
        assert vintages == sorted(vintages)

    def test_unknown_file_type_raises(self, loader):
        with pytest.raises(KeyError, match="nonexistent"):
            loader.list_vintages("nonexistent")


# ---------------------------------------------------------------------------
# DataLoader.load_file_type
# ---------------------------------------------------------------------------


class TestLoadFileType:
    def test_returns_nonempty_dataframe(self, loader):
        df = loader.load_file_type("widget")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_vintage_column_present(self, loader):
        df = loader.load_file_type("widget")
        assert "vintage" in df.columns

    def test_vintage_column_non_null(self, loader):
        df = loader.load_file_type("widget")
        assert df["vintage"].notna().all()

    def test_both_vintages_represented(self, loader):
        df = loader.load_file_type("widget")
        assert {"2023-01", "2024-03"}.issubset(set(df["vintage"].unique()))

    def test_schema_drift_fills_nan(self, loader):
        """gadget has schema drift — extra_col should appear with NaN in older vintage."""
        df = loader.load_file_type("gadget")
        assert "extra_col" in df.columns
        # The 2022-06 vintage row should have NaN for extra_col
        older = df[df["vintage"] == "2022-06"]
        assert older["extra_col"].isna().all()

    def test_unknown_file_type_raises(self, loader):
        with pytest.raises(KeyError, match="nonexistent"):
            loader.load_file_type("nonexistent")

    def test_result_is_cached(self, loader):
        df1 = loader.load_file_type("widget")
        df2 = loader.load_file_type("widget")
        assert df1 is df2  # same object from cache

    def test_parquet_written(self, loader, tmp_catalog):
        _, consolidated_dir, _ = tmp_catalog
        loader.load_file_type("widget")
        parquet_path = consolidated_dir / "widget.parquet"
        assert parquet_path.exists()

    def test_parquet_cache_loaded_on_second_loader(self, loader, tmp_catalog, monkeypatch):
        """A fresh DataLoader for the same catalog should load from parquet."""
        catalog_path, consolidated_dir, tmp_path = tmp_catalog
        # First load writes parquet
        loader.load_file_type("widget")

        # Create a second loader without in-memory cache
        import src.data_loader as dl_mod

        monkeypatch.setattr(dl_mod, "_PROJECT_ROOT", tmp_path)
        loader2 = DataLoader(catalog_path=catalog_path, consolidated_dir=consolidated_dir)
        df = loader2.load_file_type("widget")
        assert "vintage" in df.columns
        assert len(df) > 0


# ---------------------------------------------------------------------------
# Missing catalog file
# ---------------------------------------------------------------------------


class TestMissingCatalog:
    def test_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Catalog not found"):
            DataLoader(catalog_path=tmp_path / "nonexistent.json")
