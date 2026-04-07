"""Validate the published skill tree against the CC Switch remote contract."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import REPO_ROOT, load_allowlist, relative_posix
from scripts.ci.package_generic import build_published_skill_tree, collect_package_files

README_NAME = "README.md"
SKILL_NAME = "SKILL.md"
SKILL_README_NAME = "SKILL_README.md"
SYNTHETIC_ARCHIVE_ROOT = "cc-switch-remote-skill"
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
DISALLOWED_PUBLISHED_PREFIXES = (
    ".github/",
    "tests/",
    "policy/",
    "scripts/ci/",
)


class RemoteContractError(RuntimeError):
    """Raised when the published skill tree violates the remote contract."""


def _extract_local_targets(markdown_path: Path) -> list[str]:
    text = markdown_path.read_text(encoding="utf-8")
    targets: list[str] = []
    for raw_target in LINK_PATTERN.findall(text):
        target = raw_target.strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        targets.append(target)
    return targets


def validate_published_skill_tree(stage_dir: Path) -> None:
    missing = [name for name in (README_NAME, SKILL_NAME) if not (stage_dir / name).exists()]
    if missing:
        raise RemoteContractError(
            f"published skill root is missing required files: {', '.join(missing)}"
        )
    if (stage_dir / SKILL_README_NAME).exists():
        raise RemoteContractError(f"published skill root must not contain {SKILL_README_NAME}")

    package_root = stage_dir.resolve(strict=True)
    for path in sorted(stage_dir.rglob("*")):
        if path.is_dir():
            continue
        rel_path = relative_posix(path, stage_dir)
        if rel_path.startswith(DISALLOWED_PUBLISHED_PREFIXES):
            raise RemoteContractError(f"published skill tree leaked a dev-only path: {rel_path}")
        if rel_path in {"README.md", "SKILL.md"}:
            continue

    for markdown_path in sorted(stage_dir.rglob("*.md")):
        for target in _extract_local_targets(markdown_path):
            path_part = target.split("#", 1)[0]
            if path_part.startswith("/") or ".." in PurePosixPath(path_part).parts:
                raise RemoteContractError(
                    f"published markdown contains a disallowed local link: {target}"
                )

            resolved = (markdown_path.parent / path_part).resolve()
            try:
                resolved.relative_to(package_root)
            except ValueError as exc:
                raise RemoteContractError(
                    f"published markdown link escapes the skill root: {target}"
                ) from exc

            if not resolved.exists():
                rel_markdown = markdown_path.relative_to(stage_dir).as_posix()
                raise RemoteContractError(
                    f"published markdown link target does not exist: {rel_markdown} -> {target}"
                )


def build_synthetic_remote_archive(
    stage_dir: Path,
    archive_path: Path,
    top_level_dir_name: str = SYNTHETIC_ARCHIVE_ROOT,
) -> Path:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(stage_dir.rglob("*")):
            if path.is_dir():
                continue
            rel_path = path.relative_to(stage_dir).as_posix()
            archive.write(path, arcname=f"{top_level_dir_name}/{rel_path}")
    return archive_path


def discover_skill_root(extract_dir: Path) -> Path:
    top_level_candidates: list[Path] = []
    nested_candidates: list[Path] = []
    for marker in sorted(extract_dir.rglob(SKILL_NAME)):
        rel_parent = marker.parent.relative_to(extract_dir)
        depth = len(rel_parent.parts)
        if depth == 1:
            top_level_candidates.append(marker.parent)
        elif depth > 1:
            nested_candidates.append(marker.parent)

    if len(top_level_candidates) == 1 and not nested_candidates:
        return top_level_candidates[0]
    if not top_level_candidates and len(nested_candidates) == 1:
        nested = nested_candidates[0].relative_to(extract_dir).as_posix()
        raise RemoteContractError(f"subpath not supported: discovered nested skill root {nested}")
    if not top_level_candidates and not nested_candidates:
        raise RemoteContractError("missing SKILL.md")

    discovered = [
        path.relative_to(extract_dir).as_posix()
        for path in (top_level_candidates + nested_candidates)
    ]
    raise RemoteContractError(f"multiple skill roots: {discovered}")


def extract_and_discover_skill_root(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)
    return discover_skill_root(destination)


def validate_cc_switch_remote_contract(repo_root: Path = REPO_ROOT) -> None:
    with tempfile.TemporaryDirectory(prefix="m2c-cc-switch-remote-") as temp_dir:
        temp_root = Path(temp_dir)
        stage_dir = temp_root / "published-skill-tree"
        allowlist = load_allowlist(repo_root / "policy" / "package-allowlist.txt")
        source_files = collect_package_files(repo_root=repo_root, allowlist=allowlist)
        build_published_skill_tree(
            repo_root=repo_root,
            stage_dir=stage_dir,
            source_files=source_files,
        )
        validate_published_skill_tree(stage_dir)

        archive_path = temp_root / "synthetic-remote-skill.zip"
        build_synthetic_remote_archive(stage_dir=stage_dir, archive_path=archive_path)
        discovered_root = extract_and_discover_skill_root(
            archive_path=archive_path,
            destination=temp_root / "extract",
        )
        discovered_name = discovered_root.relative_to(temp_root / "extract").as_posix()
        if discovered_name != SYNTHETIC_ARCHIVE_ROOT:
            raise RemoteContractError(
                "skill root discovery drifted: "
                f"expected {SYNTHETIC_ARCHIVE_ROOT!r}, got {discovered_name!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the published skill tree against the CC Switch remote contract."
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root to validate.",
    )
    args = parser.parse_args()

    validate_cc_switch_remote_contract(repo_root=Path(args.repo_root))
    print("CC Switch remote contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
