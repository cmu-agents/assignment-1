# Engine crashes after a game-ending human move

The chess API returns an internal server error when White makes a legal move
that immediately ends the game. For example, submitting `f7g7` from the
position below checkmates Black, but `POST /api/move` responds with HTTP 500:

```text
7k/5Q2/6K1/8/8/8/8/8 w - - 0 1
```

A game-ending move should return the final game state normally. The response
should report that the game is over, identify the result, and contain no engine
reply. Normal non-terminal moves must continue to receive a deterministic
engine response.

To reproduce the problem, run:

```python
from fastapi.testclient import TestClient

from chess_app.game import ChessGame
from chess_app.server import create_app

game = ChessGame()
game._board.set_fen("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")

with TestClient(create_app(game), raise_server_exceptions=False) as client:
    print(client.post("/api/move", json={"move": "f7g7"}))
```

This prints `<Response [500]>`. It should return 200 with the final state.
