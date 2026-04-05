"""Validate the repository SKILL.md contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import (
    PACKAGE_ALLOWLIST,
    REPO_ROOT,
    SKILL_CONTRACT,
    load_allowlist,
    load_json,
    relative_posix,
)

SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
REQUIRED_PREFLIGHT_FRAGMENTS = [
    "Preflight gate:",
    "Do not run any `python -m m2c_pipeline` command until preflight is complete.",
    "references/install-python.md",
    "permission plus network/admin confirmation",
]


def _extract_local_targets(skill_path: Path) -> list[str]:
    text = skill_path.read_text(encoding="utf-8")
    targets = []
    for raw_target in LINK_PATTERN.findall(text):
        target = raw_target.strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        targets.append(target)
    return targets


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise ValueError("SKILL.md must start with YAML frontmatter delimited by --- lines.")

    frontmatter: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"Invalid frontmatter line: {raw_line!r}")
        frontmatter[key.strip()] = _normalize_frontmatter_value(value.strip())

    return frontmatter, text[match.end() :]


def _normalize_frontmatter_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def validate_skill_spec(
    repo_root: Path = REPO_ROOT,
    contract_path: Path = SKILL_CONTRACT,
    allowlist_path: Path = PACKAGE_ALLOWLIST,
) -> None:
    contract = load_json(contract_path)
    allowlist = load_allowlist(allowlist_path)
    skill_path = repo_root / "SKILL.md"
    if not skill_path.exists():
        raise ValueError("SKILL.md is required at the repository root.")

    text = skill_path.read_text(encoding="utf-8")
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    if not non_empty_lines:
        raise ValueError("SKILL.md must not be empty.")
    if len(non_empty_lines) > contract["max_non_empty_lines"]:
        raise ValueError(
            f"SKILL.md exceeds the non-empty line limit of {contract['max_non_empty_lines']}."
        )

    frontmatter, body = _parse_frontmatter(text)
    _validate_frontmatter(frontmatter, contract)

    body_non_empty_lines = [line for line in body.splitlines() if line.strip()]
    if not body_non_empty_lines:
        raise ValueError("SKILL.md body must not be empty.")
    if body_non_empty_lines[0] != contract["required_title"]:
        raise ValueError(f"SKILL.md title must be exactly {contract['required_title']!r}.")

    sections = [match.group(1) for match in SECTION_PATTERN.finditer(body)]
    missing_sections = [
        section for section in contract["required_sections"] if section not in sections
    ]
    if missing_sections:
        raise ValueError(f"SKILL.md is missing required sections: {', '.join(missing_sections)}")

    lowered = text.lower()
    for token in contract["banned_tokens"]:
        if token.lower() in lowered:
            raise ValueError(f"SKILL.md contains banned token: {token}")

    _validate_preflight_gate(text)

    for target in _extract_local_targets(skill_path):
        path_part = target.split("#", 1)[0]
        if path_part.startswith("/") or ".." in PurePosixPath(path_part).parts:
            raise ValueError(f"SKILL.md contains a disallowed local link: {target}")
        if path_part.startswith(("references/", "evals/")) and len(PurePosixPath(path_part).parts) != 2:
            raise ValueError(f"SKILL.md local links under references/ and evals/ must be one level deep: {target}")

        resolved = skill_path.parent / path_part
        if not resolved.exists():
            raise ValueError(f"SKILL.md link target does not exist: {target}")

        rel_path = relative_posix(resolved, repo_root)
        if not is_allowlisted(rel_path, allowlist):
            raise ValueError(f"SKILL.md link target is outside the package allowlist: {target}")


def _validate_frontmatter(frontmatter: dict[str, str], contract: dict) -> None:
    missing_fields = [
        field for field in contract["required_frontmatter_fields"] if not frontmatter.get(field)
    ]
    if missing_fields:
        raise ValueError(f"SKILL.md frontmatter is missing required fields: {', '.join(missing_fields)}")

    skill_name = frontmatter["name"]
    if not NAME_PATTERN.fullmatch(skill_name):
        raise ValueError("SKILL.md frontmatter name must use lowercase letters, digits, and hyphens only.")
    if skill_name != contract["expected_name"]:
        raise ValueError(f"SKILL.md frontmatter name must be exactly {contract['expected_name']!r}.")

    description = frontmatter["description"]
    lowered_description = description.lower()
    for phrase in contract["description_required_phrases"]:
        if phrase.lower() not in lowered_description:
            raise ValueError(f"SKILL.md description must include {phrase!r}.")
    for keyword in contract["description_required_keywords"]:
        if keyword.lower() not in lowered_description:
            raise ValueError(f"SKILL.md description must mention {keyword!r}.")
    for fragment in contract["description_disallowed_fragments"]:
        if fragment.lower() in lowered_description:
            raise ValueError(f"SKILL.md description contains a disallowed generic fragment: {fragment!r}.")


def _validate_preflight_gate(text: str) -> None:
    for fragment in REQUIRED_PREFLIGHT_FRAGMENTS:
        if fragment not in text:
            raise ValueError(f"SKILL.md preflight gate is missing required phrase: {fragment!r}.")

    venv_index = text.find("prefer a compatible `./venv/bin/python`")
    system_index = text.find("look for a compatible system `python3` or `python`")
    install_index = text.find("references/install-python.md")

    if min(venv_index, system_index, install_index) < 0:
        raise ValueError("SKILL.md preflight gate must include venv/system/install decision points.")
    if not venv_index < system_index < install_index:
        raise ValueError("SKILL.md preflight gate order must be venv -> system python -> install reference.")


def is_allowlisted(rel_path: str, allowlist: list[str]) -> bool:
    from scripts.ci.common import is_allowlisted as _is_allowlisted

    return _is_allowlisted(rel_path, allowlist)


def main() -> int:
    validate_skill_spec()
    print("SKILL.md contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
