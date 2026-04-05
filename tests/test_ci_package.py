import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.ci.package_generic import PackagingError, build_package, collect_package_files


class PackageGenericTests(unittest.TestCase):
    def _create_repo(self, root: Path) -> list[str]:
        (root / "fixtures").mkdir(parents=True, exist_ok=True)
        (root / "m2c_pipeline").mkdir(parents=True, exist_ok=True)
        (root / "references").mkdir(parents=True, exist_ok=True)
        (root / "evals").mkdir(parents=True, exist_ok=True)
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / "fixtures" / "minimal-input.md").write_text("```mermaid\nflowchart LR\nA-->B\n```\n", encoding="utf-8")
        (root / "m2c_pipeline" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "references" / "runtime-commands.md").write_text("runtime\n", encoding="utf-8")
        (root / "evals" / "offline-dry-run.md").write_text("eval\n", encoding="utf-8")
        (root / "scripts" / "bootstrap_env.sh").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
        (root / "SKILL.md").write_text(
            "---\n"
            "name: m2c-pipeline\n"
            "description: Converts Mermaid diagrams in Markdown into Vertex AI image runs. "
            "Use when users want CLI execution. Do not use when the task is general Markdown editing.\n"
            "---\n\n"
            "# m2c-pipeline\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text("readme\n", encoding="utf-8")
        (root / "SKILL_README.md").write_text("# m2c-pipeline\n\nSkill README.\n", encoding="utf-8")
        (root / "LICENSE").write_text("license\n", encoding="utf-8")
        (root / ".env.example").write_text("M2C_PROJECT_ID=demo\n", encoding="utf-8")
        (root / "requirements.txt").write_text("Pillow>=10.0.0\n", encoding="utf-8")
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

    def test_build_package_creates_expected_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = self._create_repo(repo_root)

            archive_path, checksum_path = build_package(
                output_dir=repo_root / "dist",
                repo_root=repo_root,
                allowlist=allowlist,
                version="9.9.9",
            )

            self.assertTrue(archive_path.exists())
            self.assertTrue(checksum_path.exists())
            with zipfile.ZipFile(archive_path) as archive:
                members = sorted(archive.namelist())
                root_readme = archive.read("m2c-pipeline-generic-v9.9.9/README.md").decode("utf-8")

        self.assertEqual(
            members,
            [
                "m2c-pipeline-generic-v9.9.9/.env.example",
                "m2c-pipeline-generic-v9.9.9/LICENSE",
                "m2c-pipeline-generic-v9.9.9/README.md",
                "m2c-pipeline-generic-v9.9.9/SKILL.md",
                "m2c-pipeline-generic-v9.9.9/evals/offline-dry-run.md",
                "m2c-pipeline-generic-v9.9.9/fixtures/minimal-input.md",
                "m2c-pipeline-generic-v9.9.9/m2c_pipeline/module.py",
                "m2c-pipeline-generic-v9.9.9/references/runtime-commands.md",
                "m2c-pipeline-generic-v9.9.9/requirements.txt",
                "m2c-pipeline-generic-v9.9.9/scripts/bootstrap_env.sh",
            ],
        )
        self.assertEqual(root_readme, "# m2c-pipeline\n\nSkill README.\n")
        self.assertNotIn("m2c-pipeline-generic-v9.9.9/SKILL_README.md", members)
        self.assertNotIn("m2c-pipeline-generic-v9.9.9/m2c-pipeline/README.md", members)

    def test_collect_package_files_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = self._create_repo(repo_root)
            outside = repo_root.parent / "outside.py"
            outside.write_text("VALUE = 99\n", encoding="utf-8")
            (repo_root / "m2c_pipeline" / "linked.py").symlink_to(outside)

            with self.assertRaises(PackagingError):
                collect_package_files(repo_root=repo_root, allowlist=allowlist)

    def test_collect_package_files_skips_python_cache_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = self._create_repo(repo_root)
            (repo_root / "m2c_pipeline" / "__pycache__").mkdir()
            (repo_root / "m2c_pipeline" / "__pycache__" / "module.cpython-311.pyc").write_bytes(b"pyc")
            (repo_root / "m2c_pipeline" / "module.pyo").write_bytes(b"pyo")

            files = collect_package_files(repo_root=repo_root, allowlist=allowlist)
            rel_paths = {f.relative_to(repo_root).as_posix() for f in files}

        self.assertIn("m2c_pipeline/module.py", rel_paths)
        self.assertNotIn("m2c_pipeline/module.pyo", rel_paths)
        self.assertNotIn("m2c_pipeline/__pycache__/module.cpython-311.pyc", rel_paths)
