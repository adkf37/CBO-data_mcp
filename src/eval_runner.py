"""Utilities for loading and running prompt-based eval suites."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Protocol

import requests
from requests import HTTPError

from src.llm_agent import CBOAgent


class EvalAgent(Protocol):
    last_trace: list[dict[str, Any]]

    def ask(self, question: str) -> str: ...


class WebEvalAgent:
    """Minimal adapter for running evals through the deployed web app."""

    def __init__(self, base_url: str, *, timeout: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._chat_url = f"{self._base_url}/api/chat"
        self._health_url = f"{self._base_url}/api/health"
        self._session_id: str | None = None
        self.last_trace: list[dict[str, Any]] = []

    def healthcheck(self) -> dict[str, Any]:
        response = self._session.get(self._health_url, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    def reset(self) -> None:
        if self._session_id:
            self._session.post(
                f"{self._base_url}/api/session/reset",
                json={"session_id": self._session_id},
                timeout=self._timeout,
            )
        self._session_id = None
        self.last_trace = []

    def ask(self, question: str) -> str:
        payload: dict[str, Any] = {"question": question}
        if self._session_id:
            payload["session_id"] = self._session_id
        response = self._session.post(self._chat_url, json=payload, timeout=self._timeout)
        try:
            response.raise_for_status()
        except HTTPError as exc:
            body = response.text.strip()
            detail = f"HTTP {response.status_code} from {self._chat_url}"
            if body:
                detail = f"{detail}: {body[:500]}"
            raise RuntimeError(detail) from exc
        body = response.json()
        self._session_id = body.get("session_id") or self._session_id
        tool_calls = body.get("tool_calls") or []
        self.last_trace = [
            {"tool": tool_call.get("name", ""), "args": tool_call.get("args", {})}
            for tool_call in tool_calls
        ]
        return str(body.get("answer") or "")


@dataclass(slots=True)
class EvalQuestion:
    """One prompt-level evaluation case."""

    id: str
    prompt: str
    tool: str | None = None
    expected_tools: list[str] = field(default_factory=list)
    answer: str | None = None
    answer_contains: list[str] = field(default_factory=list)
    answer_regex: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    notes: str | None = None


def _text_or_none(parent: ET.Element, tag: str) -> str | None:
    child = parent.find(tag)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _texts(parent: ET.Element, tag: str) -> list[str]:
    values: list[str] = []
    for child in parent.findall(tag):
        if child.text and child.text.strip():
            values.append(child.text.strip())
    return values


def load_eval_suite(path: str | Path) -> tuple[dict[str, str], list[EvalQuestion]]:
    """Load an XML eval suite into structured question objects."""
    suite_path = Path(path)
    root = ET.fromstring(suite_path.read_text(encoding="utf-8"))
    if root.tag != "eval_suite":
        raise ValueError("Root element must be <eval_suite>.")

    metadata = {key: value for key, value in root.attrib.items()}
    questions: list[EvalQuestion] = []
    for question_el in root.findall("question"):
        prompt = _text_or_none(question_el, "prompt")
        if not prompt:
            raise ValueError(f"Question {question_el.attrib.get('id', '?')} is missing <prompt>.")
        expected_tools_text = _text_or_none(question_el, "expected_tools")
        expected_tools = []
        if expected_tools_text:
            expected_tools = [item.strip() for item in expected_tools_text.split(",") if item.strip()]
        question = EvalQuestion(
            id=question_el.attrib["id"],
            prompt=prompt,
            tool=question_el.attrib.get("tool"),
            expected_tools=expected_tools,
            answer=_text_or_none(question_el, "answer"),
            answer_contains=_texts(question_el, "answer_contains"),
            answer_regex=_texts(question_el, "answer_regex"),
            metadata={k: v for k, v in question_el.attrib.items() if k not in {"id", "tool"}},
            notes=_text_or_none(question_el, "notes"),
        )
        questions.append(question)
    return metadata, questions


def answer_failures(question: EvalQuestion, answer_text: str) -> list[str]:
    """Return a list of answer-check failures for one question."""
    failures: list[str] = []
    normalized = answer_text.lower()
    if question.answer is not None and answer_text.strip() != question.answer:
        failures.append(f"expected exact answer {question.answer!r}")
    for fragment in question.answer_contains:
        if fragment.lower() not in normalized:
            failures.append(f"missing answer_contains fragment {fragment!r}")
    for pattern in question.answer_regex:
        if re.search(pattern, answer_text, flags=re.IGNORECASE) is None:
            failures.append(f"answer did not match regex {pattern!r}")
    return failures


def tools_match(expected_tools: list[str], trace_tools: list[str]) -> bool:
    """Check whether expected tools appear in order as a subsequence."""
    if not expected_tools:
        return True
    index = 0
    for tool_name in trace_tools:
        if tool_name == expected_tools[index]:
            index += 1
            if index == len(expected_tools):
                return True
    return False


def evaluate_question(agent: EvalAgent, question: EvalQuestion) -> dict[str, Any]:
    """Run one question through the live agent and score the result."""
    reset = getattr(agent, "reset", None)
    if callable(reset):
        reset()
    try:
        answer_text = agent.ask(question.prompt)
    except Exception as exc:  # noqa: BLE001
        return {
            "id": question.id,
            "prompt": question.prompt,
            "answer": "",
            "trace_tools": [entry.get("tool", "") for entry in getattr(agent, "last_trace", [])],
            "passed": False,
            "failures": [f"agent error: {exc}"],
        }

    trace_tools = [entry.get("tool", "") for entry in agent.last_trace]
    failures = answer_failures(question, answer_text)
    if not tools_match(question.expected_tools, trace_tools):
        failures.append(
            "tool trace did not contain expected subsequence "
            f"{question.expected_tools!r}; saw {trace_tools!r}"
        )
    if question.tool and question.tool != "multi_step" and question.tool not in trace_tools:
        failures.append(f"primary tool {question.tool!r} not present in trace {trace_tools!r}")
    return {
        "id": question.id,
        "prompt": question.prompt,
        "answer": answer_text,
        "trace_tools": trace_tools,
        "passed": not failures,
        "failures": failures,
    }


def run_eval_suite(
    suite_path: str | Path,
    *,
    limit: int | None = None,
    question_ids: set[str] | None = None,
    fail_fast: bool = False,
    agent: EvalAgent | None = None,
) -> dict[str, Any]:
    """Run a live eval suite and return structured results."""
    metadata, questions = load_eval_suite(suite_path)
    if question_ids is not None:
        questions = [question for question in questions if question.id in question_ids]
    if limit is not None:
        questions = questions[:limit]

    eval_agent = agent if agent is not None else CBOAgent()
    results: list[dict[str, Any]] = []
    for question in questions:
        result = evaluate_question(eval_agent, question)
        results.append(result)
        if fail_fast and not result["passed"]:
            break

    passed = sum(1 for result in results if result["passed"])
    return {
        "suite": metadata,
        "results": results,
        "question_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
    }