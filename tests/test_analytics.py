"""Tests for the analytical and charting MCP tools."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.mcp_tools import (
    aggregate_metric,
    chart_projection,
    compare_vintages,
    get_projection,
    growth_rate,
    summarize_file_type,
    top_n,
)


class FakeLoader:
    def __init__(self, df: pd.DataFrame | None = None):
        self._df = df if df is not None else pd.DataFrame(
            [
                {"program": "Medicaid", "fiscal_year": 2024, "value": 100.0, "vintage": "2024-01"},
                {"program": "Medicaid", "fiscal_year": 2025, "value": 110.0, "vintage": "2024-01"},
                {"program": "Medicaid", "fiscal_year": 2029, "value": 150.0, "vintage": "2024-01"},
                {"program": "Medicare", "fiscal_year": 2024, "value": 800.0, "vintage": "2024-01"},
                {"program": "Medicare", "fiscal_year": 2025, "value": 850.0, "vintage": "2024-01"},
                {"program": "Medicare", "fiscal_year": 2029, "value": 1100.0, "vintage": "2024-01"},
                {"program": "CHIP", "fiscal_year": 2024, "value": 20.0, "vintage": "2024-01"},
                {"program": "CHIP", "fiscal_year": 2029, "value": 30.0, "vintage": "2024-01"},
            ]
        )
        self._index = {"medicaid": {"vintages": ["2024-01"]}}

    def list_file_types(self):
        return ["medicaid"]

    def list_vintages(self, file_type):
        return ["2024-01"]

    def load_file_type(self, file_type):
        if file_type != "medicaid":
            raise KeyError(file_type)
        return self._df


# ── aggregate_metric ──────────────────────────────────────────────────────────


def test_aggregate_metric_overall_sum():
    result = aggregate_metric("medicaid", metric="value", agg="sum", loader=FakeLoader())
    assert "error" not in result
    assert result["aggregate"] == pytest.approx(3160.0)
    assert result["agg"] == "sum"


def test_aggregate_metric_group_by_program_mean():
    result = aggregate_metric(
        "medicaid", metric="value", agg="mean", group_by="program", loader=FakeLoader()
    )
    assert "error" not in result
    rows = {row["group"]: row["value"] for row in result["rows"]}
    assert rows["Medicaid"] == pytest.approx(120.0)
    assert rows["Medicare"] == pytest.approx(916.6666666, rel=1e-3)
    assert rows["CHIP"] == pytest.approx(25.0)


def test_aggregate_metric_rejects_unknown_agg():
    result = aggregate_metric("medicaid", metric="value", agg="weird", loader=FakeLoader())
    assert "error" in result and "Unsupported agg" in result["error"]


def test_aggregate_metric_missing_metric_returns_error():
    result = aggregate_metric("medicaid", metric="not_a_column", loader=FakeLoader())
    assert "error" in result and "not found" in result["error"]


# ── top_n ─────────────────────────────────────────────────────────────────────


def test_top_n_orders_descending_by_default():
    result = top_n("medicaid", metric="value", n=2, loader=FakeLoader())
    assert "error" not in result
    assert [row["group"] for row in result["rows"]] == ["Medicare", "Medicaid"]


def test_top_n_ascending_returns_smallest():
    result = top_n("medicaid", metric="value", n=1, ascending=True, loader=FakeLoader())
    assert result["rows"][0]["group"] == "CHIP"


def test_top_n_rejects_invalid_n():
    result = top_n("medicaid", metric="value", n=0, loader=FakeLoader())
    assert "error" in result


# ── growth_rate ───────────────────────────────────────────────────────────────


def test_growth_rate_for_program_between_years():
    result = growth_rate(
        "medicaid",
        metric="value",
        year_start=2024,
        year_end=2029,
        program="Medicaid",
        loader=FakeLoader(),
    )
    assert "error" not in result
    assert result["start_value"] == pytest.approx(100.0)
    assert result["end_value"] == pytest.approx(150.0)
    assert result["absolute_change"] == pytest.approx(50.0)
    assert result["pct_change"] == pytest.approx(0.5)
    # CAGR over 5 years from 100 -> 150 = (1.5)^(1/5) - 1 ≈ 0.0845
    assert result["cagr"] == pytest.approx(0.0845, rel=1e-2)


def test_growth_rate_requires_strict_ordering():
    result = growth_rate(
        "medicaid", metric="value", year_start=2029, year_end=2029, loader=FakeLoader()
    )
    assert "error" in result


def test_growth_rate_zero_start_returns_none_cagr():
    df = pd.DataFrame(
        [
            {"program": "X", "fiscal_year": 2024, "value": 0.0, "vintage": "2024-01"},
            {"program": "X", "fiscal_year": 2029, "value": 50.0, "vintage": "2024-01"},
        ]
    )
    result = growth_rate(
        "medicaid", metric="value", year_start=2024, year_end=2029, loader=FakeLoader(df)
    )
    assert result["cagr"] is None
    assert result["pct_change"] is None


# ── summarize_file_type ───────────────────────────────────────────────────────


def test_summarize_file_type_returns_schema_and_year_range():
    result = summarize_file_type("medicaid", loader=FakeLoader())
    assert "error" not in result
    assert result["row_count"] == 8
    assert result["program_column"] == "program"
    assert result["year_column"] == "fiscal_year"
    assert result["year_range"] == [2024, 2029]
    assert "value" in result["numeric_columns"]
    assert set(result["top_programs"]) == {"Medicaid", "Medicare", "CHIP"}
    assert result["vintages"] == ["2024-01"]


# ── chart_projection ──────────────────────────────────────────────────────────


def test_chart_projection_line_returns_chart_data(tmp_path: Path):
    result = chart_projection(
        "medicaid",
        metric="value",
        program="Medicaid",
        kind="line",
        output_dir=str(tmp_path),
        filename="medicaid_line",
        loader=FakeLoader(),
    )
    assert "error" not in result, result
    cd = result["chart_data"]
    assert cd["type"] == "line"
    assert "labels" in cd
    assert "datasets" in cd
    assert result["chart_kind"] == "line"
    assert result["point_count"] >= 1


def test_chart_projection_bar_returns_chart_data(tmp_path: Path):
    result = chart_projection(
        "medicaid",
        metric="value",
        kind="bar",
        output_dir=str(tmp_path),
        filename="medicaid_bar",
        loader=FakeLoader(),
    )
    assert "error" not in result, result
    cd = result["chart_data"]
    assert cd["type"] == "bar"
    assert "labels" in cd
    assert "datasets" in cd
    assert result["chart_kind"] == "bar"
    # 3 program groups in fake data
    assert result["point_count"] == 3


def test_chart_projection_line_compares_one_series_across_multiple_vintages(tmp_path: Path):
    df = pd.DataFrame(
        [
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2026,
                "value": 88.0,
                "vintage": "2023-05",
            },
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2027,
                "value": 89.0,
                "vintage": "2023-05",
            },
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2026,
                "value": 90.0,
                "vintage": "2024-06",
            },
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2027,
                "value": 91.0,
                "vintage": "2024-06",
            },
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2026,
                "value": 92.0,
                "vintage": "2026-02",
            },
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2027,
                "value": 93.0,
                "vintage": "2026-02",
            },
            {
                "program": "Medicaid",
                "category": "Outlays",
                "unit": "Billions of dollars",
                "fiscal_year": 2026,
                "value": 700.0,
                "vintage": "2026-02",
            },
        ]
    )

    result = chart_projection(
        "medicaid",
        metric="value",
        program="Medicaid",
        category="Total Enrolled Within a Fiscal Year",
        unit="Millions of people",
        kind="line",
        group_by="vintage",
        year_start=2026,
        year_end=2027,
        output_dir=str(tmp_path),
        loader=FakeLoader(df),
    )

    assert "error" not in result, result
    assert result["chart_data"]["type"] == "line"
    assert result["chart_data"]["labels"] == [2026, 2027]
    datasets = {ds["label"]: ds["data"] for ds in result["chart_data"]["datasets"]}
    assert datasets == {
        "2023-05": [88.0, 89.0],
        "2024-06": [90.0, 91.0],
        "2026-02": [92.0, 93.0],
    }
    assert result["unit"] == "Millions of people"


def test_chart_projection_filters_explicit_vintages(tmp_path: Path):
    df = pd.DataFrame(
        [
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2026,
                "value": 88.0,
                "vintage": "2023-05",
            },
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2026,
                "value": 90.0,
                "vintage": "2024-06",
            },
            {
                "program": "Medicaid",
                "category": "Total Enrolled Within a Fiscal Year",
                "unit": "Millions of people",
                "fiscal_year": 2026,
                "value": 92.0,
                "vintage": "2026-02",
            },
        ]
    )

    result = chart_projection(
        "medicaid",
        metric="value",
        program="Medicaid",
        category="Total Enrolled Within a Fiscal Year",
        unit="Millions of people",
        kind="line",
        group_by="vintage",
        vintages=["2023-05", "2026-02"],
        output_dir=str(tmp_path),
        loader=FakeLoader(df),
    )

    assert "error" not in result, result
    assert result["vintages"] == ["2023-05", "2026-02"]
    labels = [dataset["label"] for dataset in result["chart_data"]["datasets"]]
    assert labels == ["2023-05", "2026-02"]


def test_chart_projection_filters_vintages_since_start(tmp_path: Path):
    df = pd.DataFrame(
        [
            {
                "program": "SSDI",
                "category": "All Disabled Workers",
                "unit": "Thousands",
                "fiscal_year": 2026,
                "value": 100.0,
                "vintage": "2022-05",
            },
            {
                "program": "SSDI",
                "category": "All Disabled Workers",
                "unit": "Thousands",
                "fiscal_year": 2026,
                "value": 110.0,
                "vintage": "2023-05",
            },
            {
                "program": "SSDI",
                "category": "All Disabled Workers",
                "unit": "Thousands",
                "fiscal_year": 2026,
                "value": 120.0,
                "vintage": "2026-02",
            },
        ]
    )

    result = chart_projection(
        "medicaid",
        metric="value",
        category="All Disabled Workers",
        unit="Thousands",
        kind="line",
        group_by="vintage",
        vintage_start="2023",
        output_dir=str(tmp_path),
        loader=FakeLoader(df),
    )

    assert "error" not in result, result
    assert result["vintages"] == ["2023-05", "2026-02"]


def test_chart_projection_rejects_unknown_kind(tmp_path: Path):
    result = chart_projection(
        "medicaid",
        metric="value",
        kind="pie",
        output_dir=str(tmp_path),
        loader=FakeLoader(),
    )
    assert "error" in result and "Unsupported chart kind" in result["error"]


def test_chart_projection_missing_metric(tmp_path: Path):
    result = chart_projection(
        "medicaid",
        metric="missing",
        output_dir=str(tmp_path),
        loader=FakeLoader(),
    )
    assert "error" in result


# ── is_total handling (prevents double counting) ──────────────────────────────


def _totals_loader() -> FakeLoader:
    """Loader with subtotal rows + their subcomponents for the same year."""
    df = pd.DataFrame(
        [
            # 2024 — Total + its three components (Total = sum of parts)
            {"program": "Medicare", "category": "Total Medicare benefits",
             "fiscal_year": 2024, "value": 900.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": True},
            {"program": "Medicare", "category": "Part A",
             "fiscal_year": 2024, "value": 400.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": False},
            {"program": "Medicare", "category": "Part B",
             "fiscal_year": 2024, "value": 350.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": False},
            {"program": "Medicare", "category": "Part D",
             "fiscal_year": 2024, "value": 150.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": False},
            # 2029 — same shape, larger numbers
            {"program": "Medicare", "category": "Total Medicare benefits",
             "fiscal_year": 2029, "value": 1200.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": True},
            {"program": "Medicare", "category": "Part A",
             "fiscal_year": 2029, "value": 500.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": False},
            {"program": "Medicare", "category": "Part B",
             "fiscal_year": 2029, "value": 500.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": False},
            {"program": "Medicare", "category": "Part D",
             "fiscal_year": 2029, "value": 200.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": False},
        ]
    )
    return FakeLoader(df)


def test_aggregate_metric_excludes_totals_by_default():
    # Subcomponents only: 400 + 350 + 150 + 500 + 500 + 200 = 2100
    result = aggregate_metric(
        "medicaid", metric="value", agg="sum", loader=_totals_loader()
    )
    assert "error" not in result
    assert result["aggregate"] == pytest.approx(2100.0)


def test_aggregate_metric_include_totals_keeps_totals():
    # Subcomponents + totals: 2100 + 900 + 1200 = 4200 (double counted on purpose)
    result = aggregate_metric(
        "medicaid",
        metric="value",
        agg="sum",
        include_totals=True,
        loader=_totals_loader(),
    )
    assert result["aggregate"] == pytest.approx(4200.0)


def test_top_n_excludes_totals_by_default():
    result = top_n(
        "medicaid",
        metric="value",
        n=5,
        group_by="category",
        loader=_totals_loader(),
    )
    groups = [row["group"] for row in result["rows"]]
    assert "Total Medicare benefits" not in groups
    assert {"Part A", "Part B", "Part D"}.issubset(set(groups))


def test_growth_rate_excludes_totals_by_default():
    # 2024 components sum to 900, 2029 components sum to 1200
    result = growth_rate(
        "medicaid",
        metric="value",
        year_start=2024,
        year_end=2029,
        loader=_totals_loader(),
    )
    assert "error" not in result
    assert result["start_value"] == pytest.approx(900.0)
    assert result["end_value"] == pytest.approx(1200.0)


def test_get_projection_includes_totals_by_default():
    result = get_projection("medicaid", year_start=2024, year_end=2024,
                             loader=_totals_loader())
    cats = {row["category"] for row in result["rows"]}
    assert "Total Medicare benefits" in cats


def test_get_projection_can_exclude_totals():
    result = get_projection(
        "medicaid",
        year_start=2024,
        year_end=2024,
        include_totals=False,
        loader=_totals_loader(),
    )
    cats = {row["category"] for row in result["rows"]}
    assert "Total Medicare benefits" not in cats


def test_compare_vintages_can_exclude_totals():
    # Two vintages with totals + parts. Excluding totals should yield only Part rows.
    df = pd.DataFrame(
        [
            {"program": "Medicare", "category": "Total Medicare benefits",
             "fiscal_year": 2029, "value": 1200.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": True},
            {"program": "Medicare", "category": "Part A",
             "fiscal_year": 2029, "value": 500.0, "unit": "Billions of dollars",
             "vintage": "2024-06", "is_total": False},
            {"program": "Medicare", "category": "Total Medicare benefits",
             "fiscal_year": 2029, "value": 1300.0, "unit": "Billions of dollars",
             "vintage": "2026-02", "is_total": True},
            {"program": "Medicare", "category": "Part A",
             "fiscal_year": 2029, "value": 550.0, "unit": "Billions of dollars",
             "vintage": "2026-02", "is_total": False},
        ]
    )
    result = compare_vintages(
        "medicaid",
        metric="value",
        vintage_a="2024-06",
        vintage_b="2026-02",
        year=2029,
        include_totals=False,
        loader=FakeLoader(df),
    )
    assert "error" not in result
    cats = {row["category"] for row in result["rows"]}
    assert cats == {"Part A"}


# ── Source citations ─────────────────────────────────────────────────────────


def _sourced_loader() -> FakeLoader:
    df = pd.DataFrame(
        [
            {
                "program": "Medicare", "category": "Part A", "fiscal_year": 2030,
                "value": 500.0, "unit": "Billions of dollars",
                "vintage": "2026-02",
                "source_file": "51302-2026-02-medicare.xlsx",
                "source_sheet": "Medicare_02-2026", "is_total": False,
            },
            {
                "program": "Medicare", "category": "Part B", "fiscal_year": 2030,
                "value": 600.0, "unit": "Billions of dollars",
                "vintage": "2026-02",
                "source_file": "51302-2026-02-medicare.xlsx",
                "source_sheet": "Medicare_02-2026", "is_total": False,
            },
        ]
    )
    return FakeLoader(df)


def test_get_projection_returns_sources():
    result = get_projection("medicaid", loader=_sourced_loader())
    assert "sources" in result
    assert len(result["sources"]) == 1  # deduped
    s = result["sources"][0]
    assert s["source_file"] == "51302-2026-02-medicare.xlsx"
    assert s["source_sheet"] == "Medicare_02-2026"
    assert s["vintage"] == "2026-02"
    assert s["cbo_product_id"] == "51302"
    assert "cbo_baseline_url" in s


def test_aggregate_metric_returns_sources():
    result = aggregate_metric(
        "medicaid", metric="value", agg="sum", loader=_sourced_loader()
    )
    assert "error" not in result
    assert result["aggregate"] == pytest.approx(1100.0)
    assert result["sources"] and result["sources"][0]["cbo_product_id"] == "51302"


def test_summarize_file_type_returns_sources():
    result = summarize_file_type("medicaid", loader=_sourced_loader())
    assert "error" not in result
    assert result["sources"] and result["sources"][0]["source_file"].endswith(".xlsx")


def test_growth_rate_returns_sources():
    df = pd.DataFrame(
        [
            {"program": "Medicare", "fiscal_year": 2024, "value": 100.0,
             "unit": "Billions of dollars", "vintage": "2024-06", "is_total": False,
             "source_file": "51302-2024-06-medicare.xlsx"},
            {"program": "Medicare", "fiscal_year": 2030, "value": 200.0,
             "unit": "Billions of dollars", "vintage": "2024-06", "is_total": False,
             "source_file": "51302-2024-06-medicare.xlsx"},
        ]
    )
    result = growth_rate(
        "medicaid", metric="value", year_start=2024, year_end=2030,
        loader=FakeLoader(df),
    )
    assert "error" not in result
    assert result["sources"] and result["sources"][0]["cbo_product_id"] == "51302"
