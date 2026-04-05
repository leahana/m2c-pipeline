import tempfile
import unittest
from pathlib import Path

from scripts.ci.publish_skill_branch import SKILL_BRANCH_DIR, build_skill_commit


EXCLUDED_DIRS = {"tests", "scripts", ".github", "policy"}


def _create_repo(root: Path) -> list[str]:
    (root / "m2c_pipeline" / "templates").mkdir(parents=True)
    (root / "references").mkdir()
    (root / "evals").mkdir()
    (root / "tests" / "fixtures").mkdir(parents=True)
    (root / "scripts" / "ci").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "policy").mkdir()

    (root / "m2c_pipeline" / "__init__.py").write_text("", encoding="utf-8")
    (root / "m2c_pipeline" / "templates" / "base.py").write_text("", encoding="utf-8")
    (root / "references" / "runtime-commands.md").write_text("runtime\n", encoding="utf-8")
    (root / "evals" / "offline-dry-run.md").write_text("eval\n", encoding="utf-8")
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
        "README.md",
        "LICENSE",
        ".env.example",
        "requirements.txt",
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
        self.assertIn("README.md", rel_paths)
        self.assertIn("LICENSE", rel_paths)
        self.assertIn(".env.example", rel_paths)
        self.assertIn("requirements.txt", rel_paths)
        self.assertIn("references/runtime-commands.md", rel_paths)
        self.assertIn("evals/offline-dry-run.md", rel_paths)
        self.assertIn("m2c_pipeline/__init__.py", rel_paths)
        self.assertIn("m2c_pipeline/templates/base.py", rel_paths)

        # Must NOT include dev-only files
        for path in rel_paths:
            top = Path(path).parts[0]
            self.assertNotIn(top, EXCLUDED_DIRS, f"Dev file leaked into skill: {path}")

    def test_staged_tree_matches_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = _create_repo(repo_root)

            from scripts.ci.package_generic import collect_package_files, stage_package_files
            source_files = collect_package_files(repo_root=repo_root, allowlist=allowlist)

            with tempfile.TemporaryDirectory() as stagedir:
                stage_dir = Path(stagedir)
                stage_package_files(repo_root, stage_dir, source_files)
                staged = {
                    p.relative_to(stage_dir).as_posix()
                    for p in stage_dir.rglob("*")
                    if p.is_file()
                }

        expected = {f.relative_to(repo_root).as_posix() for f in source_files}
        self.assertEqual(staged, expected)

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
                    ["git", "show", f"HEAD:{SKILL_BRANCH_DIR}/README.md"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                self.assertEqual(readme.stdout, "# m2c-pipeline\n\nSkill README content.\n")
                root_readme = subprocess.run(
                    ["git", "show", "HEAD:README.md"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                self.assertEqual(root_readme.stdout, readme.stdout)
                skill = subprocess.run(
                    ["git", "show", f"HEAD:{SKILL_BRANCH_DIR}/SKILL.md"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                self.assertIn("name: m2c-pipeline", skill.stdout)
                ls_tree = subprocess.run(
                    ["git", "ls-tree", "--name-only", "HEAD"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                root_entries = ls_tree.stdout.splitlines()
                self.assertEqual(root_entries, ["README.md", SKILL_BRANCH_DIR])
                nested_tree = subprocess.run(
                    ["git", "ls-tree", "--name-only", f"HEAD:{SKILL_BRANCH_DIR}"],
                    capture_output=True, text=True, cwd=stage_dir, check=True,
                )
                nested_entries = nested_tree.stdout.splitlines()
                self.assertIn("SKILL.md", nested_entries)
                self.assertIn("README.md", nested_entries)
                self.assertNotIn("SKILL_README.md", nested_entries)
                self.assertNotIn("SKILL_README.md", root_entries)
                self.assertNotIn("SKILL.md", root_entries)
