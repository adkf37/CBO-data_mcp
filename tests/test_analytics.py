"""Tests for the analytical and charting MCP tools."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.mcp_tools import (
    aggregate_metric,
    chart_projection,
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
