"""Run the XML prompt eval suite against the live CBO agent."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eval_runner import WebEvalAgent, load_eval_suite, run_eval_suite


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        default=str(PROJECT_ROOT / "evals" / "cbo_qa.xml"),
        help="Path to the XML eval suite.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N questions.")
    parser.add_argument(
        "--question-id",
        action="append",
        default=None,
        help="Run only the specified question id. May be repeated.",
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop after the first failure.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON results.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("CBO_EVAL_BASE_URL"),
        help=(
            "Base URL of the deployed web app, for example https://your-service.run.app. "
            "If set, evals run through /api/chat on the live site instead of the local Gemini client."
        ),
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate and summarize the XML suite without running live Gemini evals.",
    )
    return parser.parse_args()


def _selected_questions(args: argparse.Namespace, question_count: int) -> int:
    if args.question_id:
        return len(set(args.question_id))
    if args.limit is not None:
        return min(args.limit, question_count)
    return question_count


def _filter_questions(args: argparse.Namespace, questions: list[object]) -> list[object]:
    selected = questions
    if args.question_id:
        wanted = set(args.question_id)
        selected = [question for question in selected if getattr(question, "id", None) in wanted]
    if args.limit is not None:
        selected = selected[: args.limit]
    return selected


def _print_or_dump(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return

    status = payload.get("status", "ok")
    print(f"Status: {status}")
    if "message" in payload:
        print(payload["message"])
    suite = payload.get("suite")
    if isinstance(suite, dict):
        suite_name = suite.get("name", "eval_suite")
        version = suite.get("version", "?")
        print(f"Suite: {suite_name} (v{version})")
    if "question_count" in payload:
        print(f"Questions selected: {payload['question_count']}")
    if "question_ids" in payload:
        print(f"Question ids: {', '.join(payload['question_ids'])}")


def main() -> int:
    args = parse_args()
    metadata, questions = load_eval_suite(args.suite)
    selected = _filter_questions(args, questions)
    selected_questions = len(selected)

    if args.validate_only:
        payload = {
            "status": "validated",
            "message": "Eval suite parsed successfully.",
            "suite": metadata,
            "question_count": selected_questions,
            "question_ids": [question.id for question in selected],
        }
        _print_or_dump(payload, as_json=args.json)
        return 0

    if args.base_url:
        agent = WebEvalAgent(args.base_url)
        try:
            health = agent.healthcheck()
        except Exception as exc:  # noqa: BLE001
            payload = {
                "status": "blocked",
                "message": f"Failed to reach live site at {args.base_url}: {exc}",
                "suite": metadata,
                "question_count": selected_questions,
            }
            _print_or_dump(payload, as_json=args.json)
            return 2

        if not health.get("api_key_configured", False):
            payload = {
                "status": "blocked",
                "message": (
                    f"Live site at {args.base_url} is reachable, but /api/health reports "
                    "api_key_configured=false. Configure GEMINI_API_KEY on the deployed service first."
                ),
                "suite": metadata,
                "question_count": selected_questions,
            }
            _print_or_dump(payload, as_json=args.json)
            return 2

        results = run_eval_suite(
            args.suite,
            limit=args.limit,
            question_ids=set(args.question_id) if args.question_id else None,
            fail_fast=args.fail_fast,
            agent=agent,
        )
    elif not os.environ.get("GEMINI_API_KEY"):
        payload = {
            "status": "blocked",
            "message": (
                "GEMINI_API_KEY is not set. Set it in the environment or a .env file "
                "before running live evals. To validate the XML suite without a key, "
                "rerun with --validate-only. To run through the deployed app instead, "
                "pass --base-url https://<your-cloud-run-url>."
            ),
            "suite": metadata,
            "question_count": selected_questions,
        }
        _print_or_dump(payload, as_json=args.json)
        return 2
    else:
        results = run_eval_suite(
            args.suite,
            limit=args.limit,
            question_ids=set(args.question_id) if args.question_id else None,
            fail_fast=args.fail_fast,
        )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        suite_name = results["suite"].get("name", "eval_suite")
        print(f"Suite: {suite_name}")
        print(f"Passed: {results['passed']}/{results['question_count']}")
        for result in results["results"]:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"[{status}] Q{result['id']}: {result['prompt']}")
            if not result["passed"]:
                for failure in result["failures"]:
                    print(f"  - {failure}")
                print(f"  - trace: {', '.join(result['trace_tools']) or '(no tools)'}")
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())