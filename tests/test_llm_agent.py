"""
test_llm_agent.py — Task 04: CBOAgent unit and integration tests.

Unit tests mock the Gemini SDK and run fully offline.
Integration tests are marked with @pytest.mark.integration and are skipped
automatically when GEMINI_API_KEY is not set in the environment.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from src.llm_agent import _MAX_TOOL_ITERATIONS, CBOAgent


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_text_response(text: str = "Final answer.") -> MagicMock:
    """Return a fake Gemini response containing only a text part (no tool call)."""
    part = MagicMock()
    part.function_call.name = ""  # empty → not a tool call
    resp = MagicMock()
    resp.parts = [part]
    resp.text = text
    return resp


def _make_fn_call_response(name: str, args: dict) -> MagicMock:
    """Return a fake Gemini response that requests one function call."""
    fc = MagicMock()
    fc.name = name
    fc.args = args
    part = MagicMock()
    part.function_call = fc
    resp = MagicMock()
    resp.parts = [part]
    resp.text = ""
    return resp


# ── shared fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def patched_genai(monkeypatch):
    """Patch the genai module used inside llm_agent so no real API calls occur."""
    mock_genai = MagicMock()
    monkeypatch.setattr("src.llm_agent.genai", mock_genai)
    # _build_genai_tools calls get_gemini_tool_declarations; return empty list to
    # keep the test simple — tool schema correctness is verified in test_mcp_tools.py.
    monkeypatch.setattr("src.llm_agent.get_gemini_tool_declarations", lambda: [])
    return mock_genai


@pytest.fixture()
def agent(monkeypatch, patched_genai):
    """A fully mocked CBOAgent with a fake API key."""
    monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-abc")
    return CBOAgent()


# ── unit tests — constructor ──────────────────────────────────────────────────


class TestCBOAgentInit:
    def test_raises_without_api_key(self, monkeypatch, patched_genai):
        monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            CBOAgent()

    def test_accepts_explicit_api_key(self, monkeypatch, patched_genai):
        monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        agent = CBOAgent(api_key="explicit-key")
        patched_genai.configure.assert_called_once_with(api_key="explicit-key")
        assert isinstance(agent, CBOAgent)

    def test_reads_api_key_from_env(self, monkeypatch, patched_genai):
        monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
        monkeypatch.setenv("GEMINI_API_KEY", "env-key-xyz")
        CBOAgent()
        patched_genai.configure.assert_called_once_with(api_key="env-key-xyz")

    def test_model_is_initialized(self, monkeypatch, patched_genai):
        monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        CBOAgent()
        patched_genai.GenerativeModel.assert_called_once()
        call_kwargs = patched_genai.GenerativeModel.call_args.kwargs
        assert call_kwargs.get("model_name") == "gemini-2.5-flash"


# ── unit tests — ask() single turn ───────────────────────────────────────────


class TestCBOAgentAskSingleTurn:
    def test_returns_text_when_no_tool_call(self, agent, patched_genai):
        chat_mock = patched_genai.GenerativeModel.return_value.start_chat.return_value
        chat_mock.send_message.return_value = _make_text_response("The answer is 42.")

        result = agent.ask("What is the meaning of life?")

        assert result == "The answer is 42."
        chat_mock.send_message.assert_called_once_with("What is the meaning of life?")

    def test_empty_response_returns_placeholder(self, agent, patched_genai):
        resp = MagicMock()
        resp.parts = []
        resp.text = ""
        chat_mock = patched_genai.GenerativeModel.return_value.start_chat.return_value
        chat_mock.send_message.return_value = resp

        result = agent.ask("Give me nothing.")

        assert result == "(no response)"


# ── unit tests — ask() multi-turn tool calling ────────────────────────────────


class TestCBOAgentAskToolCalling:
    def test_single_tool_call_dispatched(self, agent, patched_genai, monkeypatch):
        """Model requests list_file_types → tool runs → model returns final text."""
        chat_mock = patched_genai.GenerativeModel.return_value.start_chat.return_value
        chat_mock.send_message.side_effect = [
            _make_fn_call_response("list_file_types", {}),
            _make_text_response("Available types: medicaid."),
        ]

        fake_tool = MagicMock(return_value=[{"file_type": "medicaid"}])
        monkeypatch.setattr("src.llm_agent.get_tool", lambda name: fake_tool)

        result = agent.ask("List available file types.")

        assert result == "Available types: medicaid."
        fake_tool.assert_called_once_with()

    def test_tool_call_with_args(self, agent, patched_genai, monkeypatch):
        """Model requests get_projection with args → args forwarded to tool."""
        chat_mock = patched_genai.GenerativeModel.return_value.start_chat.return_value
        chat_mock.send_message.side_effect = [
            _make_fn_call_response(
                "get_projection",
                {"file_type": "medicaid", "year_start": 2029, "year_end": 2029},
            ),
            _make_text_response("Medicaid enrollment in 2029 is X."),
        ]

        fake_tool = MagicMock(return_value={"rows": [], "row_count": 0})
        monkeypatch.setattr("src.llm_agent.get_tool", lambda name: fake_tool)

        result = agent.ask("Medicaid in 2029?")

        assert result == "Medicaid enrollment in 2029 is X."
        fake_tool.assert_called_once_with(
            file_type="medicaid", year_start=2029, year_end=2029
        )

    def test_failed_tool_call_wrapped_as_error(self, agent, patched_genai, monkeypatch):
        """Unknown tool name → error dict sent back → model returns fallback text."""
        chat_mock = patched_genai.GenerativeModel.return_value.start_chat.return_value
        chat_mock.send_message.side_effect = [
            _make_fn_call_response("unknown_tool", {}),
            _make_text_response("I could not retrieve that data."),
        ]

        def raise_key_error(name: str):
            raise KeyError(f"Unknown tool '{name}'")

        monkeypatch.setattr("src.llm_agent.get_tool", raise_key_error)

        result = agent.ask("Do something unknown.")

        assert result == "I could not retrieve that data."
        # Two send_message calls: initial question + error response
        assert chat_mock.send_message.call_count == 2

    def test_max_iterations_cap(self, agent, patched_genai, monkeypatch):
        """Tool calls capped at _MAX_TOOL_ITERATIONS; last response text returned."""
        chat_mock = patched_genai.GenerativeModel.return_value.start_chat.return_value
        # Always return another tool call — iteration must stop at the cap.
        final_response = _make_text_response("Stopped after cap.")
        chat_mock.send_message.side_effect = (
            [_make_fn_call_response("list_file_types", {})] * _MAX_TOOL_ITERATIONS
            + [final_response]
        )

        fake_tool = MagicMock(return_value=[])
        monkeypatch.setattr("src.llm_agent.get_tool", lambda name: fake_tool)

        result = agent.ask("Keep calling tools forever.")

        # The loop ran _MAX_TOOL_ITERATIONS times after the first send_message,
        # so total send_message calls = 1 (question) + _MAX_TOOL_ITERATIONS.
        assert chat_mock.send_message.call_count == 1 + _MAX_TOOL_ITERATIONS
        assert result == "Stopped after cap."


# ── integration tests (skipped when GEMINI_API_KEY is absent) ─────────────────


_HAS_KEY = bool(os.environ.get("GEMINI_API_KEY"))
_SKIP_REASON = "GEMINI_API_KEY not set — integration test skipped"


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_KEY, reason=_SKIP_REASON)
class TestCBOAgentIntegration:
    """End-to-end benchmark queries against the live Gemini API.

    These tests require ``GEMINI_API_KEY`` to be set and a populated
    ``data/catalog.json`` produced by ``scripts/catalog_data.py``.
    """

    @pytest.fixture(autouse=True)
    def _live_agent(self):
        self.agent = CBOAgent()

    def test_medicaid_enrollment_query(self):
        """Benchmark 1: Medicaid enrollment projection for 2029."""
        answer = self.agent.ask(
            "How many people are projected to be enrolled in Medicaid in 2029 "
            "according to the latest projections?"
        )
        assert isinstance(answer, str)
        assert len(answer) > 10

    def test_social_security_vintage_comparison(self):
        """Benchmark 2: Compare 2023 vs 2024 Social Security projections for 2030."""
        answer = self.agent.ask(
            "Compare CBO's 2023 and 2024 projections for Social Security outlays in 2030."
        )
        assert isinstance(answer, str)
        assert len(answer) > 10

    def test_discretionary_spending_growth(self):
        """Benchmark 3: Discretionary spending categories with highest growth 2025–2034."""
        answer = self.agent.ask(
            "What are the discretionary spending categories with the largest projected "
            "growth between 2025 and 2034?"
        )
        assert isinstance(answer, str)
        assert len(answer) > 10
