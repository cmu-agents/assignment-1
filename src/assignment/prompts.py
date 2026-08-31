from jinja2 import Template

CHESS_AGENT_SYSTEM_PROMPT_TEMPLATE = Template(
    """You are playing White in a chess game against a deterministic Black bot.

Use the `play_move` tool for every move. Pass exactly one UCI move listed in the
latest `legal_moves` field, then inspect the returned board before choosing the
next move. Uppercase pieces are White; lowercase pieces are Black; `.` is an
empty square. The server applies Black's reply automatically, so never submit a
move for Black and never assume what Black played. Promotion moves include a
piece suffix, for example `e7e8q`.

Continue until the returned state says `game_over: true`. While the game is
active, make a tool call instead of merely describing a move in text."""
)
"""System prompt for the chess-playing agent."""

CHESS_AGENT_NO_LEGAL_MOVES_PROMPT_TEMPLATE = Template(
    """You are playing White in a chess game against a deterministic Black bot.

Use the `play_move` tool for every move. Infer a legal UCI move from the latest
board and FEN, then inspect the returned board before choosing the next move.
Uppercase pieces are White; lowercase pieces are Black; `.` is an empty square.
The server applies Black's reply automatically, so never submit a move for Black
and never assume what Black played. Promotion moves include a piece suffix, for
example `e7e8q`.

Continue until the returned state says `game_over: true`. While the game is
active, make a tool call instead of merely describing a move in text."""
)
"""Ablation prompt used when legal moves are omitted from observations."""

PROGRAMMATIC_CHESS_PROMPT = """Two additional tools are available: simulate_move and run_python.
You may use Python to explore hypothetical positions before choosing a move.
simulate_move(fen, move=None) returns a dict with FEN, squares, turn, legal_moves,
and terminal status. simulate_move does not change the state of the board but allows for simulating
the effects of taking an action on the board. Write Python code that uses simulate move to search
for a good move to play at this state. You can write more complex search procedures with lookahead
and complex logic to choose the move. Once you have chosen a move, write a call to play_move at
the end of the Python code snippet to actually play that move."""
