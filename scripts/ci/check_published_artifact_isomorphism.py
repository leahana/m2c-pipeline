"""Verify release zip and staged skill tree are isomorphic."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import REPO_ROOT
from scripts.ci.package_generic import (
    build_package,
    build_published_skill_tree,
    collect_package_files,
)


class IsomorphismError(RuntimeError):
    """Raised when published artifacts diverge."""


def _collect_tree_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        rel_path = path.relative_to(root).as_posix()
        hashes[rel_path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _extract_archive_root(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)
    top_level_entries = sorted(destination.iterdir(), key=lambda path: path.name)
    if len(top_level_entries) != 1 or not top_level_entries[0].is_dir():
        raise IsomorphismError(
            "Expected exactly one top-level directory and no top-level files in "
            f"{archive_path}, got {top_level_entries!r}"
        )
    return top_level_entries[0]


def assert_isomorphic_trees(archive_tree: Path, staged_tree: Path) -> None:
    archive_hashes = _collect_tree_hashes(archive_tree)
    staged_hashes = _collect_tree_hashes(staged_tree)

    archive_paths = set(archive_hashes)
    staged_paths = set(staged_hashes)
    if archive_paths != staged_paths:
        only_archive = sorted(archive_paths - staged_paths)
        only_staged = sorted(staged_paths - archive_paths)
        raise IsomorphismError(
            "Published path mismatch: "
            f"only_in_archive={only_archive!r}, only_in_staged={only_staged!r}"
        )

    changed = sorted(
        path for path in archive_paths if archive_hashes[path] != staged_hashes[path]
    )
    if changed:
        raise IsomorphismError(f"Published content hash mismatch for paths: {changed!r}")


def validate_published_artifact_isomorphism(repo_root: Path = REPO_ROOT) -> None:
    with tempfile.TemporaryDirectory(prefix="m2c-published-isomorphism-") as temp_dir:
        temp_root = Path(temp_dir)

        archive_path, _ = build_package(output_dir=temp_root / "dist", repo_root=repo_root)
        archive_tree = _extract_archive_root(archive_path, temp_root / "archive")

        staged_tree = temp_root / "staged"
        source_files = collect_package_files(repo_root=repo_root)
        build_published_skill_tree(
            repo_root=repo_root,
            stage_dir=staged_tree,
            source_files=source_files,
        )

        assert_isomorphic_trees(archive_tree=archive_tree, staged_tree=staged_tree)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify release zip and staged skill tree have identical paths and file hashes."
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root to validate.",
    )
    args = parser.parse_args()

    validate_published_artifact_isomorphism(repo_root=Path(args.repo_root))
    print("Published artifact isomorphism validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
