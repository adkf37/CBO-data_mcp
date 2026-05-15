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


def _make_response(text: str = "", fn_calls: list | None = None) -> MagicMock:
    """Build a fake google-genai GenerateContentResponse.

    * ``fn_calls`` – list of ``(name, args)`` tuples for function-call parts.
    * When ``fn_calls`` is empty/None the response is a plain text response.
    """
    parts: list[MagicMock] = []

    for name, args in (fn_calls or []):
        fc = MagicMock()
        fc.name = name
        fc.args = args
        part = MagicMock()
        part.function_call = fc
        parts.append(part)

    if not parts:
        # Text-only response — ensure function_call is falsy so the loop exits.
        part = MagicMock()
        part.function_call = None
        parts.append(part)

    content = MagicMock()
    content.parts = parts

    candidate = MagicMock()
    candidate.content = content

    resp = MagicMock()
    resp.candidates = [candidate]
    resp.text = text
    return resp


def _make_text_response(text: str = "Final answer.") -> MagicMock:
    return _make_response(text=text)


def _make_fn_call_response(name: str, args: dict) -> MagicMock:
    return _make_response(fn_calls=[(name, args)])


def _chat_mock(patched_genai: MagicMock) -> MagicMock:
    """Return the mock object that acts as the chat session."""
    return patched_genai.Client.return_value.chats.create.return_value


# ── shared fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def patched_genai(monkeypatch):
    """Patch the genai + types modules so no real API calls occur."""
    mock_genai = MagicMock()
    mock_types = MagicMock()
    monkeypatch.setattr("src.llm_agent.genai", mock_genai)
    monkeypatch.setattr("src.llm_agent.types", mock_types)
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
        patched_genai.Client.assert_called_once_with(api_key="explicit-key")
        assert isinstance(agent, CBOAgent)

    def test_reads_api_key_from_env(self, monkeypatch, patched_genai):
        monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
        monkeypatch.setenv("GEMINI_API_KEY", "env-key-xyz")
        CBOAgent()
        patched_genai.Client.assert_called_once_with(api_key="env-key-xyz")

    def test_chat_created_with_correct_model(self, monkeypatch, patched_genai):
        monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        a = CBOAgent()
        # Chat is lazily initialised — trigger it via ask()
        _chat_mock(patched_genai).send_message.return_value = _make_text_response("hi")
        a.ask("hello")
        create_kwargs = patched_genai.Client.return_value.chats.create.call_args
        assert create_kwargs.kwargs.get("model") == "gemini-2.5-flash"


# ── unit tests — ask() single turn ───────────────────────────────────────────


class TestCBOAgentAskSingleTurn:
    def test_returns_text_when_no_tool_call(self, agent, patched_genai):
        chat = _chat_mock(patched_genai)
        chat.send_message.return_value = _make_text_response("The answer is 42.")

        result = agent.ask("What is the meaning of life?")

        assert result == "The answer is 42."
        chat.send_message.assert_called_once_with("What is the meaning of life?")

    def test_empty_response_returns_placeholder(self, agent, patched_genai):
        resp = MagicMock()
        resp.text = ""
        resp.candidates = []
        _chat_mock(patched_genai).send_message.return_value = resp

        result = agent.ask("Give me nothing.")

        assert result == "(no response)"


# ── unit tests — ask() multi-turn tool calling ────────────────────────────────


