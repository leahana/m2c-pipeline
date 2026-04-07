"""Build a timestamped local preview skill package for manual installs."""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import REPO_ROOT, load_version
from scripts.ci.package_generic import (
    apply_package_identity,
    build_published_skill_tree,
    collect_package_files,
    verify_archive,
    write_archive,
    write_checksum,
)

DEFAULT_OUTPUT_DIR = "dist"
DEFAULT_PREVIEW_PREFIX = "m2c-pipeline-preview"
TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


def format_preview_timestamp(built_at: datetime | None = None) -> str:
    return (built_at or datetime.now()).strftime(TIMESTAMP_FORMAT)


def preview_identity(version: str, built_at: datetime | None = None) -> str:
    return f"{DEFAULT_PREVIEW_PREFIX}-v{version}-{format_preview_timestamp(built_at)}"


def build_preview_package(
    output_dir: Path,
    repo_root: Path = REPO_ROOT,
    allowlist: list[str] | None = None,
    version: str | None = None,
    built_at: datetime | None = None,
) -> tuple[Path, Path, str]:
    resolved_version = version or load_version()
    identity = preview_identity(resolved_version, built_at)

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{identity}.zip"
    checksum_path = output_dir / f"{identity}.zip.sha256"

    source_files = collect_package_files(repo_root, allowlist)

    with tempfile.TemporaryDirectory(prefix="m2c-preview-package-") as temp_dir:
        temp_root = Path(temp_dir)
        stage_root = temp_root / "published-preview-tree"
        _, expected_rel_paths = build_published_skill_tree(
            repo_root=repo_root,
            stage_dir=stage_root,
            source_files=source_files,
        )
        apply_package_identity(
            stage_root,
            skill_name=identity,
            archive_basename=identity,
        )
        write_archive(archive_path, stage_root, expected_rel_paths, identity)

    verify_archive(archive_path, expected_rel_paths, identity)
    write_checksum(checksum_path, archive_path)
    return archive_path, checksum_path, identity


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a timestamped local preview skill package for manual installs."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the preview archive and checksum will be written.",
    )
    args = parser.parse_args()

    archive_path, checksum_path, identity = build_preview_package(Path(args.output_dir))
    print(f"Built preview archive: {archive_path}")
    print(f"Wrote checksum: {checksum_path}")
    print(f"Preview skill name: {identity}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
