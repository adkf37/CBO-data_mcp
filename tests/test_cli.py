from __future__ import annotations

from pathlib import Path

import pandas as pd

from main import CBOCLI


class FakeAgent:
    def ask(self, question: str) -> str:
        return f"answer: {question}"


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
    rows = pd.read_csv(exported).to_dict(orient="records")
    assert rows == [{"question": "What is Medicaid?", "answer": "answer: What is Medicaid?"}]


def test_cli_quit_command_exits_cleanly(monkeypatch):
    prompts = iter(["/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))

    cli = CBOCLI(agent=FakeAgent(), width=120)
    assert cli.run() == 0
