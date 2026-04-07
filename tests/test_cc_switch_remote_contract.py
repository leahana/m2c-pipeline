import tempfile
import unittest
from pathlib import Path

from scripts.ci.check_cc_switch_remote_contract import (
    RemoteContractError,
    discover_skill_root,
    validate_cc_switch_remote_contract,
    validate_published_skill_tree,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
README_PATH = PROJECT_ROOT / "README.md"
SKILL_README_PATH = PROJECT_ROOT / "SKILL_README.md"
CONTRACT_DOC_PATH = PROJECT_ROOT / "references" / "cc-switch-remote-contract.md"
EVAL_PATH = PROJECT_ROOT / "evals" / "cc-switch-remote-reinstall.md"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_repo(root: Path) -> None:
    _write(
        root / "policy" / "package-allowlist.txt",
        "\n".join(
            [
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
        )
        + "\n",
    )
    _write(
        root / "SKILL.md",
        "---\n"
        "name: m2c-pipeline\n"
        "description: Converts Mermaid diagrams in Markdown into Vertex AI image outputs. "
        "Use when users need remote skill execution. Do not use when the task is general Markdown editing.\n"
        "---\n\n"
        "# m2c-pipeline\n\n"
        "## Workflow\n\n"
        "- Runtime: [runtime](references/runtime-commands.md)\n",
    )
    _write(
        root / "SKILL_README.md",
        "# m2c-pipeline\n\n"
        "Install via `owner/repo + branch=skill`.\n\n"
        "已知限制：CC Switch 3.12.3 在 2026-04-06 观察到删除后重装可能失败。\n\n"
        "回退入口：[contract](references/cc-switch-remote-contract.md)\n",
    )
    _write(root / "LICENSE", "license\n")
    _write(root / ".env.example", "M2C_PROJECT_ID=demo\n")
    _write(root / "requirements.txt", "Pillow>=10.0.0\n")
    _write(root / "scripts" / "bootstrap_env.sh", "#!/usr/bin/env sh\n")
    _write(root / "fixtures" / "minimal-input.md", "```mermaid\nflowchart LR\nA-->B\n```\n")
    _write(root / "references" / "runtime-commands.md", "# Runtime\n")
    _write(root / "references" / "cc-switch-remote-contract.md", "# Contract\n")
    _write(root / "evals" / "cc-switch-remote-reinstall.md", "# Eval\n")
    _write(root / "m2c_pipeline" / "__init__.py", "")
    _write(root / "m2c_pipeline" / "version.py", '__version__ = "9.9.9"\n')


class CcSwitchRemoteContractTests(unittest.TestCase):
    def test_validate_contract_accepts_valid_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            _create_repo(repo_root)

            validate_cc_switch_remote_contract(repo_root=repo_root)

    def test_discover_skill_root_accepts_arbitrary_top_level_dir_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)
            _write(extract_dir / "not-the-repo-name" / "SKILL.md", "skill\n")

            discovered = discover_skill_root(extract_dir)

            self.assertEqual(discovered.relative_to(extract_dir).as_posix(), "not-the-repo-name")

    def test_discover_skill_root_rejects_missing_skill_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)
            (extract_dir / "bundle").mkdir()

            with self.assertRaisesRegex(RemoteContractError, "missing SKILL.md"):
                discover_skill_root(extract_dir)

    def test_discover_skill_root_rejects_multiple_skill_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)
            _write(extract_dir / "bundle-a" / "SKILL.md", "skill\n")
            _write(extract_dir / "bundle-b" / "SKILL.md", "skill\n")

            with self.assertRaisesRegex(RemoteContractError, "multiple skill roots"):
                discover_skill_root(extract_dir)

    def test_discover_skill_root_rejects_single_nested_subpath(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)
            _write(extract_dir / "bundle" / "nested-skill" / "SKILL.md", "skill\n")

            with self.assertRaisesRegex(RemoteContractError, "subpath not supported"):
                discover_skill_root(extract_dir)

    def test_validate_published_skill_tree_rejects_broken_relative_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stage_dir = Path(tmpdir)
            _write(stage_dir / "README.md", "[broken](missing.md)\n")
            _write(stage_dir / "SKILL.md", "skill\n")

            with self.assertRaisesRegex(RemoteContractError, "link target does not exist"):
                validate_published_skill_tree(stage_dir)

    def test_repository_docs_capture_known_limitations_and_fallbacks(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        skill_readme = SKILL_README_PATH.read_text(encoding="utf-8")

        for text in (readme, skill_readme):
            self.assertIn("已知限制", text)
            self.assertIn("CC Switch 3.12.3", text)
            self.assertIn("2026-04-06", text)
            self.assertIn("GitHub Release 压缩包", text)
            self.assertIn("`skill` 分支", text)
            self.assertIn("references/cc-switch-remote-contract.md", text)

    def test_repository_contract_doc_and_eval_exist(self) -> None:
        contract_text = CONTRACT_DOC_PATH.read_text(encoding="utf-8")
        eval_text = EVAL_PATH.read_text(encoding="utf-8")

        self.assertIn("owner/repo + branch=skill", contract_text)
        self.assertIn("不支持 `subpath`", contract_text)
        self.assertIn("删除后重装", contract_text)
        self.assertIn("discover_skill_root", contract_text)
        self.assertIn("首次安装", eval_text)
        self.assertIn("升级安装", eval_text)
        self.assertIn("删除后重装", eval_text)
        self.assertIn("GitHub Release 压缩包", eval_text)

