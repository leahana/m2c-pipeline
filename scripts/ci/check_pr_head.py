"""Validate PR title and head branch naming policy."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

TITLE_PATTERN = re.compile(
    r"^(feat|fix|docs|refactor|test|chore|ci|build|perf|revert)(\([a-z0-9._/-]+\))?: .+"
)
HEAD_PATTERN = re.compile(
    r"^(dev|"
    r"(feat|fix|docs|refactor|test|chore|ci|build|perf|revert|release)/[a-z0-9._/-]+|"
    r"release-please--branches--[a-z0-9._/-]+(?:--components--[a-z0-9._/-]+)?"
    r")$"
)


def validate_pr_naming(title: str, head_ref: str) -> None:
    if not TITLE_PATTERN.fullmatch(title):
        raise ValueError(
            "PR title does not match policy: "
            "^(feat|fix|docs|refactor|test|chore|ci|build|perf|revert)(\\([a-z0-9._/-]+\\))?: .+"
        )
    if not HEAD_PATTERN.fullmatch(head_ref):
        raise ValueError(
            "PR head branch does not match policy: "
            "^(dev|(feat|fix|docs|refactor|test|chore|ci|build|perf|revert|release)/[a-z0-9._/-]+)$"
        )


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name != "pull_request":
        print("policy-pr-head: skipped outside pull_request events.")
        return 0

    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH is required for pull_request validation.")

    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request", {})
    title = (pull_request.get("title") or "").strip()
    head_ref = ((pull_request.get("head") or {}).get("ref") or "").strip()

    try:
        validate_pr_naming(title, head_ref)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"PR naming policy passed for title={title!r} head={head_ref!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
