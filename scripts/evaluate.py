"""Grade a patch against a task's testbed.

    # student-facing check of the generated patch
    uv run python scripts/evaluate.py --task tasks/chess-terminal-move \
        --evaluation tasks/chess-terminal-move/public_tests \
        --patch artifacts/fix.patch

    # instructor sanity check: the reference fix must resolve the private task
    uv run python scripts/evaluate.py --task tasks/chess-terminal-move \
        --evaluation /path/to/private/chess-terminal-move \
        --patch /path/to/private/chess-terminal-move/gold_patch.diff
"""

import argparse
import logging
import sys
from pathlib import Path

from assignment.eval import EvaluationSpec, Task, evaluate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", required=True, type=Path, help="Task directory containing task.json")
    parser.add_argument(
        "--evaluation",
        required=True,
        type=Path,
        help="Directory containing evaluation.json and its test patch",
    )
    parser.add_argument("--patch", type=Path, help="Unified diff to apply before testing")
    parser.add_argument("--timeout", type=float, default=600, help="Seconds allowed for the test command")
    parser.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="Build even if the local checkout is not on the task's base commit",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Log each evaluation step")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")

    task = Task.load(args.task)
    evaluation = EvaluationSpec.load(args.evaluation)
    patch = args.patch.read_text() if args.patch else None

    report = evaluate(
        evaluation,
        patch=patch,
        task=task,
        timeout=args.timeout,
        strict=args.strict,
    )
    print(report.summary())
    return 0 if report.resolved else 1


if __name__ == "__main__":
    sys.exit(main())
