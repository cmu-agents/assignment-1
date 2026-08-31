"""Run one model-written snippet inside the testbed, beside the chess server.

Shipped into the sandbox next to ``chess_tools.py``. The snippet never reaches
the agent process, and its ``simulate_move``/``play_move`` calls go to the
server over localhost instead of back through the tunnel.
"""

from __future__ import annotations

import base64
import io
import json
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout

import httpx

sys.path.insert(0, "/opt/assignment")

from chess_tools import _play_move, _simulate_move  # noqa: E402

def build_tools(client: httpx.Client) -> dict:
    """Expose the registered tools under the names the model was taught."""

    def unwrap(result):
        # The tool layer reports a failed call as an observation. A snippet
        # wants an exception at the line that caused it.
        if isinstance(result, str):
            if result.startswith("<chess_error>"):
                raise RuntimeError(result)
            return json.loads(result)
        return result

    def simulate_move(fen: str, move: str | None = None) -> dict:
        return unwrap(_simulate_move(client, json.dumps({"fen": fen, "move": move})))

    def play_move(move: str) -> dict:
        return unwrap(_play_move(client, json.dumps({"move": move})))

    return {"simulate_move": simulate_move, "play_move": play_move}

def main() -> None:
    port, encoded = sys.argv[1], sys.argv[2]
    code = base64.b64decode(encoded).decode()
    client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30)

    namespace = {"__name__": "__agent__", **build_tools(client)}
    stdout, stderr = io.StringIO(), io.StringIO()
    error = None
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            exec(compile(code, "<agent-python>", "exec"), namespace, namespace)
        except BaseException as exc:
            error = f"{type(exc).__name__}: {exc}"
            traceback.print_exc(limit=4)

    # The result is the only thing on the real stdout, so the caller can parse
    # it whatever the snippet printed.
    json.dump(
        {"stdout": stdout.getvalue(), "stderr": stderr.getvalue(), "error": error},
        sys.__stdout__,
    )

if __name__ == "__main__":
    main()
