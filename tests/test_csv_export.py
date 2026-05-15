from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.mcp_tools import export_csv


def test_export_csv_autogenerates_filename_and_writes_metadata(tmp_path: Path):
    rows = [{"program": "Medicaid Enrollment", "year": 2029, "value": 110.0}]
    result = export_csv(
        rows,
        output_dir=str(tmp_path),
        file_type="medicaid",
        vintage="2024-01",
        query_params={"metric": "enrollment", "year": 2029},
    )
    assert "error" not in result

    output = Path(result["file_path"])
    assert output.exists()
    assert output.parent == tmp_path
    assert output.suffix == ".csv"
    assert "medicaid" in output.name
    assert "enrollment" in output.name
    assert "2029" in output.name

    text = output.read_text(encoding="utf-8")
    assert "# file_type: medicaid" in text
    assert "# vintage: 2024-01" in text
    assert "# export_timestamp:" in text

    parsed = pd.read_csv(output, comment="#")
    assert list(parsed.columns) == ["program", "year", "value"]
    assert parsed.to_dict(orient="records") == rows


def test_export_csv_creates_exports_directory_and_sanitizes_filename(tmp_path: Path):
    rows = [{"question": "Q", "answer": "A"}]
    result = export_csv(
        rows,
        output_dir=str(tmp_path / "nested" / "exports"),
        filename="../unsafe file?.csv",
    )
    assert "error" not in result

    output = Path(result["file_path"])
    assert output.exists()
    assert output.parent == (tmp_path / "nested" / "exports")
    assert output.name == "unsafe_file.csv"
    parsed = pd.read_csv(output, comment="#").to_dict(orient="records")
    assert parsed == rows


def test_export_csv_embeds_provenance_headers(tmp_path: Path):
    """Caller-supplied question, tool_calls, and sources land in the CSV header."""
    rows = [{"program": "Medicare", "year": 2030, "value": 1234.5}]
    tool_calls = [
        {"tool": "summarize_file_type", "args": {"file_type": "medicare"}},
        {"tool": "aggregate_metric", "args": {"file_type": "medicare", "metric": "value"}},
    ]
    sources = [
        {
            "source_file": "51302-2026-02-medicare.xlsx",
            "source_sheet": "Medicare_02-2026",
            "vintage": "2026-02",
            "cbo_product_id": "51302",
        }
    ]

    result = export_csv(
        rows,
        output_dir=str(tmp_path),
        file_type="medicare",
        vintage="2026-02",
        source_question="What is Medicare spending in 2030?",
        tool_calls=tool_calls,
        sources=sources,
    )
    assert "error" not in result

    text = Path(result["file_path"]).read_text(encoding="utf-8")
    assert "# source_question: What is Medicare spending in 2030?" in text
    assert "# tool_call_1: summarize_file_type" in text
    assert "# tool_call_2: aggregate_metric" in text
    assert "# source_1: source_file=51302-2026-02-medicare.xlsx" in text
    assert "sheet=Medicare_02-2026" in text
    assert "vintage=2026-02" in text


def test_export_csv_inherits_sources_from_result_dict(tmp_path: Path):
    """If caller passes the full tool result dict, sources are auto-pulled."""
    tool_result = {
        "rows": [{"year": 2030, "value": 1.0}],
        "sources": [
            {"source_file": "x.xlsx", "source_sheet": "S", "vintage": "2026-02"}
        ],
    }
    result = export_csv(tool_result, output_dir=str(tmp_path), file_type="medicare")
    assert "error" not in result
    text = Path(result["file_path"]).read_text(encoding="utf-8")
    assert "# source_1: source_file=x.xlsx" in text
