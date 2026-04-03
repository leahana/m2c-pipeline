"""Shared helpers for repository policy and packaging scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = REPO_ROOT / "policy"
PACKAGE_ALLOWLIST = POLICY_DIR / "package-allowlist.txt"
SKILL_CONTRACT = POLICY_DIR / "skill-contract.json"
GOVERNANCE_CONTRACT = POLICY_DIR / "governance.json"
VERSION_FILE = REPO_ROOT / "m2c_pipeline" / "version.py"
VERSION_PATTERN = re.compile(r'^__version__\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_allowlist(path: Path = PACKAGE_ALLOWLIST) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def load_version(path: Path = VERSION_FILE) -> str:
    match = VERSION_PATTERN.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Could not parse __version__ from {path}")
    return match.group(1)


def is_allowlisted(rel_path: str, patterns: list[str]) -> bool:
    candidate = PurePosixPath(rel_path)
    return any(candidate.match(pattern) for pattern in patterns)


def resolve_within_repo(path: Path, repo_root: Path = REPO_ROOT) -> Path:
    repo_real = repo_root.resolve(strict=True)
    real_path = path.resolve(strict=True)
    real_path.relative_to(repo_real)
    return real_path


def relative_posix(path: Path, repo_root: Path = REPO_ROOT) -> str:
    real_path = resolve_within_repo(path, repo_root)
    return real_path.relative_to(repo_root.resolve(strict=True)).as_posix()
