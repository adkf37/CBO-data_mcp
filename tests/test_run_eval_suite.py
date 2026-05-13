from __future__ import annotations

import argparse
from unittest.mock import MagicMock

from scripts.run_eval_suite import _filter_questions, main
from src.eval_runner import EvalQuestion


def test_filter_questions_respects_question_ids_and_limit():
    args = argparse.Namespace(question_id=["3", "1"], limit=1)
    questions = [
        EvalQuestion(id="1", prompt="one"),
        EvalQuestion(id="2", prompt="two"),
        EvalQuestion(id="3", prompt="three"),
    ]

    selected = _filter_questions(args, questions)

    assert [question.id for question in selected] == ["1"]


def test_main_returns_blocked_without_api_key(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.run_eval_suite.parse_args",
        lambda: argparse.Namespace(
            suite="evals/cbo_qa.xml",
            limit=None,
            question_id=None,
            fail_fast=False,
            json=False,
            base_url=None,
            validate_only=False,
        ),
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 2
    assert "Status: blocked" in output
    assert "--validate-only" in output


def test_main_validate_only_returns_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.run_eval_suite.parse_args",
        lambda: argparse.Namespace(
            suite="evals/cbo_qa.xml",
            limit=2,
            question_id=None,
            fail_fast=False,
            json=True,
            base_url=None,
            validate_only=True,
        ),
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"status": "validated"' in output
    assert '"question_count": 2' in output


def test_main_uses_live_site_when_base_url_present(monkeypatch, capsys):
    fake_agent = MagicMock()
    fake_agent.healthcheck.return_value = {"status": "ok", "api_key_configured": True}
    monkeypatch.setattr(
        "scripts.run_eval_suite.parse_args",
        lambda: argparse.Namespace(
            suite="evals/cbo_qa.xml",
            limit=1,
            question_id=None,
            fail_fast=False,
            json=False,
            base_url="https://example.test",
            validate_only=False,
        ),
    )
    monkeypatch.setattr("scripts.run_eval_suite.WebEvalAgent", lambda base_url: fake_agent)
    monkeypatch.setattr(
        "scripts.run_eval_suite.run_eval_suite",
        lambda *args, **kwargs: {
            "suite": {"name": "cbo_data_mcp"},
            "passed": 1,
            "failed": 0,
            "question_count": 1,
            "results": [{"id": "1", "prompt": "demo", "passed": True, "failures": [], "trace_tools": []}],
        },
    )

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Suite: cbo_data_mcp" in output
    assert "Passed: 1/1" in output


def test_main_blocks_when_live_site_reports_no_api_key(monkeypatch, capsys):
    fake_agent = MagicMock()
    fake_agent.healthcheck.return_value = {"status": "ok", "api_key_configured": False}
    monkeypatch.setattr(
        "scripts.run_eval_suite.parse_args",
        lambda: argparse.Namespace(
            suite="evals/cbo_qa.xml",
            limit=None,
            question_id=None,
            fail_fast=False,
            json=False,
            base_url="https://example.test",
            validate_only=False,
        ),
    )
    monkeypatch.setattr("scripts.run_eval_suite.WebEvalAgent", lambda base_url: fake_agent)

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 2
    assert "api_key_configured=false" in output