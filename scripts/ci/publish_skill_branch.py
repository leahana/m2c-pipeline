"""Publish allowlisted skill files to the orphan `skill` branch."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import REPO_ROOT, load_version
from scripts.ci.package_generic import (
    PUBLISHED_SKILL_DIR,
    PackagingError,
    build_published_skill_tree,
    collect_package_files,
    published_skill_paths,
)


class PublishError(RuntimeError):
    """Raised when skill branch publishing fails."""


SKILL_BRANCH_DIR = PUBLISHED_SKILL_DIR


def _run(cmd: list[str], cwd: Path, env: dict | None = None) -> str:
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )
    return result.stdout.strip()


def _remote_url() -> str:
    token = os.environ.get("SKILL_PUBLISH_TOKEN", "").strip()
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if token and repository:
        return f"https://x-access-token:{token}@github.com/{repository}.git"
    # Fallback: read from current repo's origin remote (local dev / dry-run)
    try:
        return _run(["git", "remote", "get-url", "origin"], cwd=REPO_ROOT)
    except subprocess.CalledProcessError as exc:
        raise PublishError(
            "Cannot determine remote URL. Set SKILL_PUBLISH_TOKEN + GITHUB_REPOSITORY "
            "or ensure 'origin' remote is configured."
        ) from exc


def collect_skill_files(repo_root: Path = REPO_ROOT) -> list[Path]:
    return collect_package_files(repo_root=repo_root)


def stage_skill_tree(
    repo_root: Path,
    source_files: list[Path],
    stage_dir: Path,
) -> Path:
    try:
        skill_root, _ = build_published_skill_tree(
            repo_root=repo_root,
            stage_dir=stage_dir,
            source_files=source_files,
        )
    except PackagingError as exc:
        raise PublishError(str(exc)) from exc
    return skill_root


def build_skill_commit(
    repo_root: Path,
    source_files: list[Path],
    version: str,
    stage_dir: Path,
) -> None:
    stage_skill_tree(repo_root, source_files, stage_dir)

    git_env = {**os.environ, "GIT_AUTHOR_NAME": "github-actions[bot]",
               "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
               "GIT_COMMITTER_NAME": "github-actions[bot]",
               "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com"}

    _run(["git", "init", "-b", "skill"], cwd=stage_dir)
    _run(["git", "add", "."], cwd=stage_dir)
    _run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", f"skill v{version}"],
        cwd=stage_dir,
        env=git_env,
    )


def push_skill_branch(stage_dir: Path, remote_url: str) -> None:
    _run(
        ["git", "push", "--force", remote_url, "HEAD:refs/heads/skill"],
        cwd=stage_dir,
    )


def publish(
    repo_root: Path = REPO_ROOT,
    dry_run: bool = False,
    version: str | None = None,
    stage_dir: Path | None = None,
) -> None:
    resolved_version = version or load_version()
    source_files = collect_skill_files(repo_root)
    rel_paths = published_skill_paths(source_files, repo_root)

    print(f"Skill branch content for v{resolved_version} ({len(rel_paths)} files):")
    for p in rel_paths:
        print(f"  {p}")

    if stage_dir is not None:
        stage_skill_tree(repo_root, source_files, stage_dir)
        print(f"Staged skill tree at: {stage_dir}")
        return

    if dry_run:
        print("Dry-run mode: skipping git push.")
        return

    remote_url = _remote_url()
    with tempfile.TemporaryDirectory(prefix="m2c-skill-publish-") as tmpdir:
        stage_dir = Path(tmpdir)
        build_skill_commit(repo_root, source_files, resolved_version, stage_dir)
        push_skill_branch(stage_dir, remote_url)

    print(f"Published skill branch: {remote_url} -> refs/heads/skill")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish skill files to the skill branch.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print files to be published without pushing.",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Override version string in commit message.",
    )
    parser.add_argument(
        "--stage-dir",
        default=None,
        help="Stage the published skill tree into an empty local directory without creating a git repo or pushing.",
    )
    args = parser.parse_args()

    publish(
        dry_run=args.dry_run,
        version=args.version,
        stage_dir=Path(args.stage_dir) if args.stage_dir else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
