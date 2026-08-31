"""Instructor-side patch evaluation helpers."""

from assignment.eval.harness import (
    EvaluationSpec,
    Report,
    TestStatus,
    evaluate,
    parse_pytest_report,
    resolve_image,
)
from assignment.task import Task

__all__ = [
    "EvaluationSpec",
    "Report",
    "Task",
    "TestStatus",
    "evaluate",
    "resolve_image",
    "parse_pytest_report",
]
