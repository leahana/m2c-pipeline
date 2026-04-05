import tempfile
import unittest
from pathlib import Path

from scripts.ci.publish_skill_branch import build_skill_commit, publish, stage_skill_tree


EXCLUDED_PREFIXES = ("tests/", ".github/", "policy/", "scripts/ci/")


def _create_repo(root: Path) -> list[str]:
    (root / "fixtures").mkdir()
    (root / "m2c_pipeline" / "templates").mkdir(parents=True)
    (root / "references").mkdir()
    (root / "evals").mkdir()
    (root / "tests" / "fixtures").mkdir(parents=True)
    (root / "scripts" / "ci").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "policy").mkdir()

    (root / "m2c_pipeline" / "__init__.py").write_text("", encoding="utf-8")
    (root / "m2c_pipeline" / "templates" / "base.py").write_text("", encoding="utf-8")
    (root / "fixtures" / "minimal-input.md").write_text("```mermaid\nflowchart LR\nA-->B\n```\n", encoding="utf-8")
    (root / "references" / "runtime-commands.md").write_text("runtime\n", encoding="utf-8")
    (root / "evals" / "offline-dry-run.md").write_text("eval\n", encoding="utf-8")
    (root / "scripts" / "bootstrap_env.sh").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
    (root / "SKILL.md").write_text(
        "---\nname: m2c-pipeline\n"
        "description: Converts Mermaid diagrams in Markdown into Vertex AI image runs. "
        "Use when users want CLI execution. Do not use when the task is general Markdown editing.\n"
        "---\n\n# m2c-pipeline\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("readme\n", encoding="utf-8")
    (root / "SKILL_README.md").write_text("# m2c-pipeline\n\nSkill README content.\n", encoding="utf-8")
    (root / "LICENSE").write_text("license\n", encoding="utf-8")
    (root / ".env.example").write_text("M2C_PROJECT_ID=demo\n", encoding="utf-8")
    (root / "requirements.txt").write_text("Pillow>=10.0.0\n", encoding="utf-8")
    (root / "m2c_pipeline" / "version.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")

    # dev-only files that must NOT be included
    (root / "tests" / "fixtures" / "test_input.md").write_text("mermaid\n", encoding="utf-8")
    (root / "scripts" / "ci" / "common.py").write_text("", encoding="utf-8")
    (root / ".github" / "workflows" / "ci.yml").write_text("", encoding="utf-8")
    (root / "policy" / "governance.json").write_text("{}", encoding="utf-8")

    return [
        "SKILL.md",
        "SKILL_README.md",
        "LICENSE",
        ".env.example",
        "requirements.txt",
        "scripts/bootstrap_env.sh",
        "fixtures/**",
        "references/**",
        "evals/**",
        "m2c_pipeline/**",
    ]


class PublishSkillBranchTests(unittest.TestCase):
    def test_collect_only_allowlisted_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = _create_repo(repo_root)

            # Write allowlist file so collect_package_files can find it
            policy_dir = repo_root / "policy"
            policy_dir.mkdir(exist_ok=True)
            (policy_dir / "package-allowlist.txt").write_text(
                "\n".join(allowlist) + "\n", encoding="utf-8"
            )

            from scripts.ci.package_generic import collect_package_files
            files = collect_package_files(repo_root=repo_root, allowlist=allowlist)
            rel_paths = {f.relative_to(repo_root).as_posix() for f in files}

        # Must include all allowlisted content
        self.assertIn("SKILL.md", rel_paths)
        self.assertIn("SKILL_README.md", rel_paths)
        self.assertIn("LICENSE", rel_paths)
        self.assertIn(".env.example", rel_paths)
        self.assertIn("requirements.txt", rel_paths)
        self.assertIn("fixtures/minimal-input.md", rel_paths)
        self.assertIn("scripts/bootstrap_env.sh", rel_paths)
        self.assertIn("references/runtime-commands.md", rel_paths)
        self.assertIn("evals/offline-dry-run.md", rel_paths)
        self.assertIn("m2c_pipeline/__init__.py", rel_paths)
        self.assertIn("m2c_pipeline/templates/base.py", rel_paths)
        self.assertNotIn("README.md", rel_paths)

        # Must NOT include dev-only files
        for path in rel_paths:
            self.assertFalse(path.startswith(EXCLUDED_PREFIXES), f"Dev file leaked into skill: {path}")

    def test_staged_tree_matches_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = _create_repo(repo_root)

            from scripts.ci.package_generic import collect_package_files, published_skill_paths
            source_files = collect_package_files(repo_root=repo_root, allowlist=allowlist)

            with tempfile.TemporaryDirectory() as stagedir:
                stage_dir = Path(stagedir)
                stage_skill_tree(repo_root, source_files, stage_dir)
                staged = {
                    p.relative_to(stage_dir).as_posix()
                    for p in stage_dir.rglob("*")
                    if p.is_file()
                }
            expected = set(published_skill_paths(source_files, repo_root))
            self.assertEqual(staged, expected)
            self.assertNotIn("SKILL_README.md", staged)
            self.assertNotIn("m2c-pipeline/README.md", staged)

    def test_no_hidden_files_except_env_example(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = _create_repo(repo_root)

            from scripts.ci.package_generic import collect_package_files
            files = collect_package_files(repo_root=repo_root, allowlist=allowlist)
            rel_paths = [f.relative_to(repo_root).as_posix() for f in files]

        for path in rel_paths:
            parts = Path(path).parts
            hidden = [p for p in parts if p.startswith(".") and p != ".env.example"]
            self.assertEqual(hidden, [], f"Hidden file in skill: {path}")

    def test_build_skill_commit_creates_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = _create_repo(repo_root)

            from scripts.ci.package_generic import collect_package_files
            source_files = collect_package_files(repo_root=repo_root, allowlist=allowlist)

            with tempfile.TemporaryDirectory() as stagedir:
                stage_dir = Path(stagedir)
                build_skill_commit(repo_root, source_files, "9.9.9", stage_dir)

                result = Path(stagedir)
                self.assertTrue((result / ".git").exists())

                import subprocess
                log = subprocess.run(
                    ["git", "log", "--oneline"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                self.assertIn("skill v9.9.9", log.stdout)
                readme = subprocess.run(
                    ["git", "show", "HEAD:README.md"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                self.assertEqual(readme.stdout, "# m2c-pipeline\n\nSkill README content.\n")
                skill = subprocess.run(
                    ["git", "show", "HEAD:SKILL.md"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                self.assertIn("name: m2c-pipeline", skill.stdout)
                ls_tree = subprocess.run(
                    ["git", "ls-tree", "--name-only", "HEAD"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                root_entries = ls_tree.stdout.splitlines()
                self.assertIn("README.md", root_entries)
                self.assertIn("SKILL.md", root_entries)
                self.assertIn("fixtures", root_entries)
                self.assertIn("scripts", root_entries)
                self.assertIn("m2c_pipeline", root_entries)
                self.assertNotIn("m2c-pipeline", root_entries)
                self.assertNotIn("SKILL_README.md", root_entries)

    def test_publish_stage_dir_writes_skill_tree_without_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = _create_repo(repo_root)

            policy_dir = repo_root / "policy"
            policy_dir.mkdir(exist_ok=True)
            (policy_dir / "package-allowlist.txt").write_text(
                "\n".join(allowlist) + "\n", encoding="utf-8"
            )

            with tempfile.TemporaryDirectory() as stagedir:
                stage_dir = Path(stagedir) / "stage"
                publish(repo_root=repo_root, stage_dir=stage_dir, version="9.9.9")

                self.assertFalse((stage_dir / ".git").exists())
                self.assertEqual(
                    (stage_dir / "README.md").read_text(encoding="utf-8"),
                    "# m2c-pipeline\n\nSkill README content.\n",
                )
                self.assertTrue((stage_dir / "scripts" / "bootstrap_env.sh").exists())
                self.assertTrue((stage_dir / "fixtures" / "minimal-input.md").exists())
                self.assertFalse((stage_dir / "m2c-pipeline").exists())
                self.assertFalse((stage_dir / "tests").exists())
                self.assertFalse((stage_dir / "SKILL_README.md").exists())
