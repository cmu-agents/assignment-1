"""Grade a patch against a SWE-bench instance, in its published image.

    # check a patch the agent produced
    uv run python scripts/evaluate_swebench.py django__django-15368 \
        --patch artifacts/django__django-15368.patch

    # baseline: with no patch the FAIL_TO_PASS tests should still fail
    uv run python scripts/evaluate_swebench.py django__django-15368

Nothing is built or fetched. The instance's image is published, and its tests
and issue text are vendored under `tasks/swebench/`.
"""

import argparse
import logging
import sys
from pathlib import Path

from assignment.eval.harness import evaluate
from assignment.eval.instances import available, load as load_instance


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("instance_id", choices=available(), help="A vendored SWE-bench instance")
    parser.add_argument("--patch", type=Path, help="Unified diff to apply before testing")
    parser.add_argument(
        "--timeout", type=float, default=1800, help="Seconds allowed for the test command"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Log each evaluation step")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s"
    )

    instance = load_instance(args.instance_id)
    patch = args.patch.read_text() if args.patch else None

    print(patch)

    report = evaluate(instance, patch=patch, timeout=args.timeout)
    print(report.summary())
    return 0 if report.resolved else 1


if __name__ == "__main__":
    sys.exit(main())
