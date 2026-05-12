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
    "You are a helpful analyst of U.S. Congressional Budget Office (CBO) data. "
    "When answering questions, always cite the file type and vintage used to "
    "derive each figure. "
    "Use the available tools to retrieve the data you need before answering. "
    "If multiple vintages or file types are relevant, compare them explicitly."
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

    def ask(self, question: str) -> str:
        """Resolve a natural-language question about CBO data.

        Runs the Gemini tool-calling loop, dispatching each function call
        through the tool registry and feeding the results back to the model
        until it produces a final text answer or the iteration cap is reached.

        Parameters
        ----------
        question:
            Natural-language query to resolve using CBO projection data.

        Returns
        -------
        str
            The model's final text answer with tool-sourced data cited.
        """
        chat = self._model.start_chat()
        response = chat.send_message(question)

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
