"""Command-line runners students use for the two assignment parts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from assignment.agent import (
    ChessAgent,
    CodeAgent,
)
from assignment.chess_sandbox import ChessSandbox
from assignment.task import Task
from assignment.env import Environment
from assignment.utils.image import build_testbed_image
from assignment.eval.instances import available, load as load_instance

DEFAULT_TASK = Path("tasks/chess-terminal-move")


def _compact_threshold(value: str) -> int | None:
    tokens = int(value)
    if tokens < 0:
        raise argparse.ArgumentTypeError("context threshold cannot be negative")
    return tokens or None


def _add_compaction_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--compact-threshold-tokens",
        type=_compact_threshold,
        default=None,
        help=(
            "summarize old context before an action request at this estimated "
            "prompt size; use 0 to disable"
        ),
    )
    parser.add_argument(
        "--compaction-keep-recent-steps",
        type=int,
        help="steps kept verbatim when compacting; the rest are summarized",
    )
    parser.add_argument(
        "--compaction-max-tokens",
        type=int,
        help="token budget for the summary a compaction produces",
    )


def _add_code_agent_arguments(parser: argparse.ArgumentParser) -> None:
    """The arguments both code-agent runners take, so they cannot drift apart."""
    parser.add_argument("--model")
    parser.add_argument("--step-limit", type=int, default=100)
    _add_compaction_argument(parser)
    parser.add_argument(
        "--skills-path",
        type=Path,
        help=(
            "directory of skill folders, each holding a SKILL.md; the agent is "
            "told what they cover and can load one with invoke_skill"
        ),
    )
    # No defaults: a run's outputs are named deliberately, so that repeated runs
    # cannot quietly overwrite each other.
    parser.add_argument("--trajectory", type=Path, help="where to write the run log")
    parser.add_argument(
        "--patch-output", type=Path, help="where to write the patch the agent submits"
    )


def _required(value, flag: str):
    """Fail early when an argument with no default was left out."""
    if value is None:
        raise SystemExit(f"Pass {flag}.")
    return value


def _model(argument: str | None) -> str:
    model = argument or os.environ.get("OPENAI_MODEL")
    if not model:
        raise SystemExit("Set OPENAI_MODEL or pass --model.")
    return model


def run_code_agent() -> None:
    """Launch the CodeAgent on the buggy chess task and save its artifacts."""

    parser = argparse.ArgumentParser(description=run_code_agent.__doc__)
    parser.add_argument("--task", type=Path, default=DEFAULT_TASK)
    _add_code_agent_arguments(parser)
    args = parser.parse_args()

    trajectory = _required(args.trajectory, "--trajectory")
    patch_output = _required(args.patch_output, "--patch-output")
    task = Task.load(args.task)
    model = _model(args.model)

    submitted_patch = ""
    with Environment(
        image=build_testbed_image(task),
        cwd="/testbed",
    ) as environment:
        agent = CodeAgent(
            task=task.problem_statement,
            environment=environment,
            model=model,
            logs_save_path=str(trajectory),
            step_limit=args.step_limit,
            auto_stop_environment=False,
            compact_threshold_tokens=args.compact_threshold_tokens,
            compaction_keep_recent_steps=args.compaction_keep_recent_steps,
            compaction_max_tokens=args.compaction_max_tokens,
            skills_path=str(args.skills_path) if args.skills_path else None,
        )
        agent.run()
        output = environment.execute("cat patch.txt")
        if output["returncode"] != 0:
            raise SystemExit("Error reading agent-produced patch")
        submitted_patch = output["output"]

    if not submitted_patch.strip():
        raise SystemExit("Agent finished without a non-empty patch.")
    patch_output.parent.mkdir(parents=True, exist_ok=True)
    patch_output.write_text(submitted_patch)
    print(f"Patch: {patch_output}")
    print(f"Trajectory: {trajectory}")


def run_swebench_agent() -> None:
    """Launch the CodeAgent on a SWE-bench instance in its published image."""

    parser = argparse.ArgumentParser(description=run_swebench_agent.__doc__)
    parser.add_argument("instance_id")
    _add_code_agent_arguments(parser)
    args = parser.parse_args()

    trajectory = _required(args.trajectory, "--trajectory")
    patch_output = _required(args.patch_output, "--patch-output")
    model = _model(args.model)
    instance = load_instance(args.instance_id)

    print(
        f"Instance: {instance.instance_id} ({instance.repo} @ {instance.base_commit[:12]})"
    )
    print(f"Image: {instance.image}", flush=True)

    submitted_patch = ""
    # SWE-bench images install the repository into a conda env named `testbed`
    # but never activate it, so without this `python` is conda's base env and
    # the repository's own dependencies are missing.
    with Environment(
        image=instance.image, cwd="/testbed", conda_env="testbed"
    ) as environment:
        agent = CodeAgent(
            task=instance.problem_statement,
            environment=environment,
            model=model,
            logs_save_path=str(trajectory),
            step_limit=args.step_limit,
            auto_stop_environment=False,
            compact_threshold_tokens=args.compact_threshold_tokens,
            compaction_keep_recent_steps=args.compaction_keep_recent_steps,
            compaction_max_tokens=args.compaction_max_tokens,
            skills_path=str(args.skills_path) if args.skills_path else None,
        )
        agent.run()
        output = environment.execute("cat patch.txt")
        if output["returncode"] != 0:
            raise SystemExit("Error reading agent-produced patch")
        submitted_patch = output["output"]

    if not submitted_patch.strip():
        raise SystemExit("Agent finished without a non-empty patch.")
    patch_output.parent.mkdir(parents=True, exist_ok=True)
    patch_output.write_text(submitted_patch)
    print(f"Patch: {patch_output}")
    print(f"Trajectory: {trajectory}")


def run_chess_agent() -> None:
    """Apply the Part 1 patch, then let ChessAgent play through the API."""

    parser = argparse.ArgumentParser(description=run_chess_agent.__doc__)
    parser.add_argument("--task", type=Path, default=DEFAULT_TASK)
    parser.add_argument("--model")
    parser.add_argument("--step-limit", type=int, default=200)
    _add_compaction_argument(parser)
    parser.add_argument("--skills-path", type=Path)
    parser.add_argument("--programmatic-tools", action="store_true")
    parser.add_argument("--omit-legal-moves", action="store_true")
    parser.add_argument("--sandbox-timeout", type=int, default=1800)
    # No defaults, as with the code agents: the patch to play with and the log to
    # write are named per run.
    parser.add_argument("--patch", type=Path, help="the Part 1 patch to apply")
    parser.add_argument("--trajectory", type=Path, help="where to write the run log")
    parser.add_argument(
        "--result", type=Path, default=Path("artifacts/game-result.json")
    )
    args = parser.parse_args()

    patch = _required(args.patch, "--patch")
    trajectory = _required(args.trajectory, "--trajectory")
    if not patch.is_file():
        raise SystemExit(
            f"Part 1 patch not found at {patch}. Run assignment-code-agent first."
        )

    model = _model(args.model)
    with ChessSandbox(
        task=args.task,
        patch=patch,
        deployment_timeout=args.sandbox_timeout,
    ) as sandbox:
        print(f"Chess server: {sandbox.server_url}", flush=True)
        agent = ChessAgent(
            environment=sandbox,
            model=model,
            logs_save_path=str(trajectory),
            step_limit=args.step_limit,
            skills_path=str(args.skills_path) if args.skills_path else None,
            auto_stop_environment=False,
            compact_threshold_tokens=args.compact_threshold_tokens,
            compaction_keep_recent_steps=args.compaction_keep_recent_steps,
            compaction_max_tokens=args.compaction_max_tokens,
            programmatic_tools=args.programmatic_tools,
            include_legal_moves=not args.omit_legal_moves,
        )
        agent.run()

    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(agent.last_state, indent=2))
    print(f"Result: {args.result}")
    print(f"Trajectory: {trajectory}")
