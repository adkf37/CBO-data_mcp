from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass, field
from typing import Protocol

from src.llm_agent import CBOAgent
from src.mcp_tools import chart_projection, export_csv, list_file_types, list_vintages

try:  # pragma: no cover - platform-specific
    import readline  # noqa: F401
except Exception:  # noqa: BLE001, pragma: no cover - fallback to plain input()
    readline = None  # type: ignore[assignment]


DEFAULT_WIDTH = 120


class AgentProtocol(Protocol):
    def ask(self, question: str) -> str: ...


@dataclass
class CLIState:
    last_question: str = ""
    last_answer: str = ""
    last_rows: list[dict] = field(default_factory=list)


class CBOCLI:
    def __init__(self, agent: AgentProtocol | None, *, width: int = DEFAULT_WIDTH) -> None:
        self.agent = agent
        self.width = width
        self.state = CLIState()

    def run(self) -> int:
        self._print_banner()
        while True:
            try:
                raw = input("cbo> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                return 0

            if not raw:
                continue

            if raw in {"/quit", "/exit"}:
                print("Goodbye.")
                return 0
            if raw == "/help":
                self._print_help()
                continue
            if raw == "/types":
                self._handle_types()
                continue
            if raw.startswith("/vintages"):
                self._handle_vintages(raw)
                continue
            if raw.startswith("/export"):
                self._handle_export(raw)
                continue
            if raw.startswith("/chart"):
                self._handle_chart(raw)
                continue
            if raw == "/reset":
                self._handle_reset()
                continue
            if raw == "/trace":
                self._handle_trace()
                continue

            self._handle_question(raw)

    def _print_banner(self) -> None:
        print("CBO Data MCP CLI")
        print("Ask a question or use /help. Type /quit to exit.")
        if self.agent is None:
            print("Note: GEMINI_API_KEY is not configured; natural-language queries are disabled.")

    def _print_help(self) -> None:
        lines = [
            "Commands:",
            "  /help                              Show this help message",
            "  /types                             List available CBO file types",
            "  /vintages <file_type>              List vintages for one file type",
            "  /export [filename]                 Export the last question/answer to CSV",
            "  /chart <file_type> <metric> [k=v]  Render a PNG chart (kind=line|bar, program=, vintage=, year_start=, year_end=)",
            "  /reset                             Clear the agent's conversation memory",
            "  /trace                             Show the tools called for the last question",
            "  /quit or /exit                     Exit the CLI",
            "Example:",
            "  How many people are projected to be enrolled in Medicaid in 2029?",
            "  /chart medicaid value kind=line vintage=2025-01",
        ]
        self._print_wrapped("\n".join(lines))

    def _handle_types(self) -> None:
        result = list_file_types()
        if isinstance(result, dict) and "error" in result:
            self._print_wrapped(f"Error: {result['error']}")
            return
        names = ", ".join(row.get("file_type", "") for row in result if row.get("file_type"))
        self._print_wrapped(names or "No file types found.")

    def _handle_vintages(self, raw: str) -> None:
        parts = raw.split(maxsplit=1)
        if len(parts) < 2:
            self._print_wrapped("Usage: /vintages <file_type>")
            return
        result = list_vintages(parts[1])
        if "error" in result:
            self._print_wrapped(f"Error: {result['error']}")
            return
        vintages = ", ".join(result.get("vintages", []))
        self._print_wrapped(vintages or f"No vintages found for '{parts[1]}'.")

    def _handle_export(self, raw: str) -> None:
        if not self.state.last_rows:
            self._print_wrapped("No previous query result available to export.")
            return
        parts = raw.split(maxsplit=1)
        filename = parts[1].strip() if len(parts) > 1 else None
        result = export_csv(
            self.state.last_rows,
            filename=filename,
            file_type="cli_session",
            query_params={"question": self.state.last_question or "latest_query"},
        )
        if "error" in result:
            self._print_wrapped(f"Error: {result['error']}")
            return
        self._print_wrapped(f"Exported {result['row_count']} row(s) to {result['file_path']}")

    def _handle_question(self, question: str) -> None:
        if self.agent is None:
            self._print_wrapped(
                "Natural-language queries are unavailable until GEMINI_API_KEY is configured."
            )
            return
        try:
            answer = self.agent.ask(question)
        except Exception as exc:  # noqa: BLE001
            self._print_wrapped(f"Sorry, I couldn't process that request: {exc}")
            return
        self.state.last_question = question
        self.state.last_answer = answer
        self.state.last_rows = [{"question": question, "answer": answer}]
        self._print_wrapped(answer)

    def _handle_chart(self, raw: str) -> None:
        parts = raw.split()[1:]
        if len(parts) < 2:
            self._print_wrapped(
                "Usage: /chart <file_type> <metric> [kind=line|bar] [program=...] "
                "[vintage=...] [year_start=...] [year_end=...] [group_by=...]"
            )
            return
        file_type, metric = parts[0], parts[1]
        kwargs: dict[str, object] = {}
        for token in parts[2:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            if key in {"year_start", "year_end"}:
                try:
                    kwargs[key] = int(value)
                except ValueError:
                    self._print_wrapped(f"Invalid integer for {key}: {value}")
                    return
            else:
                kwargs[key] = value
        result = chart_projection(file_type, metric=metric, **kwargs)
        if "error" in result:
            self._print_wrapped(f"Error: {result['error']}")
            return
        self._print_wrapped(
            f"Saved {result['chart_kind']} chart with {result['point_count']} point(s) "
            f"to {result['file_path']}"
        )

    def _handle_reset(self) -> None:
        self.state = CLIState()
        if self.agent is not None and hasattr(self.agent, "reset"):
            try:
                self.agent.reset()
            except Exception as exc:  # noqa: BLE001
                self._print_wrapped(f"Reset warning: {exc}")
        self._print_wrapped("Conversation memory cleared.")

    def _handle_trace(self) -> None:
        if self.agent is None or not hasattr(self.agent, "last_trace"):
            self._print_wrapped("No trace available.")
            return
        trace = getattr(self.agent, "last_trace", []) or []
        if not trace:
            self._print_wrapped("No tool calls were made for the last question.")
            return
        for i, step in enumerate(trace, 1):
            args_preview = ", ".join(f"{k}={v!r}" for k, v in step.get("args", {}).items())
            self._print_wrapped(f"{i}. {step.get('tool')}({args_preview})")

    def _print_wrapped(self, text: str) -> None:
        for line in text.splitlines() or [""]:
            print(textwrap.fill(line, width=self.width))


def build_cli() -> CBOCLI:
    width = int(os.environ.get("CBO_CLI_WIDTH", DEFAULT_WIDTH))
    try:
        agent: AgentProtocol | None = CBOAgent()
    except Exception:  # noqa: BLE001
        agent = None
    return CBOCLI(agent=agent, width=width)


def main() -> int:
    return build_cli().run()


if __name__ == "__main__":
    raise SystemExit(main())
