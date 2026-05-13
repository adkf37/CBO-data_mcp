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
