import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.ci.check_repo_policy as check_repo_policy

CHECKOUT_SHA = "692973e3d937129bcbf40652eb9f2f61becf3332"
RELEASE_PLEASE_SHA = "16a9c90856f42705d54a6fda1823352bdc62cf38"


def _write_workflow(path: Path, body: str) -> None:
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")


class RepoPolicyTests(unittest.TestCase):
    def test_validate_workflows_accepts_repository_workflows(self) -> None:
        check_repo_policy._validate_workflows()

    def test_validate_workflows_rejects_write_permissions_outside_release_please(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_dir = Path(tmpdir)
            _write_workflow(
                workflow_dir / "ci.yml",
                f"""
                name: ci
                on:
                  pull_request:
                permissions:
                  contents: read
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    permissions:
                      contents: write
                    steps:
                      - uses: actions/checkout@{CHECKOUT_SHA}
                """,
            )
            _write_workflow(
                workflow_dir / "claude-review.yml",
                f"""
                name: claude-review
                on:
                  issue_comment:
                permissions:
                  contents: read
                jobs:
                  claude-review:
                    runs-on: ubuntu-latest
                    permissions:
                      issues: write
                      pull-requests: write
                    steps:
                      - uses: anthropics/claude-code-action@v1
                """,
            )
            _write_workflow(
                workflow_dir / "governance-audit.yml",
                f"""
                name: governance-audit
                on:
                  workflow_dispatch:
                permissions:
                  contents: read
                jobs:
                  audit:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@{CHECKOUT_SHA}
                """,
            )
            _write_workflow(
                workflow_dir / "release-please.yml",
                f"""
                name: release-please
                on:
                  push:
                    branches:
                      - main
                permissions:
                  contents: read
                jobs:
                  release-please:
                    runs-on: ubuntu-latest
                    permissions:
                      contents: write
                      issues: write
                      pull-requests: write
                    steps:
                      - uses: googleapis/release-please-action@{RELEASE_PLEASE_SHA}
                """,
            )

            with patch.object(check_repo_policy, "WORKFLOW_DIR", workflow_dir):
                with self.assertRaisesRegex(ValueError, "ci.yml must not request write permissions"):
                    check_repo_policy._validate_workflows()

    def test_validate_workflows_rejects_incorrect_release_please_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_dir = Path(tmpdir)
            _write_workflow(
                workflow_dir / "ci.yml",
                f"""
                name: ci
                on:
                  pull_request:
                permissions:
                  contents: read
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@{CHECKOUT_SHA}
                """,
            )
            _write_workflow(
                workflow_dir / "claude-review.yml",
                f"""
                name: claude-review
                on:
                  issue_comment:
                permissions:
                  contents: read
                jobs:
                  claude-review:
                    runs-on: ubuntu-latest
                    permissions:
                      issues: write
                      pull-requests: write
                    steps:
                      - uses: anthropics/claude-code-action@v1
                """,
            )
            _write_workflow(
                workflow_dir / "governance-audit.yml",
                f"""
                name: governance-audit
                on:
                  workflow_dispatch:
                permissions:
                  contents: read
                jobs:
                  audit:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@{CHECKOUT_SHA}
                """,
            )
            _write_workflow(
                workflow_dir / "release-please.yml",
                f"""
                name: release-please
                on:
                  push:
                    branches:
                      - main
                permissions:
                  contents: read
                jobs:
                  release-please:
                    runs-on: ubuntu-latest
                    permissions:
                      contents: write
                      pull-requests: write
                    steps:
                      - uses: googleapis/release-please-action@{RELEASE_PLEASE_SHA}
                """,
            )

            with patch.object(check_repo_policy, "WORKFLOW_DIR", workflow_dir):
                with self.assertRaisesRegex(
                    ValueError,
                    "release-please.yml must request contents/issues/pull-requests write exactly once",
                ):
                    check_repo_policy._validate_workflows()
