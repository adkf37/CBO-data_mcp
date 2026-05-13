from __future__ import annotations

from pathlib import Path

from src.eval_runner import EvalQuestion, answer_failures, load_eval_suite, tools_match


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