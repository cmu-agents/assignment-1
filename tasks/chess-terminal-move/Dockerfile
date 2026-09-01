# Testbed image for the `chess-terminal-move` task.
#
# The repository under test is copied to /testbed without its Git history. The
# private tests and reference patch remain outside the student environment.
#
# Dependencies are not installed here. They are pinned in task.json and applied
# by assignment.utils.image as the final layer, which has to come after Modal's
# own dependency install rather than before it. The editable install below is
# --no-deps for the same reason: pyproject.toml declares open ranges, and
# resolving them here would only be undone twice over.

FROM python:3.12-slim

# The slim image ships no git. The build needs it for the baseline commit, the
# grader needs it to apply patches, and the agent needs it to diff its work.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY . /testbed

WORKDIR /testbed

# A fresh repository gives the agent a clean baseline to `git diff` against and
# lets the grader `git apply` patches, without shipping the upstream history.
RUN git init -q -b main . \
    && git add -A \
    && git -c user.email=harness@localhost -c user.name=harness commit -q -m "base commit"

RUN pip install --no-cache-dir --no-deps -e .
