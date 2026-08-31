"""Tests for the agent loop.

These use a scripted stand-in for the language model and a fake environment, so
they run offline and launch no Modal sandbox.

The assertions look for content anywhere in the prompt rather than at fixed
positions, so that any reasonable message layout passes.
"""

import json
from pathlib import Path
import re
import string

import pytest

from openai.types.chat import ChatCompletion

from assignment.agent import CodeAgent, StepLimitError

TASK = "print hello, world to the terminal"

# A plausible run for TASK: look around, write the script, run it, produce the
# patch, then check it. Shared by the tests so they exercise the same trajectory.
ACTIONS = [
    ("call_1", "ls -la"),
    ("call_2", "cat <<'EOF' > hello.py\nprint('hello, world')\nEOF"),
    ("call_3", "python hello.py"),
    ("call_4", "git diff -- hello.py > patch.txt"),
    ("call_5", "cat patch.txt"),
]

# A 26,000 character file: 1000 a's, then 1000 b's, and so on through z. Long
# enough that it must be truncated before it reaches the model.
LONG_FILE_COMMAND = "cat f.txt"
LONG_FILE = "".join(letter * 1000 for letter in string.ascii_lowercase)

# The head and tail of that file, with anything at all between them. A truncated
# observation keeps both ends, so this matches whether or not the middle is
# elided, and the length of the match is what tells the two apart.
HEAD_TO_TAIL = re.compile(r"a{100,}.*?z{100,}", re.DOTALL)

# What the fake environment reports for each of those commands.
OUTPUTS = {
    LONG_FILE_COMMAND: LONG_FILE,
    "ls -la": "total 4\ndrwxr-xr-x 2 root root 4096 Jan  1 00:00 .\n",
    "cat <<'EOF' > hello.py\nprint('hello, world')\nEOF": "",
    "python hello.py": "hello, world\n",
    "git diff -- hello.py > patch.txt": "",
    "cat patch.txt": "diff --git a/hello.py b/hello.py\n+print('hello, world')\n",
}


class FakeEnvironment:
    """Stands in for `Environment`, recording commands instead of running them."""

    cwd = "/testbed"
    system, release, version, machine = "Linux", "6.1.0-21-cloud-amd64", "#1 SMP", "x86_64"

    def __init__(self):
        self.commands = []

    def execute(self, command, **kwargs):
        self.commands.append(command)
        return {"output": OUTPUTS.get(command, ""), "returncode": 0}


def make_action(call_id: str, command: str, name: str = "execute") -> dict:
    """An assistant message calling `execute` with `command`."""
    return make_raw_action(call_id, name, json.dumps({"command": command}))


def make_text(content: str) -> dict:
    """An assistant message with no tool call, so nothing is executed."""
    return {"role": "assistant", "content": content}


def make_raw_action(call_id: str, name: str, arguments: str) -> dict:
    """An assistant message making one tool call, with arguments passed through."""
    return {
        "role": "assistant",
        "content": f"Calling {name}.",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ],
    }


def as_text(messages) -> str:
    """Flatten messages to one string, so tests can search them for content.

    Strings that are themselves JSON, such as a tool message's content or a tool
    call's arguments, are unwrapped too, so a search matches the real text rather
    than its escaped form.
    """
    parts = []

    def walk(node):
        if isinstance(node, str):
            parts.append(node)
            try:
                nested = json.loads(node)
            except json.JSONDecodeError:
                return
            if isinstance(nested, (dict, list)):
                walk(nested)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(messages)
    return "\n".join(parts)


def make_completion(message: dict) -> ChatCompletion:
    """Wrap an assistant message in a chat completion, as the API would return it."""
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4.1",
            "choices": [{"index": 0, "finish_reason": "tool_calls", "message": message}],
        }
    )


@pytest.fixture
def make_agent(monkeypatch, tmp_path):
    """Build a CodeAgent whose API client returns a scripted list of responses.

    The fake stands in for `client.chat.completions.create`, the boundary the
    agent actually talks to, so a test sees every request the agent issues no
    matter how the loop above it is written. The credentials are stubbed because
    `Agent.__init__` refuses to construct without them; no request is ever made.

    Returns the agent and the list of calls made to the API, each entry being
    the keyword arguments of one request.

    The agent takes one step per scripted response, so a run that steps further
    than the script fails with an IndexError rather than silently repeating.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:0/v1")

    def _make(responses: list[dict]):
        agent = CodeAgent(
            TASK,
            FakeEnvironment(),
            model="gpt-4.1",
            logs_save_path=str(tmp_path / "logs.json"),
        )
        agent.step_limit = len(responses)

        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return make_completion(responses[len(calls) - 1])

        agent.client.chat.completions.create = create
        return agent, calls

    return _make


def test_prompt_carries_task_action_and_result(make_agent):
    """The second step's prompt holds the task, the action, and the tool result."""
    agent, calls = make_agent([make_action(call_id, command) for call_id, command in ACTIONS[:2]])

    with pytest.raises(StepLimitError):
        agent.run()

    first_id, first_command = ACTIONS[0]
    second_step = as_text(calls[1]["messages"])
    assert TASK in second_step, "the task statement should still be in the prompt"
    assert first_command in second_step, "the action the agent took should be in the prompt"
    assert OUTPUTS[first_command] in second_step, "the tool result should be in the prompt"
    assert first_id in second_step, "the result should be tied to the call it answers"


