"""
llm_agent.py — Gemini 2.5 Flash Integration (google-genai SDK).

CBOAgent wires the Google Gemini 2.5 Flash model to the MCP tool registry so
that natural-language user queries are automatically resolved by calling the
appropriate tools and returning a coherent, cited answer.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.tool_registry import get_gemini_tool_declarations, get_tool

log = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 10

_PLANNER_SYSTEM_PROMPT = (
    "You are the PLANNER stage for a CBO baseline data agent. You DO NOT call "
    "any tools yourself. Given a user question, emit a short structured plan "
    "describing how the EXECUTOR stage should answer it.\n\n"
    "Return a single JSON object inside ```json fences with these keys:\n"
    "  - file_type: best guess at the dataset (e.g. 'medicaid', 'medicare', "
    "'snap', 'ssdi', 'unemployment', 'socialsecurity', 'healthinsurance', or "
    "null if uncertain).\n"
    "  - intent: one of 'discovery', 'lookup', 'chart', 'comparison', "
    "'aggregation', 'growth', 'availability', 'citation', 'other'.\n"
    "  - steps: ordered list of {tool, why} entries naming MCP tools to call "
    "(list_file_types, list_vintages, summarize_file_type, get_projection, "
    "aggregate_metric, top_n, growth_rate, compare_vintages, chart_projection, "
    "search_programs, export_csv).\n"
    "  - ambiguity_notes: free text flagging unit/category/vintage traps the "
    "executor must resolve (e.g. mixed units in Medicaid, missing vintage, "
    "totals-vs-subcomponents).\n"
    "Keep the plan under 200 words. Do NOT answer the question, just plan."
)

_SYSTEM_PROMPT = (
    "You are a careful analyst of U.S. Congressional Budget Office (CBO) baseline "
    "projection data. Your job is to answer the user's question with numbers "
    "drawn from the available MCP tools — never invent figures.\n\n"
    "DATA SHAPE — IMPORTANT:\n"
    "Most CBO files have columns (program, category, fiscal_year, value, unit, "
    "vintage). A single `program` (e.g. 'Medicaid') typically contains MANY "
    "rows for the same year across different `category` values reporting in "
    "different `unit` values — for example Medicaid 2026-02 has rows for "
    "'Estimated Outlays' (Billions of dollars), 'Total Enrolled Within a "
    "Fiscal Year' (Millions of people), and per-enrollee dollar figures "
    "(Dollars per enrollee). Summing 'value' across these is meaningless.\n\n"
    "Common file type aliases: SNAP -> `snap`; SSDI -> `ssdi`; Unemployment "
    "Insurance or UI -> `unemployment`; Social Security -> `socialsecurity`; "
    "health insurance -> `healthinsurance`. Available program files also include "
    "`medicaid`, `medicare`, `snap`, `ssdi`, and `unemployment`. When uncertain, "
    "call `list_file_types` or `list_vintages` rather than answering from memory.\n\n"
    "Common measure mappings after discovery: Medicaid enrollment -> "
    "category='Total Enrolled Within a Fiscal Year', unit='Millions of people'; "
    "Medicare spending/outlays -> category='Outlays', unit='Billions of dollars'; "
    "SNAP outlays -> category='Outlays' when present, prefer unit='Billions of dollars' "
    "for recent vintages; SSDI beneficiary counts -> category='Total Beneficiaries', "
    "unit='Thousands of people'; Unemployment Insurance outlays -> use the total "
    "benefit/outlay category discovered by `summarize_file_type` and cite the native unit.\n\n"
    "Tool-use playbook:\n"
    "1. Do not answer data-availability, category/unit, latest-vintage, chart, "
    "lookup, growth, or comparison questions from memory. Call the relevant "
    "tool even if the answer seems obvious.\n"
    "2. Whenever the user names a measure that is not literally a column "
    "(e.g. 'enrollment', 'outlays', 'spending', 'beneficiaries'), call "
    "`summarize_file_type` FIRST to see `categories`, `units`, and "
    "`categories_by_unit`. Pick the category + unit that match the user's "
    "intent (e.g. 'enrollment' → unit='Millions of people' → category like "
    "'Total Enrolled Within a Fiscal Year').\n"
    "3. Always pass `category=` and/or `unit=` to `chart_projection`, "
    "`compare_vintages`, `aggregate_metric`, `top_n`, and `growth_rate` so the slice is "
    "unit-consistent. If a tool returns a 'mixed units' error, read the "
    "`available_units` / `available_categories` it returns and retry with the "
    "right filter.\n"
    "4. Use `get_projection` for raw row-level lookups, `aggregate_metric` for "
    "totals/averages/group_by, `top_n` for rankings, `growth_rate` for "
    "year-over-year change/CAGR, and `compare_vintages` for projection "
    "revisions.\n"
    "5. When the user asks for the 'most recent' or 'latest' projection, call "
    "`list_vintages` and pick the lexically largest vintage (vintages are "
    "YYYY-MM strings).\n"
    "6. CHART FIRST — call `chart_projection` automatically (without being "
    "asked) whenever the user's question involves: (a) data across multiple "
    "years or a time series, (b) a comparison of two or more vintages, (c) "
    "trends, growth, or projections for any program. Only skip the chart if "
    "the user explicitly asks for a table or raw numbers only. When you do "
    "produce text numbers, still generate the chart alongside.\n"
    "Choose chart kind: kind='line' for time series and vintage comparisons "
    "(default); kind='bar' for single-year program rankings; "
    "kind='stacked_bar' for composition questions — e.g. when the user asks "
    "to see how spending breaks down across programs or categories over time "
    "(stack by program or category, x-axis = year). DO NOT mention any file "
    "path in your answer — the chart renders in the browser with a download button.\n"
    "7. For multi-vintage chart requests such as 'compare baselines in one "
    "chart' or 'separate lines for each vintage', use `chart_projection` with "
    "`group_by='vintage'`. For explicit vintages, pass `vintages=[...]` and do "
    "not claim charting is limited to one vintage. For 'since 2023', pass "
    "`vintage_start='2023'`.\n"
    "8. Always cite the file_type, vintage, category, and unit behind each "
    "figure in your answer.\n"
    "9. If a tool returns an error, read the message, adjust parameters, and "
    "try again before giving up.\n"
    "10. Treat the conversation as multi-turn: follow-up questions may reuse "
    "the previously identified file type, category, or vintage.\n"
    "11. TOTALS vs SUBCOMPONENTS: rows in the data carry an `is_total` flag. "
    "Most aggregation tools (`aggregate_metric`, `top_n`, `growth_rate`, "
    "`chart_projection`) already EXCLUDE `is_total=true` rows by default to "
    "prevent double counting a 'Total Medicare benefits' line on top of its "
    "Part A / Part B / Part D components. When the user explicitly wants the "
    "published total line (e.g. 'show me the bottom-line total'), either "
    "(a) pass `category=` to narrow to just that total row and set "
    "`include_totals=true`, or (b) leave `include_totals=false` and let the "
    "sum of subcomponents stand in for the total. Never mix the two — if "
    "you find yourself summing 'Part A' + 'Part B' + 'Part D' + 'Total "
    "Medicare benefits' in the same call you are double counting."
    "\n12. SOURCE CITATIONS: tool results now include a `sources` list with "
    "`source_file` (the originating CBO workbook, e.g. "
    "`51302-2026-02-medicare.xlsx`), `source_sheet`, and `vintage`. When you "
    "report a figure, name the source_file at least once per answer so the "
    "user can verify against the published CBO baseline."
)


class CBOAgent:
    """Gemini 2.5 Flash agent wired to the CBO MCP tool registry.

    Parameters
    ----------
    api_key:
        Gemini API key.  When *None* (default), the key is read from the
        ``GEMINI_API_KEY`` environment variable after loading any ``.env``
        file via python-dotenv.  The key is **never** hardcoded or logged.
    """

    def __init__(self, api_key: str | None = None, *, enable_planner: bool = False) -> None:
        load_dotenv()
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Provide it via the GEMINI_API_KEY environment variable or a .env file."
            )

        self._client = genai.Client(api_key=resolved_key)
        self._tool = types.Tool(function_declarations=get_gemini_tool_declarations())
        self._chat: Any = None
        self.last_trace: list[dict[str, Any]] = []
        self.last_plan: dict[str, Any] | None = None
        self._enable_planner = enable_planner

    def reset(self) -> None:
        """Clear conversation history so the next ``ask`` starts fresh."""
        self._chat = None
        self.last_trace = []
        self.last_plan = None

    def _ensure_chat(self) -> Any:
        if self._chat is None:
            self._chat = self._client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    tools=[self._tool],
                ),
            )
        return self._chat

    def plan(self, question: str) -> dict[str, Any]:
        """Produce a lightweight structured plan for ``question``.

        Performs a stateless Gemini call with the planner system prompt and
        returns the parsed plan dict. On any parsing/transport failure a
        minimal plan with the raw model text is returned so the executor can
        still proceed. This is a deliberately small skeleton — it does not
        execute tools; it only suggests them.
        """
        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=_PLANNER_SYSTEM_PROMPT,
                ),
            )
            text = self._extract_text(response)
        except Exception as exc:  # noqa: BLE001
            log.warning("Planner call failed: %s", exc)
            return {"error": str(exc), "raw": None}

        return self._parse_plan_text(text)

    @staticmethod
    def _parse_plan_text(text: str) -> dict[str, Any]:
        """Extract a JSON plan from ``text`` (allowing ```json fences)."""
        if not text:
            return {"raw": "", "steps": []}
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        candidate = match.group(1) if match else text.strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                parsed.setdefault("raw", text)
                return parsed
        except (ValueError, json.JSONDecodeError):
            pass
        return {"raw": text, "steps": []}

    def ask(self, question: str) -> str:
        """Resolve a natural-language question about CBO data.

        Runs the Gemini tool-calling loop, dispatching each function call
        through the tool registry and feeding the results back to the model
        until it produces a final text answer or the iteration cap is reached.
        Conversation state persists across calls; use :meth:`reset` to clear it.

        When the agent was constructed with ``enable_planner=True``, a separate
        planning call is made first to produce a structured plan (stored on
        :attr:`last_plan`) that is prepended to the executor's first message.
        """
        prompt = question
        if self._enable_planner:
            self.last_plan = self.plan(question)
            plan_blob = json.dumps(self.last_plan, indent=2, default=str)
            prompt = (
                f"PLAN (advisory, produced by planner stage):\n```json\n{plan_blob}\n```\n\n"
                f"USER QUESTION: {question}"
            )

        chat = self._ensure_chat()
        response = chat.send_message(prompt)
        self.last_trace = []

        for _ in range(_MAX_TOOL_ITERATIONS):
            candidates = getattr(response, "candidates", [])
            if not candidates:
                return self._extract_text(response)

            fn_calls = [
                p.function_call
                for p in candidates[0].content.parts
                if getattr(p, "function_call", None) and p.function_call.name
            ]

            if not fn_calls:
                return self._extract_text(response)

            fn_response_parts: list[types.Part] = []
            for fc in fn_calls:
                name = fc.name
                args = dict(fc.args) if fc.args else {}
                log.debug("Tool call: %s(%s)", name, args)
                try:
                    result = get_tool(name)(**args)
                except Exception as exc:  # noqa: BLE001
                    result = {"error": str(exc)}
                self.last_trace.append({"tool": name, "args": args, "result": result})
                fn_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=name,
                            response={"result": result},
                        )
                    )
                )

            response = chat.send_message(fn_response_parts)

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
        for candidate in getattr(response, "candidates", []):
            for part in getattr(candidate.content, "parts", []):
                try:
                    if part.text:
                        parts.append(part.text)
                except Exception:  # noqa: BLE001
                    pass
        return "\n".join(parts) if parts else "(no response)"
