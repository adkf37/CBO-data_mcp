from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from src.eval_runner import EvalQuestion, WebEvalAgent, answer_failures, evaluate_question, load_eval_suite, tools_match


def test_tools_match_accepts_ordered_subsequence():
    assert tools_match(
        ["list_vintages", "summarize_file_type", "chart_projection"],
        ["list_vintages", "summarize_file_type", "chart_projection"],
    )
    assert tools_match(
        ["list_vintages", "summarize_file_type", "chart_projection"],
        ["list_vintages", "summarize_file_type", "get_projection", "chart_projection"],
    )
    assert not tools_match(
        ["list_vintages", "summarize_file_type", "chart_projection"],
        ["summarize_file_type", "list_vintages", "chart_projection"],
    )


def test_answer_failures_checks_contains_and_regex():
    question = EvalQuestion(
        id="1",
        prompt="demo",
        answer_contains=["2026-02", "Millions of people"],
        answer_regex=[r"\b2029\b"],
    )
    assert answer_failures(question, "Using 2026-02 in Millions of people for 2029.") == []
    failures = answer_failures(question, "Using 2025-01 in dollars.")
    assert any("2026-02" in failure for failure in failures)
    assert any("Millions of people" in failure for failure in failures)
    assert any("2029" in failure for failure in failures)


def test_load_eval_suite_parses_real_cbo_suite():
    suite_path = Path("evals/cbo_qa.xml")
    metadata, questions = load_eval_suite(suite_path)

    assert metadata["name"] == "cbo_data_mcp"
    assert len(questions) >= 18
    prompts = {question.id: question.prompt for question in questions}
    assert prompts["3"] == (
        "Compare Medicaid enrollment across the 2023-05, 2024-06, and 2026-02 baselines in one chart."
    )
    assert any(
        question.expected_tools == ["list_vintages", "summarize_file_type", "chart_projection"]
        for question in questions
    )


def test_web_eval_agent_uses_chat_api_and_records_trace(monkeypatch):
    session = MagicMock()
    health_response = MagicMock()
    health_response.json.return_value = {"status": "ok", "api_key_configured": True}
    health_response.raise_for_status.return_value = None
    chat_response = MagicMock()
    chat_response.json.return_value = {
        "answer": "Done",
        "session_id": "abc123",
        "tool_calls": [{"name": "chart_projection", "args": {"file_type": "medicaid"}}],
    }
    chat_response.raise_for_status.return_value = None
    session.get.return_value = health_response
    session.post.return_value = chat_response
    monkeypatch.setattr("src.eval_runner.requests.Session", lambda: session)

    agent = WebEvalAgent("https://example.test")
    assert agent.healthcheck()["api_key_configured"] is True
    assert agent.ask("hello") == "Done"
    assert agent.last_trace == [{"tool": "chart_projection", "args": {"file_type": "medicaid"}}]


def test_web_eval_agent_reset_clears_session(monkeypatch):
    session = MagicMock()
    chat_response = MagicMock()
    chat_response.json.return_value = {"answer": "Done", "session_id": "abc123", "tool_calls": []}
    chat_response.raise_for_status.return_value = None
    session.post.return_value = chat_response
    monkeypatch.setattr("src.eval_runner.requests.Session", lambda: session)

    agent = WebEvalAgent("https://example.test")
    agent.ask("hello")
    agent.reset()

    assert agent.last_trace == []
    assert session.post.call_args_list[-1].kwargs["json"] == {"session_id": "abc123"}


def test_web_eval_agent_includes_response_body_in_http_errors(monkeypatch):
    session = MagicMock()
    chat_response = MagicMock()
    chat_response.status_code = 500
    chat_response.text = '{"error":"boom"}'
    chat_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    session.post.return_value = chat_response
    monkeypatch.setattr("src.eval_runner.requests.Session", lambda: session)

    agent = WebEvalAgent("https://example.test")
    with pytest.raises(RuntimeError, match=r'HTTP 500 from https://example.test/api/chat: \{"error":"boom"\}'):
        agent.ask("hello")


def test_evaluate_question_returns_failed_result_on_agent_error():
    class BrokenAgent:
        last_trace = [{"tool": "list_vintages", "args": {}}]

        def ask(self, question: str) -> str:
            raise RuntimeError("upstream failed")

    result = evaluate_question(
        BrokenAgent(),
        EvalQuestion(id="2", prompt="Chart Medicaid enrollment from 2025 to 2034 in the latest projection."),
    )

    assert result["passed"] is False
    assert result["trace_tools"] == ["list_vintages"]
    assert result["failures"] == ["agent error: upstream failed"]


def test_evaluate_question_resets_agent_before_running():
    class ResettableAgent:
        def __init__(self) -> None:
            self.last_trace = []
            self.reset_called = False

        def reset(self) -> None:
            self.reset_called = True
            self.last_trace = []

        def ask(self, question: str) -> str:
            self.last_trace = [{"tool": "summarize_file_type", "args": {}}]
            return "Millions of people"

    agent = ResettableAgent()
    result = evaluate_question(
        agent,
        EvalQuestion(
            id="1",
            prompt="What units are available?",
            tool="summarize_file_type",
            answer_contains=["Millions of people"],
        ),
    )

    assert agent.reset_called is True
    assert result["passed"] is True
