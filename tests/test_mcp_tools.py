from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.mcp_tools import compare_vintages, export_csv, get_projection, list_file_types
from src.tool_registry import get_gemini_tool_declarations, list_tool_names


class FakeLoader:
    def __init__(self):
        self._index = {
            "medicaid": {
                "description": "Medicaid projections.",
                "vintages": ["2023-01", "2024-01"],
            }
        }
        self._df = pd.DataFrame(
            [
                {
                    "program": "Medicaid",
                    "fiscal_year": 2029,
                    "value": 100.0,
                    "vintage": "2023-01",
                },
                {
                    "program": "Medicaid",
                    "fiscal_year": 2029,
                    "value": 110.0,
                    "vintage": "2024-01",
                },
                {
                    "program": "CHIP",
                    "fiscal_year": 2029,
                    "value": 25.0,
                    "vintage": "2024-01",
                },
            ]
        )

    def list_file_types(self):
        return sorted(self._index.keys())

    def list_vintages(self, file_type: str):
        return self._index[file_type]["vintages"]

    def load_file_type(self, file_type: str):
        if file_type not in self._index:
            raise KeyError(file_type)
        return self._df


def test_list_file_types_returns_non_empty_list():
    result = list_file_types(loader=FakeLoader())
    assert isinstance(result, list)
    assert result
    assert result[0]["file_type"] == "medicaid"


def test_get_projection_filters_known_program_and_year():
    result = get_projection(
        "medicaid",
        program="Medicaid",
        year_start=2029,
        year_end=2029,
        loader=FakeLoader(),
    )
    assert "error" not in result
    assert result["row_count"] == 2
    assert {row["vintage"] for row in result["rows"]} == {"2023-01", "2024-01"}


def test_compare_vintages_returns_both_vintage_values():
    result = compare_vintages(
        "medicaid",
        metric="value",
        vintage_a="2023-01",
        vintage_b="2024-01",
        program="Medicaid",
        year=2029,
        loader=FakeLoader(),
    )
    assert "error" not in result
    assert result["row_count"] == 1
    row = result["rows"][0]
    assert row["vintage_a"] == "2023-01"
    assert row["vintage_b"] == "2024-01"
    assert row["value_a"] == 100.0
    assert row["value_b"] == 110.0


def test_export_csv_creates_file(tmp_path: Path):
    rows = [{"program": "Medicaid", "value": 110.0}]
    result = export_csv(
        rows,
        output_dir=str(tmp_path),
        filename="out.csv",
        file_type="medicaid",
        vintage="2024-01",
    )
    assert "error" not in result
    output = Path(result["file_path"])
    assert output.exists()
    assert output.name == "out.csv"
    contents = output.read_text(encoding="utf-8")
    assert "# file_type: medicaid" in contents
    assert "# vintage: 2024-01" in contents
    written = pd.read_csv(output, comment="#").to_dict(orient="records")
    assert written == rows


def test_get_projection_invalid_year_range_returns_error():
    result = get_projection(
        "medicaid",
        year_start=2030,
        year_end=2029,
        loader=FakeLoader(),
    )
    assert result["error"] == "year_start must be less than or equal to year_end."


def test_tool_registry_contains_all_six_tools():
    assert set(list_tool_names()) == {
        "list_file_types",
        "list_vintages",
        "get_projection",
        "compare_vintages",
        "search_programs",
        "export_csv",
    }


def test_tool_registry_exposes_gemini_declarations():
    declarations = get_gemini_tool_declarations()
    assert len(declarations) == 6
    assert {d["name"] for d in declarations} == set(list_tool_names())
