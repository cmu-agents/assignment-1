# 11-768 Assignment 1: Build an Agent Harness

Student setup, requirements, grading, and submission instructions are in
[`ASSIGNMENT.md`](ASSIGNMENT.md).

The target chess application is pinned as a submodule. Do not develop inside
`chess_app/`; the assignment runner copies that exact commit into a Modal
sandbox and gives the coding agent an isolated working tree.

## Setup

Install [uv](https://docs.astral.sh/uv/) if needed, then install this project
and initialize and verify both pinned chess submodules:

```bash
make setup
```

Create a Modal account and authenticate once on your machine:

```bash
uv run modal setup
```

Copy the provided environment template and add the course key:

```bash
cp .env.example .env
```

The assignment uses the course SAIL endpoint. Add the SAIL base URL and key
distributed to you; the template supplies the default model:

```dotenv
OPENAI_BASE_URL=<course SAIL OpenAI-compatible base URL>
OPENAI_API_KEY=...
OPENAI_MODEL=deepseek/deepseek-v4-flash-0731
OPENAI_MAX_RETRIES=5
```

Validate the sources, Modal login, and inference endpoint before starting a
billable sandbox or model generation:

```bash
make doctor
```

Never commit `.env` or an API key. `make doctor` does not print the key.

Run the fast offline tests while developing:

```bash
make test
```

The starter intentionally fails tests for the student TODOs. See the milestone
table in `ASSIGNMENT.md` for the behavior covered after each part.
Modal tests are separate because they are slower and use credits:

```bash
make test-modal
```
