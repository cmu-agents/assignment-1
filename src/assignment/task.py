"""Public task definitions used to build an isolated testbed.

Shared by both halves of the assignment. Private tests and grading metadata are
deliberately not part of this object or its task directory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Task:
    """One evaluation task, loaded from a task directory.

    The directory holds a `task.json` alongside the public files it names: a
    Dockerfile that builds the testbed and the issue shown to the agent.

    The testbed is built from `source`, a local checkout of the repository —
    normally a submodule. `repo` and `base_commit` record where that checkout is
    supposed to come from, and are checked against it before every build.
    """

    id: str
    repo: str
    base_commit: str
    source: Path
    dockerfile: Path
    problem_statement: str
    pins: tuple[str, ...]
    root: Path

    @classmethod
    def load(cls, path: str | Path) -> Task:
        """Read a task from its directory, or directly from its `task.json`.

        Args:
            path: The task directory, or the `task.json` inside it.

        Returns:
            The task, with its sibling files already read into memory.
        """
        path = Path(path).resolve()
        spec_path = path if path.is_file() else path / "task.json"
        if not spec_path.is_file():
            raise FileNotFoundError(f"No task.json found at {spec_path}")
        root = spec_path.parent

        spec = json.loads(spec_path.read_text())
        missing = {
            "id",
            "repo",
            "base_commit",
            "source",
            "dockerfile",
            "problem_statement",
        } - set(spec)
        if missing:
            raise ValueError(f"{spec_path} is missing required keys: {', '.join(sorted(missing))}")

        def sibling(key: str) -> Path:
            target = root / spec[key]
            if not target.is_file():
                raise FileNotFoundError(f"{spec_path} points at {key}={spec[key]}, which does not exist")
            return target

        # The source checkout is resolved but not required to exist yet: a fresh
        # clone has an empty submodule until `git submodule update --init`, and
        # the error for that should come from the build, which can say so.
        source = (root / spec["source"]).resolve()

        # Exact versions for the testbed. Optional: a task without them takes
        # whatever its Dockerfile resolves.
        pins = tuple(spec.get("pins", ()))

        return cls(
            id=spec["id"],
            repo=spec["repo"],
            base_commit=spec["base_commit"],
            source=source,
            dockerfile=sibling("dockerfile"),
            problem_statement=sibling("problem_statement").read_text(),
            pins=pins,
            root=root,
        )
