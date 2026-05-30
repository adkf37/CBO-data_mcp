"""Tests for the official MCP tools (src/official_tools.py) and registration."""

from __future__ import annotations


def test_tools_registered_and_declared():
    from src.tool_registry import TOOL_FUNCTIONS, get_gemini_tool_declarations

    declared = {d["name"] for d in get_gemini_tool_declarations()}
    assert set(TOOL_FUNCTIONS) == declared  # every function has a declaration
    for name in (
        "list_official_datasets", "summarize_official_dataset",
        "search_official_variables", "get_official_series",
        "compare_official_vintages", "official_growth_rate",
        "chart_official_series", "query_budget_accounts", "query_demographic",
    ):
        assert name in TOOL_FUNCTIONS


def test_list_official_datasets(official_tools):
    out = official_tools.list_official_datasets()
    assert out["count"] == 4
    out_eco = official_tools.list_official_datasets(domain="economic")
    assert all(d["domain"] == "economic" for d in out_eco["datasets"])


def test_summarize_official_dataset(official_tools):
    out = official_tools.summarize_official_dataset("economic_projections")
    assert out["format"] == "long"
    assert out["variable_count"] == 2
    assert out["sources"][0]["source_repo"] == "https://github.com/US-CBO/cbo-data"


def test_search_variables(official_tools):
    out = official_tools.search_variables("gdp")
    assert any(m["variable"] == "real_gdp" for m in out["matches"])


def test_get_series_returns_rows_and_sources(official_tools):
    out = official_tools.get_series("economic_projections", "unemployment_rate")
    assert out["row_count"] == 3
    assert out["file_type"] == "fiscal"
    assert out["sources"][0]["raw_url"].endswith("fiscal_2026-02.csv")


def test_get_series_rejects_non_long(official_tools):
    out = official_tools.get_series("spending_detail", "outlays")
    assert "error" in out


def test_compare_official_vintages(official_tools):
    out = official_tools.compare_official_vintages(
        "economic_projections", "unemployment_rate", "2026-02", "2025-01",
    )
    assert out["row_count"] >= 3
    # delta present where both vintages have data
    deltas = [r.get("delta") for r in out["rows"] if r.get("delta") is not None]
    assert deltas


def test_series_growth_rate(official_tools):
    out = official_tools.series_growth_rate(
        "economic_projections", "real_gdp", 2023, 2025,
    )
    assert out["value_start"] == 23000
    assert out["value_end"] == 24000
    assert out["absolute_change"] == 1000
    assert out["cagr_percent"] is not None


def test_chart_series_single_vintage(official_tools):
    out = official_tools.chart_series(
        "economic_projections", "unemployment_rate",
    )
    cd = out["chart_data"]
    assert cd["type"] == "line"
    assert cd["labels"] == ["2023", "2024", "2025"]
    assert len(cd["datasets"]) == 1
    assert cd["datasets"][0]["data"] == [3.6, 4.0, 4.2]


def test_chart_series_multi_vintage_overlay(official_tools):
    out = official_tools.chart_series(
        "economic_projections", "unemployment_rate",
        vintages=["2026-02", "2025-01"],
    )
    assert len(out["chart_data"]["datasets"]) == 2
    assert set(out["vintages"]) == {"2026-02", "2025-01"}


def test_query_budget_accounts_ranking(official_tools):
    out = official_tools.query_budget_accounts(
        group_by="agency", top_n=5, metric="outlays",
    )
    assert out["mode"] == "ranking"
    assert out["rows"][0]["group_key"] == "Department of Health and Human Services"


def test_query_budget_accounts_lookup(official_tools):
    out = official_tools.query_budget_accounts(title_query="health")
    assert out["mode"] == "lookup"
    assert out["row_count"] == 1


def test_query_demographic(official_tools):
    out = official_tools.query_demographic("population_bls", year_start=2030, year_end=2030)
    assert out["row_count"] == 2
    assert "age" in out["rows"][0]
