"""Validate the repository SKILL.md contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import REPO_ROOT, SKILL_CONTRACT, load_allowlist, load_json, relative_posix

SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def _extract_local_targets(skill_path: Path) -> list[str]:
    text = skill_path.read_text(encoding="utf-8")
    targets = []
    for raw_target in LINK_PATTERN.findall(text):
        target = raw_target.strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        targets.append(target)
    return targets


def validate_skill_spec(repo_root: Path = REPO_ROOT) -> None:
    contract = load_json(SKILL_CONTRACT)
    allowlist = load_allowlist()
    skill_path = repo_root / "SKILL.md"
    if not skill_path.exists():
        raise ValueError("SKILL.md is required at the repository root.")

    text = skill_path.read_text(encoding="utf-8")
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    if not non_empty_lines:
        raise ValueError("SKILL.md must not be empty.")
    if non_empty_lines[0] != contract["title"]:
        raise ValueError(f"SKILL.md title must be exactly {contract['title']!r}.")
    if len(non_empty_lines) > contract["max_non_empty_lines"]:
        raise ValueError(
            f"SKILL.md exceeds the non-empty line limit of {contract['max_non_empty_lines']}."
        )

    sections = [match.group(1) for match in SECTION_PATTERN.finditer(text)]
    missing_sections = [
        section for section in contract["required_sections"] if section not in sections
    ]
    if missing_sections:
        raise ValueError(f"SKILL.md is missing required sections: {', '.join(missing_sections)}")

    lowered = text.lower()
    for token in contract["banned_tokens"]:
        if token.lower() in lowered:
            raise ValueError(f"SKILL.md contains banned token: {token}")

    for target in _extract_local_targets(skill_path):
        path_part = target.split("#", 1)[0]
        if path_part.startswith("/") or "../" in path_part:
            raise ValueError(f"SKILL.md contains a disallowed local link: {target}")
        resolved = (skill_path.parent / path_part).resolve(strict=True)
        rel_path = relative_posix(resolved, repo_root)
        if not Path(resolved).exists():
            raise ValueError(f"SKILL.md link target does not exist: {target}")
        if not is_allowlisted(rel_path, allowlist):
            raise ValueError(f"SKILL.md link target is outside the package allowlist: {target}")


def is_allowlisted(rel_path: str, allowlist: list[str]) -> bool:
    from scripts.ci.common import is_allowlisted as _is_allowlisted

    return _is_allowlisted(rel_path, allowlist)


def main() -> int:
    validate_skill_spec()
    print("SKILL.md contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
