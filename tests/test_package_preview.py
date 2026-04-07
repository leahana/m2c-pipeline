import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path

from scripts.dev.package_preview import build_preview_package, preview_identity


class PackagePreviewTests(unittest.TestCase):
    def _create_repo(self, root: Path) -> list[str]:
        (root / "fixtures").mkdir(parents=True, exist_ok=True)
        (root / "m2c_pipeline").mkdir(parents=True, exist_ok=True)
        (root / "references").mkdir(parents=True, exist_ok=True)
        (root / "evals").mkdir(parents=True, exist_ok=True)
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / "fixtures" / "minimal-input.md").write_text(
            "```mermaid\nflowchart LR\nA-->B\n```\n",
            encoding="utf-8",
        )
        (root / "m2c_pipeline" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "references" / "runtime-commands.md").write_text("runtime\n", encoding="utf-8")
        (root / "evals" / "offline-dry-run.md").write_text("eval\n", encoding="utf-8")
        (root / "scripts" / "bootstrap_env.sh").write_text(
            "#!/usr/bin/env sh\n",
            encoding="utf-8",
        )
        (root / "SKILL.md").write_text(
            "---\n"
            "name: m2c-pipeline\n"
            "description: Converts Mermaid diagrams in Markdown into Vertex AI image runs. "
            "Use when users want CLI execution. Do not use when the task is general Markdown editing.\n"
            "---\n\n"
            "# m2c-pipeline\n\n"
            "Use `m2c-pipeline` for local testing.\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text("readme\n", encoding="utf-8")
        (root / "SKILL_README.md").write_text(
            "# m2c-pipeline\n\n"
            "Install `m2c-pipeline` from `m2c-pipeline-generic-v<version>.zip`.\n",
            encoding="utf-8",
        )
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

    def test_preview_identity_uses_exact_timestamp_format(self) -> None:
        built_at = datetime(2026, 4, 7, 10, 5, 54)
        self.assertEqual(
            preview_identity("9.9.9", built_at),
            "m2c-pipeline-preview-v9.9.9-20260407-100554",
        )

    def test_build_preview_package_uses_timestamped_identity_everywhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            allowlist = self._create_repo(repo_root)
            built_at = datetime(2026, 4, 7, 10, 5, 54)
            expected_identity = "m2c-pipeline-preview-v9.9.9-20260407-100554"

            archive_path, checksum_path, identity = build_preview_package(
                output_dir=repo_root / "dist",
                repo_root=repo_root,
                allowlist=allowlist,
                version="9.9.9",
                built_at=built_at,
            )

            self.assertEqual(identity, expected_identity)
            self.assertEqual(archive_path.name, f"{expected_identity}.zip")
            self.assertEqual(checksum_path.name, f"{expected_identity}.zip.sha256")

            with zipfile.ZipFile(archive_path) as archive:
                members = sorted(archive.namelist())
                root_readme = archive.read(f"{expected_identity}/README.md").decode("utf-8")
                skill_text = archive.read(f"{expected_identity}/SKILL.md").decode("utf-8")

        self.assertTrue(all(member.startswith(f"{expected_identity}/") for member in members))
        self.assertIn(f"{expected_identity}/README.md", members)
        self.assertIn(f"{expected_identity}/SKILL.md", members)
        self.assertIn(f"name: {expected_identity}", skill_text)
        self.assertIn(f"# {expected_identity}", skill_text)
        self.assertNotIn("name: m2c-pipeline\n", skill_text)
        self.assertIn(f"# {expected_identity}", root_readme)
        self.assertIn(f"`{expected_identity}`", root_readme)
        self.assertIn(f"`{expected_identity}.zip`", root_readme)
        self.assertNotIn("m2c-pipeline-generic-v<version>.zip", root_readme)
