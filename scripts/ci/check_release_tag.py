"""Validate that the release tag matches the repository version contract."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import GOVERNANCE_CONTRACT, load_json, load_version


def validate_release_tag(tag: str, release_tag_regex: str, version: str) -> None:
    if not re.fullmatch(release_tag_regex, tag):
        raise ValueError(f"Tag {tag!r} does not match {release_tag_regex!r}.")

    expected = f"v{version}"
    if tag != expected:
        raise ValueError(f"Tag {tag!r} does not match version {expected!r}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release tag/version consistency.")
    parser.add_argument(
        "--tag",
        default=os.environ.get("GITHUB_REF_NAME", ""),
        help="Tag name to validate. Defaults to GITHUB_REF_NAME.",
    )
    args = parser.parse_args()

    if not args.tag:
        raise SystemExit("A tag value is required via --tag or GITHUB_REF_NAME.")

    contract = load_json(GOVERNANCE_CONTRACT)
    validate_release_tag(
        tag=args.tag,
        release_tag_regex=contract["release_tag_regex"],
        version=load_version(),
    )
    print(f"Release tag validation passed for {args.tag}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
