from __future__ import annotations

from web.app import _collect_response_sources, _select_response_charts


def test_select_response_charts_keeps_first_chart_by_default():
    trace = [
        {
            "tool": "chart_projection",
            "result": {
                "chart_data": {
                    "type": "line",
                    "title": "SSDI Total Beneficiaries",
                    "labels": [2026],
                    "datasets": [{"label": "2026-02", "data": [7000]}],
                }
            },
        },
        {
            "tool": "chart_projection",
            "result": {
                "chart_data": {
                    "type": "line",
                    "title": "SSDI Disabled Workers",
                    "labels": [2026],
                    "datasets": [{"label": "2026-02", "data": [6000]}],
                }
            },
        },
    ]

    charts = _select_response_charts(
        trace,
        "Compare SSDI beneficiary counts across all projections since 2021.",
    )

    assert len(charts) == 1
    assert charts[0]["title"] == "SSDI Total Beneficiaries"


def test_select_response_charts_allows_explicit_multiple_charts():
    trace = [
        {
            "tool": "chart_projection",
            "result": {
                "chart_data": {
                    "type": "line",
                    "title": "A",
                    "labels": [2026],
                    "datasets": [{"label": "2026-02", "data": [1]}],
                }
            },
        },
        {
            "tool": "chart_projection",
            "result": {
                "chart_data": {
                    "type": "line",
                    "title": "B",
                    "labels": [2026],
                    "datasets": [{"label": "2026-02", "data": [2]}],
                }
            },
        },
    ]

    charts = _select_response_charts(trace, "Show separate charts for A and B.")

    assert [chart["title"] for chart in charts] == ["A", "B"]


def test_collect_response_sources_dedupes_chart_sources():
    source = {
        "source_file": "51307-2026-02-ssdi.xlsx",
        "source_sheet": "SSDI_02-2026",
        "vintage": "2026-02",
    }
    trace = [
        {"tool": "chart_projection", "result": {"sources": [source]}},
        {"tool": "get_projection", "result": {"sources": [source]}},
    ]

    assert _collect_response_sources(trace) == [source]
