"""Validate local assignment configuration without launching a Modal sandbox."""

from __future__ import annotations

import argparse
import os
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from modal.config import Config

from assignment.task import Task
from assignment.utils.image import SourceMismatch, verify_source


TASKS = ("tasks/chess-terminal-move",)
PLACEHOLDERS = ("replace-", "course-key", "<", ">")


def _configured(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    if not value or any(marker in value.lower() for marker in PLACEHOLDERS):
        return None
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="validate files and credentials without contacting the inference endpoint",
    )
    args = parser.parse_args()
    load_dotenv()

    failures: list[str] = []
    warnings: list[str] = []

    for task_path in TASKS:
        try:
            verify_source(Task.load(task_path))
            print(f"[ok] pinned source: {task_path}")
        except (FileNotFoundError, SourceMismatch, ValueError) as exc:
            failures.append(f"{task_path}: {exc}")

    modal_config = Config()
    if modal_config.get("token_id") and modal_config.get("token_secret"):
        print("[ok] Modal credentials are configured")
    else:
        failures.append("Modal credentials are missing; run `uv run modal setup`")

    api_key = _configured("OPENAI_API_KEY")
    base_url = _configured("OPENAI_BASE_URL")
    model = _configured("OPENAI_MODEL")
    if api_key:
        print("[ok] OPENAI_API_KEY is set")
    else:
        failures.append("OPENAI_API_KEY is missing or still a placeholder")
    if model:
        print(f"[ok] model: {model}")
    else:
        failures.append("OPENAI_MODEL is missing")
    if base_url:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            failures.append("OPENAI_BASE_URL must be a complete HTTPS URL")
        else:
            print(f"[ok] inference endpoint: {parsed.netloc}")
    else:
        failures.append("OPENAI_BASE_URL is missing")

    if not args.offline and api_key and base_url:
        models_url = base_url.rstrip("/") + "/models"
        try:
            response = httpx.get(
                models_url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if response.status_code in {401, 403}:
                failures.append(
                    f"inference endpoint rejected the API key ({response.status_code})"
                )
            elif response.status_code >= 500:
                failures.append(
                    f"inference endpoint is unavailable ({response.status_code})"
                )
            elif response.status_code == 200:
                print("[ok] inference endpoint accepted the API key")
            else:
                warnings.append(
                    f"endpoint is reachable but GET /models returned {response.status_code}"
                )
        except httpx.HTTPError as exc:
            failures.append(f"could not reach inference endpoint: {exc}")

    for warning in warnings:
        print(f"[warning] {warning}")
    if failures:
        for failure in failures:
            print(f"[error] {failure}")
        print("Configuration is not ready; no Modal sandbox was launched.")
        return 1
    print("Assignment configuration is ready; no Modal sandbox was launched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