def test_long_observation_is_truncated(make_agent):
    """A 26,000 character file reaches the next prompt in truncated form."""
    agent, calls = make_agent(
        [make_action("call_cat", LONG_FILE_COMMAND), make_action("call_ls", "ls -la")]
    )

    with pytest.raises(StepLimitError):
        agent.run()

    assert LONG_FILE_COMMAND in agent.env.commands, "the file should have been read"

    second_step = as_text(calls[1]["messages"])
    match = HEAD_TO_TAIL.search(second_step)
    assert match, (
        "expected the start and the end of the file to survive in the prompt, "
        "so the model can still see what it read"
    )
    assert len(match.group()) < 10000, (
        f"the observation reached the model at {len(match.group()):,} characters; "
        f"observations over 10,000 characters should be truncated"
    )


def test_context_compaction_summarizes_old_steps_and_keeps_recent_tool_pair(make_agent):
    """Compaction replaces old raw context but preserves a valid recent step."""

    actions = [
        make_action("call_old", LONG_FILE_COMMAND),
        make_action("call_recent", "ls -la"),
        make_action("call_next", "python hello.py"),
    ]
    agent, calls = make_agent(actions)
    agent.compact_threshold_tokens = 1
    agent.compaction_keep_recent_steps = 1

    action_index = 0
    summary = (
        "Inspected a large generated file. No source changes or tests have been "
        "completed. Continue investigating the repository."
    )

    def create(**kwargs):
        nonlocal action_index
        calls.append(kwargs)
        if "tools" not in kwargs:
            return make_completion(make_text(summary))
        response = make_completion(actions[action_index])
        action_index += 1
        return response

    agent.client.chat.completions.create = create

    with pytest.raises(StepLimitError):
        agent.run()

    compaction_calls = [call for call in calls if "tools" not in call]
    action_calls = [call for call in calls if "tools" in call]
    assert len(compaction_calls) == 1
    assert len(action_calls) == 3

    compaction_source = as_text(compaction_calls[0]["messages"])
    assert TASK in compaction_source
    assert LONG_FILE_COMMAND in compaction_source
    assert OUTPUTS[LONG_FILE_COMMAND][:100] in compaction_source

    next_action_prompt = as_text(action_calls[2]["messages"])
    assert TASK in next_action_prompt
    assert summary in next_action_prompt
    assert "call_recent" in next_action_prompt
    assert "ls -la" in next_action_prompt
    assert OUTPUTS["ls -la"] in next_action_prompt
    assert LONG_FILE_COMMAND not in next_action_prompt
    assert OUTPUTS[LONG_FILE_COMMAND][:100] not in next_action_prompt

    assert len(agent.compaction_events) == 1
    event = agent.compaction_events[0]
    assert event["estimated_tokens_after"] < event["estimated_tokens_before"]

    trajectory = json.loads(Path(agent.logs_save_path).read_text())
    assert len(trajectory["compactions"]) == 1


def test_skill_catalog_lists_names_without_skill_bodies(monkeypatch, tmp_path):
    """The prompt advertises each skill by name but not its full body.

    A CodeAgent loaded with the code-skills catalog should name `submit-task`
    in its prompt so the model knows the skill exists, while the skill's body —
    which tells the agent to write `patch.txt` — stays out of the prompt until
    the agent actually invokes the skill.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:0/v1")

    agent = CodeAgent(
        TASK,
        FakeEnvironment(),
        model="gpt-4.1",
        logs_save_path=str(tmp_path / "logs.json"),
        skills_path="./tasks/code-skills/",
    )

    prompt = as_text(agent.build_prompt())
    assert "submit-task" in prompt, "the skill catalog should name the available skill"
    assert "patch.txt" not in prompt, (
        "the skill's body should not be in the prompt before the skill is invoked"
    )


def test_step_limit_raises(make_agent):
    """A run that never finishes stops after exactly step_limit model calls."""
    agent, calls = make_agent([make_action(call_id, command) for call_id, command in ACTIONS])
    step_limit = agent.step_limit

    with pytest.raises(StepLimitError):
        agent.run()

    assert len(calls) == step_limit, (
        f"expected {step_limit} calls to the model, the agent made {len(calls)}"
    )


def test_malformed_arguments_are_not_executed(make_agent):
    """A tool call whose arguments are not valid JSON runs nothing and does not crash.

    Reaching the step limit, rather than a JSONDecodeError, is what shows the
    agent handled the bad arguments instead of propagating them.
    """
    agent, _ = make_agent([make_raw_action("call_bad", "execute", "{not json")])

    with pytest.raises(StepLimitError):
        agent.run()

    assert agent.env.commands == [], "nothing should have been executed"


def test_unknown_tool_is_not_executed(make_agent):
    """A call to a tool the agent does not have runs nothing and does not crash."""
    agent, _ = make_agent([make_action("call_unknown", "ls -la", name="not_a_tool")])

    with pytest.raises(StepLimitError):
        agent.run()

    assert agent.env.commands == [], "nothing should have been executed"
