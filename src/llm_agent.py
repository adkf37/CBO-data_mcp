"""
llm_agent.py — Task 04: Gemini 2.5 Flash Integration.

CBOAgent wires the Google Gemini 2.5 Flash model to the MCP tool registry so
that natural-language user queries are automatically resolved by calling the
appropriate tools and returning a coherent, cited answer.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

from src.tool_registry import get_gemini_tool_declarations, get_tool

log = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 10

_SYSTEM_PROMPT = (
    "You are a careful analyst of U.S. Congressional Budget Office (CBO) baseline "
    "projection data. Your job is to answer the user's question with numbers "
    "drawn from the available MCP tools — never invent figures.\n\n"
    "Tool-use playbook:\n"
    "1. If you do not know which file type or column to query, call "
    "`list_file_types` and then `summarize_file_type` to learn the schema, year "
    "range, vintages, and program names before issuing analytical calls.\n"
    "2. Use `get_projection` for raw row-level lookups, `aggregate_metric` for "
    "totals/averages/group_by, `top_n` for rankings, `growth_rate` for "
    "year-over-year change/CAGR, and `compare_vintages` for projection revisions.\n"
    "3. Chain tools when needed (for example summarize → aggregate → top_n) "
    "instead of guessing.\n"
    "4. When the user asks for a chart/plot/visualization, call "
    "`chart_projection` and report the saved file path.\n"
    "5. Always cite the file_type and vintage that produced each figure, and "
    "state units (millions, billions, percent of GDP, etc.) when the column "
    "name implies them.\n"
    "6. If a tool returns an error, read the message, adjust parameters, and try "
    "again before giving up.\n"
    "7. Treat the conversation as multi-turn: follow-up questions may reuse the "
    "previously identified file type or program."
)


def _build_genai_tools() -> list[Any]:
    """Convert MCP tool declarations to a Gemini SDK Tool object list."""
    type_map = {
        "string": genai.protos.Type.STRING,
        "integer": genai.protos.Type.INTEGER,
        "number": genai.protos.Type.NUMBER,
        "boolean": genai.protos.Type.BOOLEAN,
        "array": genai.protos.Type.ARRAY,
        "object": genai.protos.Type.OBJECT,
    }

    function_declarations: list[Any] = []
    for decl in get_gemini_tool_declarations():
        params = decl.get("parameters", {})
        props: dict[str, Any] = {}
        for prop_name, prop_schema in params.get("properties", {}).items():
            raw_type = prop_schema.get("type", "string")
            proto_type = type_map.get(raw_type, genai.protos.Type.STRING)
            props[prop_name] = genai.protos.Schema(type=proto_type)

        fd = genai.protos.FunctionDeclaration(
            name=decl["name"],
            description=decl.get("description", ""),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties=props,
                required=params.get("required", []),
            ),
        )
        function_declarations.append(fd)

    return [genai.protos.Tool(function_declarations=function_declarations)]


class CBOAgent:
    """Gemini 2.5 Flash agent wired to the CBO MCP tool registry.

    Parameters
    ----------
    api_key:
        Gemini API key.  When *None* (default), the key is read from the
        ``GEMINI_API_KEY`` environment variable after loading any ``.env``
        file via python-dotenv.  The key is **never** hardcoded or logged.
    """

    def __init__(self, api_key: str | None = None) -> None:
        load_dotenv()
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Provide it via the GEMINI_API_KEY environment variable or a .env file."
            )

        genai.configure(api_key=resolved_key)

        tools = _build_genai_tools()
        self._model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=tools,
            system_instruction=_SYSTEM_PROMPT,
        )
        self._chat: Any = None
        self.last_trace: list[dict[str, Any]] = []

    def reset(self) -> None:
        """Clear conversation history so the next ``ask`` starts fresh."""
        self._chat = None
        self.last_trace = []

    def _ensure_chat(self) -> Any:
        if self._chat is None:
            self._chat = self._model.start_chat()
        return self._chat

    def ask(self, question: str) -> str:
        """Resolve a natural-language question about CBO data.

        Runs the Gemini tool-calling loop, dispatching each function call
        through the tool registry and feeding the results back to the model
        until it produces a final text answer or the iteration cap is reached.
        Conversation state persists across calls; use :meth:`reset` to clear it.

        Parameters
        ----------
        question:
            Natural-language query to resolve using CBO projection data.

        Returns
        -------
        str
            The model's final text answer with tool-sourced data cited.
        """
        chat = self._ensure_chat()
        response = chat.send_message(question)
        self.last_trace = []

        for _ in range(_MAX_TOOL_ITERATIONS):
            fn_calls = [
                part.function_call
                for part in response.parts
                if part.function_call.name
            ]

            if not fn_calls:
                return self._extract_text(response)

            fn_responses: list[Any] = []
            for fn_call in fn_calls:
                name = fn_call.name
                args = dict(fn_call.args)
                log.debug("Tool call: %s(%s)", name, args)
                try:
                    result = get_tool(name)(**args)
                except Exception as exc:  # noqa: BLE001
                    result = {"error": str(exc)}
                self.last_trace.append({"tool": name, "args": args, "result": result})

                fn_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=name,
                            response={"result": result},
                        )
                    )
                )

            response = chat.send_message(fn_responses)

        log.warning("Reached maximum tool-call iterations (%d).", _MAX_TOOL_ITERATIONS)
        return self._extract_text(response)

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Best-effort extraction of plain text from a Gemini response."""
        try:
            text = response.text
            if text:
                return text
        except Exception:  # noqa: BLE001
            pass
        parts: list[str] = []
        for part in getattr(response, "parts", []):
            try:
                if part.text:
                    parts.append(part.text)
            except Exception:  # noqa: BLE001
                pass
        return "\n".join(parts) if parts else "(no response)"
