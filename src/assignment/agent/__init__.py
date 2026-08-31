"""Starter implementations for the shared ReAct loop and its two agents.

Part 1 completes the generic loop (``base.py``) and the coding-agent tool
executor (``code_agent.py``). Part 2 adds context compaction to that loop. Part
3 reuses it and implements one new domain tool, ``play_move``
(``chess_agent.py``).
"""

from assignment.agent.base import (
    MAX_OBSERVATION_CHARS,
    Agent,
    StepLimitError,
    format_tool_output,
    rough_message_tokens,
)
from assignment.agent.chess_agent import ChessAgent, format_chess_state
from assignment.agent.code_agent import CodeAgent

__all__ = [
    "MAX_OBSERVATION_CHARS",
    "Agent",
    "ChessAgent",
    "CodeAgent",
    "StepLimitError",
    "format_chess_state",
    "format_tool_output",
    "rough_message_tokens",
]
