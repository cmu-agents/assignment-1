"""Tests for the Modal sandbox environment.

These spin up real Modal sandboxes, so they are slow and billable.
Run with `pytest -m modal`.
"""

import modal
import pytest

from assignment.env import Environment

pytestmark = pytest.mark.modal


def running_sandboxes(app: modal.App) -> list[modal.Sandbox]:
    """Sandboxes still alive on `app`. poll() returns None while a sandbox runs."""
    return [sb for sb in modal.Sandbox.list(app_id=app.app_id) if sb.poll() is None]


@pytest.fixture(scope="module")
def env():
    """One sandbox shared by every test in this module.

    The assertions here are part of the test surface: they check that the
    sandbox is launched and torn down cleanly, and are reported as errors at
    setup/teardown of whichever test is running.
    """
    # SWE-ReX hardcodes the Modal app name, so we can look up the app it will use
    # and confirm nothing is already running on it.
    app = modal.App.lookup("swe-rex", create_if_missing=True)
    assert not running_sandboxes(app), (
        "Active sandbox found on the `swe-rex` modal.App. If there are sandboxes "
        "running from other projects, this test will fail."
    )

    env = Environment()
    assert len(running_sandboxes(app)) == 1, (
        "Launched one sandbox for swe-rex but more than one running sandbox found. "
        "Something has gone wrong."
    )

    yield env

    env.stop()
    assert not running_sandboxes(app), (
        "Sandbox launched by test was terminated but a running sandbox was still "
        "found. Something has gone wrong."
    )


def test_shell_command(env):
    """A bare command string runs through the shell, via the shell=True default."""
    output = env.execute("echo 'hello, world'")
    assert output["returncode"] == 0, "`echo 'hello, world'` did not return expected exit code"
    assert output["output"] == "hello, world\n", (
        f"`echo 'hello, world'` did not produce expected output when run on sandbox, "
        f"instead produced {output['output']}"
    )


def test_argv_command(env):
    """An argv list runs unshelled when shell=False is passed explicitly."""
    output = env.execute(["echo", "hello, world"], shell=False)
    assert output["returncode"] == 0, "`echo hello, world` did not return expected exit code"
    assert output["output"] == "hello, world\n", (
        f"`echo hello, world` did not produce expected output when run on sandbox, "
        f"instead produced {output['output']}"
    )


def test_failing_command(env):
    """A failing command reports its exit code, with the traceback in the output."""
    output = env.execute("python -c 'print(\"hello, world\"); raise Exception(\"test exception\")'")
    assert output["returncode"] != 0, "A raising command did not return a nonzero exit code"
    assert "hello, world\n" in output["output"], (
        f"A raising command did not produce expected output when run on sandbox, "
        f"instead produced {output['output']}"
    )
    # Streams are merged, so the traceback lands in output alongside stdout.
    assert "test exception" in output["output"], "the traceback should be in the output"
