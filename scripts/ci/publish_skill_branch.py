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
from scripts.ci.package_generic import collect_package_files, stage_package_files


class PublishError(RuntimeError):
    """Raised when skill branch publishing fails."""


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


def build_skill_commit(
    repo_root: Path,
    source_files: list[Path],
    version: str,
    stage_dir: Path,
) -> None:
    stage_package_files(repo_root, stage_dir, source_files)

    git_env = {**os.environ, "GIT_AUTHOR_NAME": "github-actions[bot]",
               "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
               "GIT_COMMITTER_NAME": "github-actions[bot]",
               "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com"}

    _run(["git", "init", "-b", "skill"], cwd=stage_dir)
    _run(["git", "add", "."], cwd=stage_dir)
    _run(
        ["git", "commit", "-m", f"skill v{version}"],
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
) -> None:
    resolved_version = version or load_version()
    source_files = collect_skill_files(repo_root)
    rel_paths = [f.relative_to(repo_root).as_posix() for f in source_files]

    print(f"Skill branch content for v{resolved_version} ({len(source_files)} files):")
    for p in rel_paths:
        print(f"  {p}")

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
    args = parser.parse_args()

    publish(dry_run=args.dry_run, version=args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
