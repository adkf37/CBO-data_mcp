from __future__ import annotations

from pathlib import Path

import pandas as pd

from main import CBOCLI


class FakeAgent:
    def __init__(self) -> None:
        self.last_trace: list[dict] = []
        self.reset_called = False

    def ask(self, question: str) -> str:
        self.last_trace = [{"tool": "list_file_types", "args": {}, "result": []}]
        return f"answer: {question}"

    def reset(self) -> None:
        self.reset_called = True
        self.last_trace = []


def test_cli_smoke_processes_question_export_and_quit(monkeypatch, capsys, tmp_path: Path):
    prompts = iter(["What is Medicaid?", "/export out.csv", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))
    monkeypatch.chdir(tmp_path)

    cli = CBOCLI(agent=FakeAgent(), width=120)
    code = cli.run()

    assert code == 0
    out = capsys.readouterr().out
    assert "CBO Data MCP CLI" in out
    assert "answer: What is Medicaid?" in out
    assert "Exported 1 row(s)" in out

    exported = tmp_path / "exports" / "out.csv"
    assert exported.exists()
    rows = pd.read_csv(exported, comment="#").to_dict(orient="records")
    assert rows == [{"question": "What is Medicaid?", "answer": "answer: What is Medicaid?"}]


def test_cli_quit_command_exits_cleanly(monkeypatch):
    prompts = iter(["/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))

    cli = CBOCLI(agent=FakeAgent(), width=120)
    assert cli.run() == 0


def test_cli_trace_and_reset_commands(monkeypatch, capsys):
    prompts = iter(["What is X?", "/trace", "/reset", "/trace", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))

    agent = FakeAgent()
    cli = CBOCLI(agent=agent, width=120)
    assert cli.run() == 0
    out = capsys.readouterr().out

    assert "list_file_types" in out
    assert "Conversation memory cleared" in out
    assert "No tool calls" in out
    assert agent.reset_called is True


def test_cli_chart_command_dispatches_to_tool(monkeypatch, capsys, tmp_path: Path):
    captured: dict = {}

    def fake_chart(file_type, **kwargs):
        captured["file_type"] = file_type
        captured["kwargs"] = kwargs
        return {
            "file_path": str(tmp_path / "chart.png"),
            "chart_kind": kwargs.get("kind", "line"),
            "point_count": 3,
        }

    monkeypatch.setattr("main.chart_projection", fake_chart)
    prompts = iter(["/chart medicaid value kind=line year_start=2025", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))

    cli = CBOCLI(agent=FakeAgent(), width=120)
    assert cli.run() == 0
    out = capsys.readouterr().out

    assert captured["file_type"] == "medicaid"
    assert captured["kwargs"]["metric"] == "value"
    assert captured["kwargs"]["kind"] == "line"
    assert captured["kwargs"]["year_start"] == 2025
    assert "Saved line chart" in out
