"""The SWE-bench instances this repository evaluates against.

Both are vendored under `tasks/swebench/`: the issue text, the test patch, the
graded test ids, and the published image name. Nothing is fetched at run time,
so evaluation works offline and cannot drift when the upstream dataset or its
serving API changes.

Adding an instance means adding a directory here, not reaching for a dataset.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

TASKS = Path(__file__).resolve().parents[3] / "tasks" / "swebench"

@dataclass(frozen=True)
class Instance:
    """One benchmark instance, read from its `instance.json`.

    Attributes:
        instance_id: The benchmark's id, for example `django__django-15368`.
        repo: Upstream repository the issue belongs to.
        version: Repository version, which fixes how its tests are run.
        base_commit: The commit the published image is built at.
        image: The published evaluation image, already holding the repository
            with its dependencies installed.
        framework: Which runner the repository uses, `django` or `pytest`. It
            selects both the test command and the output parser.
        test_cmd: The command to run, with `{python}` where the interpreter goes.
        test_patch: The diff adding the graded tests.
        problem_statement: The issue text shown to the agent.
        fail_to_pass: Tests that must go from failing to passing.
        pass_to_pass: Tests that must keep passing.
        cwd: Working directory the tests run in.
    """

    instance_id: str
    repo: str
    version: str
    base_commit: str
    image: str
    framework: str
    test_cmd: str
    test_patch: str
    problem_statement: str
    fail_to_pass: tuple[str, ...]
    pass_to_pass: tuple[str, ...]
    cwd: str = "/testbed"

    @property
    def task_id(self) -> str:
        """The id under the name `evaluate` uses, shared with `EvaluationSpec`."""
        return self.instance_id

    @classmethod
    def load(cls, path: str | Path) -> Instance:
        """Read an instance from its directory, or from its `instance.json`."""
        path = Path(path).resolve()
        spec_path = path if path.is_file() else path / "instance.json"
        if not spec_path.is_file():
            raise FileNotFoundError(f"No instance.json found at {spec_path}")

        root = spec_path.parent
        spec = json.loads(spec_path.read_text())
        return cls(
            instance_id=spec["instance_id"],
            repo=spec["repo"],
            version=spec["version"],
            base_commit=spec["base_commit"],
            image=spec["image"],
            framework=spec["framework"],
            test_cmd=spec["test_cmd"],
            test_patch=(root / spec["test_patch"]).read_text(),
            problem_statement=(root / spec["problem_statement"]).read_text(),
            fail_to_pass=tuple(spec["fail_to_pass"]),
            pass_to_pass=tuple(spec["pass_to_pass"]),
            cwd=spec.get("cwd", "/testbed"),
        )

def published_images() -> dict[str, str]:
    """Task id to published image, for every instance that ships one.

    `evaluate` consults this before building: an instance listed here already
    has an image on Docker Hub, so nothing needs to be built from source.
    """
    return {name: load(name).image for name in available()}

def available() -> list[str]:
    """The instance ids this repository can evaluate, in sorted order."""
    return sorted(path.name for path in TASKS.iterdir() if (path / "instance.json").is_file())

def load(instance_id: str) -> Instance:
    """Load a vendored instance by id.

    Raises:
        KeyError: If the id is not one of the vendored instances, listing what is.
    """
    directory = TASKS / instance_id
    if not (directory / "instance.json").is_file():
        raise KeyError(f"{instance_id!r} is not vendored. Available: {', '.join(available())}")
    return Instance.load(directory)