class TestCBOAgentAskToolCalling:
    def test_single_tool_call_dispatched(self, agent, patched_genai, monkeypatch):
        """Model requests list_file_types → tool runs → model returns final text."""
        chat = _chat_mock(patched_genai)
        chat.send_message.side_effect = [
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
        chat = _chat_mock(patched_genai)
        chat.send_message.side_effect = [
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
        chat = _chat_mock(patched_genai)
        chat.send_message.side_effect = [
            _make_fn_call_response("unknown_tool", {}),
            _make_text_response("I could not retrieve that data."),
        ]

        def raise_key_error(name: str):
            raise KeyError(f"Unknown tool '{name}'")

        monkeypatch.setattr("src.llm_agent.get_tool", raise_key_error)

        result = agent.ask("Do something unknown.")

        assert result == "I could not retrieve that data."
        assert chat.send_message.call_count == 2

    def test_max_iterations_cap(self, agent, patched_genai, monkeypatch):
        """Tool calls capped at _MAX_TOOL_ITERATIONS; last response text returned."""
        chat = _chat_mock(patched_genai)
        final_response = _make_text_response("Stopped after cap.")
        chat.send_message.side_effect = (
            [_make_fn_call_response("list_file_types", {})] * _MAX_TOOL_ITERATIONS
            + [final_response]
        )

        fake_tool = MagicMock(return_value=[])
        monkeypatch.setattr("src.llm_agent.get_tool", lambda name: fake_tool)

        result = agent.ask("Keep calling tools forever.")

        assert chat.send_message.call_count == 1 + _MAX_TOOL_ITERATIONS
        assert result == "Stopped after cap."

    def test_chat_session_persists_across_asks(self, agent, patched_genai):
        """Two consecutive ask() calls reuse the same chat session."""
        chat = _chat_mock(patched_genai)
        chat.send_message.side_effect = [
            _make_text_response("first"),
            _make_text_response("second"),
        ]

        agent.ask("first question")
        agent.ask("second question")

        # chats.create called once across both asks → conversation state persists
        assert patched_genai.Client.return_value.chats.create.call_count == 1

    def test_reset_clears_chat_and_trace(self, agent, patched_genai):
        """reset() drops the cached chat so the next ask starts a new session."""
        chat = _chat_mock(patched_genai)
        chat.send_message.return_value = _make_text_response("hi")
        agent.ask("hello")
        agent.last_trace = [{"tool": "x", "args": {}, "result": {}}]

        agent.reset()

        assert agent.last_trace == []
        agent.ask("again")
        assert patched_genai.Client.return_value.chats.create.call_count == 2

    def test_trace_records_tool_calls(self, agent, patched_genai, monkeypatch):
        chat = _chat_mock(patched_genai)
        chat.send_message.side_effect = [
            _make_fn_call_response("list_file_types", {}),
            _make_text_response("done"),
        ]
        monkeypatch.setattr(
            "src.llm_agent.get_tool", lambda name: lambda **_: [{"file_type": "x"}]
        )

        agent.ask("list types")

        assert len(agent.last_trace) == 1
        assert agent.last_trace[0]["tool"] == "list_file_types"


# ── unit tests — planner skeleton ────────────────────────────────────────────


class TestCBOAgentPlanner:
    def test_planner_disabled_by_default(self, agent, patched_genai):
        """Without enable_planner, ask() does not call models.generate_content."""
        chat = _chat_mock(patched_genai)
        chat.send_message.return_value = _make_text_response("ok")
        agent.ask("hello")
        client = patched_genai.Client.return_value
        client.models.generate_content.assert_not_called()
        assert agent.last_plan is None

    def test_parse_plan_text_extracts_json_fence(self):
        text = (
            "Here is the plan:\n"
            "```json\n"
            "{\"file_type\": \"medicare\", \"intent\": \"comparison\", "
            "\"steps\": [{\"tool\": \"summarize_file_type\"}]}\n"
            "```"
        )
        parsed = CBOAgent._parse_plan_text(text)
        assert parsed["file_type"] == "medicare"
        assert parsed["intent"] == "comparison"
        assert parsed["steps"][0]["tool"] == "summarize_file_type"
        assert parsed["raw"] == text

    def test_parse_plan_text_returns_raw_on_invalid_json(self):
        parsed = CBOAgent._parse_plan_text("not a plan at all")
        assert parsed == {"raw": "not a plan at all", "steps": []}

    def test_enabled_planner_calls_generate_content_and_prefixes_prompt(
        self, monkeypatch, patched_genai
    ):
        monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        client = patched_genai.Client.return_value

        # Planner response — return a JSON-fenced plan.
        plan_text = (
            "```json\n"
            "{\"file_type\": \"medicaid\", \"intent\": \"chart\", \"steps\": []}\n"
            "```"
        )
        client.models.generate_content.return_value = _make_text_response(plan_text)

        chat = _chat_mock(patched_genai)
        chat.send_message.return_value = _make_text_response("done")

        a = CBOAgent(enable_planner=True)
        a.ask("chart medicaid enrollment")

        # Planner call happened
        client.models.generate_content.assert_called_once()
        assert a.last_plan is not None
        assert a.last_plan["file_type"] == "medicaid"

        # The executor saw a prompt that begins with the plan block
        sent = chat.send_message.call_args_list[0].args[0]
        assert "PLAN (advisory" in sent
        assert "USER QUESTION: chart medicaid enrollment" in sent

    def test_planner_failure_returns_error_dict_but_ask_still_works(
        self, monkeypatch, patched_genai
    ):
        monkeypatch.setattr("src.llm_agent.load_dotenv", lambda: None)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        client = patched_genai.Client.return_value
        client.models.generate_content.side_effect = RuntimeError("transport down")

        chat = _chat_mock(patched_genai)
        chat.send_message.return_value = _make_text_response("answer anyway")

        a = CBOAgent(enable_planner=True)
        answer = a.ask("any question")

        assert answer == "answer anyway"
        assert a.last_plan == {"error": "transport down", "raw": None}


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
