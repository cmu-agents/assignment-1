---
name: select-move
description: Strategy to pick a chess move.
---

Use available tools to select a good move.

# The two tools

Everything below is built out of exactly two calls, and the distinction between
them matters:

- `simulate_move(fen, move=None)` — the **search** tool. It returns a dict for
  the position, with `fen`, `legal_moves`, `game_over`, `winner` and `result`.
  Passing `move=None` just inspects a FEN; passing a UCI move plays that one ply
  and returns the position after it. It never touches the live board and never
  invokes the opponent, so chain its returned `fen` values to roll out a line as
  deep as you like, for either side.
- `play_move(move)` — the **commit** tool. It plays one move on the real board
  and the opponent answers. Call it exactly once, at the very end, with the move
  the search chose. Never call it to explore.

Both are available inside `run_python` as ordinary synchronous functions —
assume they are already imported when your code is executed, and write only the
relevant snippet, with no import lines and no tool-call boilerplate.

# Step 1: Opening preferences

If it is the first full move of the game, skip the search entirely. Take the
first of these that appears in `legal_moves`, and play it:

`e2e4`, `d2d4`, `c2c4`, `g1f3`

If none is legal, fall through to Step 2. Beyond this step, you should use Python
code to choose the move. Write code that executes the described strategy so you
reliably reason about board state.

# Step 2: Order the candidates

Call `simulate_move(fen)` with `move=None` on the current position and take
`legal_moves` from the result. Sort by UCI string, ascending — `a2a3` before
`b1c3`. This order is what settles ties later, so keep it.

# Step 3: Score each candidate two plies deep

For each candidate in order, call `simulate_move(fen, candidate)`. That result
is the position after your move; take its `legal_moves` as Black's replies, and
for each reply call `simulate_move(after_white["fen"], reply)` and score the
position that comes back with the evaluation in Step 4. Black is the minimizer,
so the candidate's score is the **lowest** of those replies. There is nothing to
undo — every `simulate_move` starts from the FEN you hand it, so the live board
is untouched throughout.

That is the whole search: your move, Black's answer, evaluate. Nothing deeper is
ever examined. Stop early at any position whose `game_over` is true and score it
directly from `winner` and `result` rather than simulating replies from it.

# Step 4: Evaluate a position

Terminal positions first, claiming draws where they are available:

| Outcome | Score |
| --- | --- |
| White wins | +100,000 |
| Black wins | −100,000 |
| Any draw — stalemate, repetition, 50-move | 0 |

Otherwise sum, in centipawns, from White's point of view:

- **Material** for every piece on the board — pawn 100, knight 320, bishop 330,
  rook 500, queen 900, king 0. Add for White, subtract for Black.
- **Centralization**: ±12 for each piece standing on d4, e4, d5, or e5. Add for
  White, subtract for Black. Every piece counts the same — a pawn on e4 is worth
  the same 12 as a queen there.
- **Check**: if the side to move is in check, ±25 — plus if that side is Black,
  minus if it is White.

There is nothing else. No king safety, no pawn structure, no mobility, no
development or castling term.

# Step 5: Play the best score

Take the candidate with the highest score. A later candidate must **strictly
beat** the current best to replace it, so when scores are equal the earliest
move in the Step 2 ordering wins.

Then call `play_move(best)` — once, with that move, as the last statement of the
snippet. This is the only call in the whole procedure that changes the actual game
board. **Do not** leave this out -- the computation will have no effect otherwise.
Do not just print out the move, call `play_move` at the end to actually play the move,
this will work like a standard `play_move` tool use.

That call *is* your move for this turn. The observation you get back shows the
board after it, with the opponent's answer already made. Read that new position
and start the next turn from it — do not call the `play_move` tool again for the
same move, which would play a second move from a board that has already moved on.

# Notes on the shape of this strategy

- The 25-point check term is smaller than a pawn, so it only ever breaks ties.
  It never justifies giving up material for a check.
- A 2-ply search sees Black's immediate recapture, so material is not hung for
  free, and it finds and avoids mate in one. Anything that pays off on Black's
  *second* move is outside the horizon.
- Draws score 0 rather than as a loss, so a repetition is accepted readily from
  a worse position.
