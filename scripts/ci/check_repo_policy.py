"""Validate repository policy guardrails."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import REPO_ROOT

WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
REQUIRED_WORKFLOWS = {
    "ci.yml",
    "claude-review.yml",
    "governance-audit.yml",
    "release-generic.yml",
}
# First-party Anthropic actions are exempt from SHA-pin enforcement.
UNPINNED_ACTION_ALLOWLIST = {
    "anthropics/claude-code-action",
}
WORKFLOW_USE_PATTERN = re.compile(r"^\s*uses:\s*([^\s@]+)@([^\s#]+)\s*$", re.MULTILINE)
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DENIED_JSON_PATTERNS = (
    "application_default_credentials.json",
    "service-account",
    "sa-key",
    "gcp-key",
    "gcp-credentials",
    "vertex-adc",
)


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        cwd=REPO_ROOT,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _validate_tracked_files(tracked_files: list[str]) -> None:
    violations: list[str] = []
    for rel_path in tracked_files:
        path = Path(rel_path)
        lower_name = path.name.lower()
        lower_path = rel_path.lower()
        if rel_path == ".env" or (rel_path.startswith(".env.") and rel_path != ".env.example"):
            violations.append(rel_path)
        if lower_name in {"openai.yaml", "openai.yml", "codex.yaml", "codex.yml"}:
            violations.append(rel_path)
        if lower_name.endswith(".json") and any(pattern in lower_name for pattern in DENIED_JSON_PATTERNS):
            violations.append(rel_path)
        if lower_path.startswith(("output/", "tests/output/", "venv/", ".venv/", ".idea/", ".vscode/")):
            violations.append(rel_path)
        if lower_name.endswith(".iml"):
            violations.append(rel_path)

    if violations:
        raise ValueError(f"Tracked files violate repo policy: {sorted(set(violations))}")


def _validate_workflows() -> None:
    existing = {path.name for path in WORKFLOW_DIR.glob("*.yml")}
    if existing != REQUIRED_WORKFLOWS:
        raise ValueError(
            f"Workflow set must be exactly {sorted(REQUIRED_WORKFLOWS)}, got {sorted(existing)}"
        )

    for workflow_path in sorted(WORKFLOW_DIR.glob("*.yml")):
        text = workflow_path.read_text(encoding="utf-8")

        if not re.search(r"(?m)^permissions:\n  contents: read$", text):
            raise ValueError(f"{workflow_path.name} must define top-level permissions: contents: read")

        uses_refs = WORKFLOW_USE_PATTERN.findall(text)
        for action_name, ref in uses_refs:
            if action_name.startswith("./"):
                continue
            if action_name in UNPINNED_ACTION_ALLOWLIST:
                continue
            if not SHA_PATTERN.fullmatch(ref):
                raise ValueError(
                    f"{workflow_path.name} uses an unpinned action reference: {action_name}@{ref}"
                )

        if workflow_path.name == "ci.yml" and re.search(r"(?m)^\s+paths(-ignore)?:", text):
            raise ValueError("ci.yml must not use paths or paths-ignore filters.")

        write_count = len(re.findall(r"(?m)^\s+contents:\s+write$", text))
        if workflow_path.name == "release-generic.yml":
            if write_count != 1:
                raise ValueError("release-generic.yml must grant contents: write exactly once.")
            if not re.search(
                r"(?ms)^  build-and-release:\n.*?^    permissions:\n      contents: write$",
                text,
            ):
                raise ValueError(
                    "release-generic.yml must scope contents: write to the build-and-release job."
                )
        elif write_count:
            raise ValueError(f"{workflow_path.name} must not request contents: write")


def validate_repo_policy() -> None:
    _validate_tracked_files(_tracked_files())
    _validate_workflows()


def main() -> int:
    validate_repo_policy()
    print("Repository policy validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
