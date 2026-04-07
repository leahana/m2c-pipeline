"""Build and verify the generic Anthropic skill package."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import (
    REPO_ROOT,
    load_allowlist,
    load_version,
    relative_posix,
    resolve_within_repo,
)


class PackagingError(RuntimeError):
    """Raised when packaging validation fails."""


EXCLUDED_PACKAGE_PARTS = {"__pycache__"}
EXCLUDED_PACKAGE_SUFFIXES = {".pyc", ".pyo"}
ROOT_README = "README.md"
SKILL_README = "SKILL_README.md"
DEFAULT_PACKAGE_NAME = "m2c-pipeline-generic"
DEFAULT_SKILL_NAME = "m2c-pipeline"
DEFAULT_SKILL_TITLE = f"# {DEFAULT_SKILL_NAME}"
SKILL_NAME_PATTERN = re.compile(
    r"(?m)^name:[ \t]*" + re.escape(DEFAULT_SKILL_NAME) + r"[ \t]*$"
)
SKILL_TITLE_PATTERN = re.compile(
    r"(?m)^" + re.escape(DEFAULT_SKILL_TITLE) + r"[ \t]*$"
)


def package_basename(version: str | None = None, package_name: str = DEFAULT_PACKAGE_NAME) -> str:
    resolved_version = version or load_version()
    return f"{package_name}-v{resolved_version}"


def _is_package_file(path: Path, repo_root: Path) -> bool:
    rel_parts = path.relative_to(repo_root).parts
    return (
        not any(part in EXCLUDED_PACKAGE_PARTS for part in rel_parts)
        and path.suffix not in EXCLUDED_PACKAGE_SUFFIXES
    )


def _collect_recursive(base_dir: Path, repo_root: Path) -> list[Path]:
    if not base_dir.exists():
        raise PackagingError(f"Allowlisted path does not exist: {base_dir}")

    collected: list[Path] = []
    for root, dirnames, filenames in os.walk(base_dir, followlinks=False):
        root_path = Path(root)
        for dirname in list(dirnames):
            dir_path = root_path / dirname
            if dir_path.is_symlink():
                raise PackagingError(f"Symlinked directories are not allowed: {dir_path}")
        for filename in filenames:
            file_path = root_path / filename
            if file_path.is_symlink():
                raise PackagingError(f"Symlinked files are not allowed: {file_path}")
            resolve_within_repo(file_path, repo_root)
            if not _is_package_file(file_path, repo_root):
                continue
            collected.append(file_path)
    return collected


def collect_package_files(
    repo_root: Path = REPO_ROOT,
    allowlist: list[str] | None = None,
) -> list[Path]:
    patterns = allowlist or load_allowlist()
    collected: dict[str, Path] = {}
    for pattern in patterns:
        if pattern.endswith("/**"):
            base_dir = repo_root / pattern[:-3]
            candidates = _collect_recursive(base_dir, repo_root)
        else:
            path = repo_root / pattern
            if not path.exists():
                raise PackagingError(f"Allowlisted path does not exist: {path}")
            if path.is_symlink():
                raise PackagingError(f"Symlinked paths are not allowed: {path}")
            if path.is_dir():
                raise PackagingError(f"Directory allowlist entries must use /**: {pattern}")
            resolve_within_repo(path, repo_root)
            if not _is_package_file(path, repo_root):
                raise PackagingError(f"Allowlisted path is not distributable: {path}")
            candidates = [path]

        for candidate in candidates:
            rel_path = relative_posix(candidate, repo_root)
            collected[rel_path] = candidate

    return [collected[key] for key in sorted(collected)]


def _published_rel_path(source_rel_path: str) -> str | None:
    if source_rel_path == ROOT_README:
        return None
    if source_rel_path == SKILL_README:
        return ROOT_README
    return source_rel_path


def _build_publish_mapping(
    source_files: list[Path],
    repo_root: Path = REPO_ROOT,
) -> list[tuple[str, Path]]:
    published: dict[str, Path] = {}
    for source_path in source_files:
        source_rel_path = relative_posix(source_path, repo_root)
        published_rel_path = _published_rel_path(source_rel_path)
        if published_rel_path is None:
            continue
        if published_rel_path in published:
            raise PackagingError(
                f"Duplicate published path detected: {published_rel_path}"
            )
        published[published_rel_path] = source_path

    if ROOT_README not in published:
        raise PackagingError(
            f"Allowlisted publish source is missing required {SKILL_README}."
        )

    return [(rel_path, published[rel_path]) for rel_path in sorted(published)]


def stage_package_files(
    package_root: Path,
    published_files: list[tuple[str, Path]],
) -> list[Path]:
    staged_paths: list[Path] = []
    for rel_path, source_path in published_files:
        destination = package_root / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        staged_paths.append(destination)
    return staged_paths


def _validate_staged_tree(package_root: Path, expected_rel_paths: list[str]) -> None:
    discovered: list[str] = []
    for path in sorted(package_root.rglob("*")):
        if path.is_dir():
            continue
        rel_path = path.relative_to(package_root).as_posix()
        if any(
            part.startswith(".") and part != ".env.example"
            for part in Path(rel_path).parts
        ):
            raise PackagingError(f"Hidden staged file is not allowed: {rel_path}")
        if rel_path.startswith("/") or ".." in Path(rel_path).parts:
            raise PackagingError(f"Unsafe staged path detected: {rel_path}")
        discovered.append(rel_path)

    if discovered != expected_rel_paths:
        raise PackagingError(
            f"Staged package contents mismatch. Expected {expected_rel_paths!r}, got {discovered!r}"
        )


def apply_package_identity(
    package_root: Path,
    skill_name: str,
    archive_basename: str | None = None,
) -> None:
    skill_path = package_root / "SKILL.md"
    readme_path = package_root / ROOT_README

    skill_text = skill_path.read_text(encoding="utf-8")
    updated_skill_text, skill_name_replacements = SKILL_NAME_PATTERN.subn(
        f"name: {skill_name}",
        skill_text,
        count=1,
    )
    updated_skill_text, skill_title_replacements = SKILL_TITLE_PATTERN.subn(
        f"# {skill_name}",
        updated_skill_text,
        count=1,
    )
    if skill_name_replacements != 1 or skill_title_replacements != 1:
        raise PackagingError("Could not rewrite SKILL.md identity.")
    updated_skill_text = updated_skill_text.replace(
        f"`{DEFAULT_SKILL_NAME}`",
        f"`{skill_name}`",
    )
    skill_path.write_text(updated_skill_text, encoding="utf-8")

    readme_text = readme_path.read_text(encoding="utf-8")
    updated_readme_text, readme_title_replacements = SKILL_TITLE_PATTERN.subn(
        f"# {skill_name}",
        readme_text,
        count=1,
    )
    if readme_title_replacements != 1:
        raise PackagingError("Could not rewrite README.md identity.")
    updated_readme_text = updated_readme_text.replace(
        f"`{DEFAULT_SKILL_NAME}`",
        f"`{skill_name}`",
    )
    if archive_basename is not None:
        updated_readme_text = updated_readme_text.replace(
            "m2c-pipeline-generic-v<version>.zip",
            f"{archive_basename}.zip",
        )
    readme_path.write_text(updated_readme_text, encoding="utf-8")


def write_archive(
    archive_path: Path,
    stage_root: Path,
    expected_rel_paths: list[str],
    basename: str,
) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        seen_members: set[str] = set()
        for rel_path in expected_rel_paths:
            member_name = f"{basename}/{rel_path}"
            if member_name in seen_members:
                raise PackagingError(f"Duplicate archive member detected: {member_name}")
            seen_members.add(member_name)
            archive.write(stage_root / rel_path, arcname=member_name)


def write_checksum(checksum_path: Path, archive_path: Path) -> None:
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")


def published_skill_paths(
    source_files: list[Path],
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    return [rel_path for rel_path, _ in _build_publish_mapping(source_files, repo_root)]


def build_published_skill_tree(
    repo_root: Path,
    stage_dir: Path,
    source_files: list[Path] | None = None,
    allowlist: list[str] | None = None,
) -> tuple[Path, list[str]]:
    if stage_dir.exists():
        if any(stage_dir.iterdir()):
            raise PackagingError(f"Stage directory must be empty: {stage_dir}")
    else:
        stage_dir.mkdir(parents=True, exist_ok=True)

    resolved_source_files = source_files or collect_package_files(repo_root, allowlist)
    published_files = _build_publish_mapping(resolved_source_files, repo_root)
    stage_package_files(stage_dir, published_files)

    expected_rel_paths = published_skill_paths(resolved_source_files, repo_root)
    _validate_staged_tree(stage_dir, expected_rel_paths)
    return stage_dir, expected_rel_paths


def build_package(
    output_dir: Path,
    repo_root: Path = REPO_ROOT,
    allowlist: list[str] | None = None,
    version: str | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    basename = package_basename(version)
    archive_path = output_dir / f"{basename}.zip"
    checksum_path = output_dir / f"{basename}.zip.sha256"

    source_files = collect_package_files(repo_root, allowlist)

    with tempfile.TemporaryDirectory(prefix="m2c-package-") as temp_dir:
        temp_root = Path(temp_dir)
        stage_root = temp_root / "published-skill-tree"
        _, expected_rel_paths = build_published_skill_tree(
            repo_root=repo_root,
            stage_dir=stage_root,
            source_files=source_files,
        )
        write_archive(archive_path, stage_root, expected_rel_paths, basename)

    verify_archive(archive_path, expected_rel_paths, basename)
    write_checksum(checksum_path, archive_path)
    return archive_path, checksum_path


def verify_archive(archive_path: Path, expected_rel_paths: list[str], basename: str) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        members = sorted(archive.namelist())
    expected_members = [f"{basename}/{rel_path}" for rel_path in expected_rel_paths]
    if members != expected_members:
        raise PackagingError(
            f"Archive contents mismatch. Expected {expected_members!r}, got {members!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the generic Anthropic skill package.")
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Directory where the archive and checksum will be written.",
    )
    args = parser.parse_args()

    archive_path, checksum_path = build_package(Path(args.output_dir))
    print(f"Built archive: {archive_path}")
    print(f"Wrote checksum: {checksum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
