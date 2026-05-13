"""Run the XML prompt eval suite against the live CBO agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eval_runner import run_eval_suite


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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