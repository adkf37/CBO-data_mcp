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
