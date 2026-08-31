# Coding-agent task variants

This repository contains two independently pinned SWE-style chess issues:

- `chess-terminal-move`: the original, smaller checkmate regression. Its source
  is the `chess_app` submodule at `2e82fff`.
- `chess-engine-search`: a harder search-state and request-atomicity regression.
  Its source is the `chess_app_search` submodule at `de578ad`.

The normal assignment runner defaults to `chess-terminal-move`. To try the
harder version, pass `TASK=tasks/chess-engine-search` to the Make targets or use
`--task tasks/chess-engine-search` with the CLI.
