"""Tests for the OfficialDataLoader query layer (src/official_data/loader.py)."""

from __future__ import annotations

import pytest


def test_list_datasets(official_loader):
    names = {d["dataset"] for d in official_loader.list_datasets()}
    assert {"economic_projections", "ten_year_budget", "spending_detail",
            "demographic"} <= names


def test_list_datasets_domain_filter(official_loader):
    eco = official_loader.list_datasets(domain="economic")
    assert all(d["domain"] == "economic" for d in eco)
    assert any(d["dataset"] == "economic_projections" for d in eco)


def test_list_vintages_newest_first(official_loader):
    vintages = official_loader.list_vintages("economic_projections")
    assert vintages == ["2026-02", "2025-01"]


def test_search_variables(official_loader):
    df = official_loader.search_variables("unemployment")
    assert "unemployment_rate" in set(df["variable"])


def test_query_series_default_vintage(official_loader):
    df = official_loader.query_series("economic_projections", ["unemployment_rate"])
    # default vintage is newest (2026-02)
    assert set(df["vintage"]) == {"2026-02"}
    assert len(df) == 3


def test_query_series_date_filter_and_estimate_type(official_loader):
    df = official_loader.query_series(
        "economic_projections", ["unemployment_rate"],
        date_start=2024, date_end=2025, estimate_type="projected",
    )
    assert list(df["year"]) == [2024, 2025]
    assert set(df["estimate_type"]) == {"projected"}


def test_query_series_rejects_non_long(official_loader):
    with pytest.raises(ValueError):
        official_loader.query_series("spending_detail", ["outlays"])


def test_rank_spending(official_loader):
    df = official_loader.rank_spending(metric="outlays", group_by="agency", top_n=5)
    # HHS (950) ranks above SSA (790)
    assert df.iloc[0]["group_key"] == "Department of Health and Human Services"
    assert df.iloc[0]["total"] == 950


def test_query_spending_filter(official_loader):
    df = official_loader.query_spending(agency="Social Security")
    assert len(df) == 1
    assert df.iloc[0]["tin"] == "028-1111"


def test_query_demographic(official_loader):
    df = official_loader.query_demographic("population_bls", year_start=2030, year_end=2030)
    assert len(df) == 2
    assert set(df["measure_name"]) == {"number_of_people"}
