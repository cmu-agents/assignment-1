"""Billable integration test for the chess server hosted in a Modal sandbox."""

import modal
import pytest

from assignment.chess_sandbox import ChessSandbox, IllegalMove


pytestmark = pytest.mark.modal

def running_sandboxes(app: modal.App) -> list[modal.Sandbox]:
    return [sandbox for sandbox in modal.Sandbox.list(app_id=app.app_id) if sandbox.poll() is None]


def test_chess_app_is_playable_through_modal_tunnel():
    app = modal.App.lookup("swe-rex", create_if_missing=True)
    assert not running_sandboxes(app), "Another swe-rex sandbox is already running."

    # This public test verifies the tunnel and API infrastructure without
    # depending on the intentionally broken engine search. The private grader
    # applies a candidate patch before exercising successful moves.
    with ChessSandbox() as sandbox:
        assert len(running_sandboxes(app)) == 1

        current = sandbox.state()
        assert current["turn"] == "white"
        assert current["history"] == []

        with pytest.raises(IllegalMove):
            sandbox.play("e2e5")

        assert sandbox.reset()["history"] == []

    assert not running_sandboxes(app), "Chess sandbox was not terminated after the test."
