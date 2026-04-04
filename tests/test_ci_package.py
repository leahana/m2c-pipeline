import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.ci.package_generic import PackagingError, build_package, collect_package_files


class PackageGenericTests(unittest.TestCase):
    def _create_repo(self, root: Path) -> list[str]:
        (root / "m2c_pipeline").mkdir(parents=True, exist_ok=True)
        (root / "references").mkdir(parents=True, exist_ok=True)
        (root / "evals").mkdir(parents=True, exist_ok=True)
        (root / "m2c_pipeline" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "references" / "runtime-commands.md").write_text("runtime\n", encoding="utf-8")
        (root / "evals" / "offline-dry-run.md").write_text("eval\n", encoding="utf-8")
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
        (root / "LICENSE").write_text("license\n", encoding="utf-8")
        (root / ".env.example").write_text("M2C_PROJECT_ID=demo\n", encoding="utf-8")
        (root / "requirements.txt").write_text("Pillow>=10.0.0\n", encoding="utf-8")
        return [
            "SKILL.md",
            "README.md",
            "LICENSE",
            ".env.example",
            "requirements.txt",
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

        self.assertEqual(
            members,
            [
                "m2c-pipeline-generic-v9.9.9/.env.example",
                "m2c-pipeline-generic-v9.9.9/LICENSE",
                "m2c-pipeline-generic-v9.9.9/README.md",
                "m2c-pipeline-generic-v9.9.9/SKILL.md",
                "m2c-pipeline-generic-v9.9.9/evals/offline-dry-run.md",
                "m2c-pipeline-generic-v9.9.9/m2c_pipeline/module.py",
                "m2c-pipeline-generic-v9.9.9/references/runtime-commands.md",
                "m2c-pipeline-generic-v9.9.9/requirements.txt",
            ],
        )

    def test_collect_package_files_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = self._create_repo(repo_root)
            outside = repo_root.parent / "outside.py"
            outside.write_text("VALUE = 99\n", encoding="utf-8")
            (repo_root / "m2c_pipeline" / "linked.py").symlink_to(outside)

            with self.assertRaises(PackagingError):
                collect_package_files(repo_root=repo_root, allowlist=allowlist)
