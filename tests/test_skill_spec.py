import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.check_skill_spec import validate_skill_spec

PROJECT_ROOT = Path(__file__).resolve().parent.parent


VALID_SKILL = """---
name: m2c-pipeline
description: Converts Mermaid diagrams in Markdown into Chiikawa-style prompts and Vertex AI image outputs. Use when users want to dry-run or generate images from Mermaid fenced blocks with the m2c_pipeline CLI. Do not use when the task is general Markdown editing, non-Mermaid diagram work, or any Gemini API-key workflow.
---

# m2c-pipeline

## When to Use
- Use this skill for Markdown files that contain fenced Mermaid blocks.
- Skip this skill when the task is not about Mermaid-to-image execution.

## Workflow
1. Use the current source workspace when it already contains `m2c_pipeline/`, `requirements.txt`, and `SKILL.md`.
2. Preflight gate: Do not run any `python -m m2c_pipeline` command until preflight is complete.
3. In preflight, prefer a compatible `./venv/bin/python`.
4. If `./venv/bin/python` is missing or incompatible, look for a compatible system `python3` or `python`.
5. If Python is still missing, read [install](references/install-python.md), choose one supported install command, and ask the user for permission plus network/admin confirmation before running it.
6. After Python is available, use `./scripts/bootstrap_env.sh` on POSIX or `python -m venv venv` plus `.\venv\Scripts\python.exe -m pip install -r requirements.txt` on Windows.
7. Prefer `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback` for first-run validation.
8. For user-provided input, keep `python -m m2c_pipeline <input>` as the stable runtime contract behind the repo-local virtualenv.
9. For live runs, keep Vertex AI enabled and capture PNG outputs or `*_FAILED.txt` artifacts.

## Guardrails
- Always prefer `./venv/bin/python` when the workspace virtualenv exists.
- Run setup and CLI commands from the repo root when the current workspace is the source repo.
- Treat `./scripts/bootstrap_env.sh` as the default repo-local POSIX setup entry point instead of reconstructing setup commands by hand.
- Prefer the documented install commands in [install](references/install-python.md) instead of inventing new package-manager flows.
- Use `.env` plus `GOOGLE_APPLICATION_CREDENTIALS` first, then fall back to system ADC.
- Do not use `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or any non-Vertex backend.

## References
- Runtime defaults: [runtime](references/runtime-commands.md)
- Python install matrix: [install](references/install-python.md)
- Auth details: [auth](references/vertex-auth.md)
- Failure handling: [recovery](references/failure-recovery.md)
- I/O boundaries: [io](references/input-output-boundaries.md)
"""


class SkillSpecTests(unittest.TestCase):
    def _write_contract(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "expected_name": "m2c-pipeline",
                    "required_title": "# m2c-pipeline",
                    "required_frontmatter_fields": ["name", "description"],
                    "required_sections": ["When to Use", "Workflow", "Guardrails", "References"],
                    "max_non_empty_lines": 220,
                    "description_required_keywords": ["Mermaid", "Markdown", "Vertex AI"],
                    "description_required_phrases": ["Use when", "Do not use when"],
                    "description_disallowed_fragments": ["general-purpose", "general tasks"],
                    "banned_tokens": ["openai.yaml", "openai.yml", "codex"],
                }
            ),
            encoding="utf-8",
        )

    def _write_allowlist(self, path: Path) -> None:
        path.write_text(
            "SKILL.md\nSKILL_README.md\nLICENSE\n.env.example\nrequirements.txt\nscripts/bootstrap_env.sh\nfixtures/**\nreferences/**\nevals/**\nm2c_pipeline/**\n",
            encoding="utf-8",
        )

    def _write_valid_repo(self, root: Path) -> tuple[Path, Path]:
        (root / "fixtures").mkdir()
        (root / "references").mkdir()
        (root / "evals").mkdir()
        (root / "scripts").mkdir()
        (root / "fixtures" / "minimal-input.md").write_text("```mermaid\nflowchart LR\nA-->B\n```\n", encoding="utf-8")
        (root / "references" / "runtime-commands.md").write_text("runtime\n", encoding="utf-8")
        (root / "references" / "install-python.md").write_text("install\n", encoding="utf-8")
        (root / "references" / "vertex-auth.md").write_text("auth\n", encoding="utf-8")
        (root / "references" / "failure-recovery.md").write_text("recovery\n", encoding="utf-8")
        (root / "references" / "input-output-boundaries.md").write_text("io\n", encoding="utf-8")
        (root / "evals" / "offline-dry-run.md").write_text("eval\n", encoding="utf-8")
        (root / "scripts" / "bootstrap_env.sh").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
        (root / "SKILL.md").write_text(VALID_SKILL, encoding="utf-8")

        contract_path = root / "skill-contract.json"
        allowlist_path = root / "package-allowlist.txt"
        self._write_contract(contract_path)
        self._write_allowlist(allowlist_path)
        return contract_path, allowlist_path

    def test_validate_skill_spec_accepts_valid_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract_path, allowlist_path = self._write_valid_repo(repo_root)

            validate_skill_spec(
                repo_root=repo_root,
                contract_path=contract_path,
                allowlist_path=allowlist_path,
            )

    def test_validate_skill_spec_rejects_missing_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract_path, allowlist_path = self._write_valid_repo(repo_root)
            (repo_root / "SKILL.md").write_text("# m2c-pipeline\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "YAML frontmatter"):
                validate_skill_spec(
                    repo_root=repo_root,
                    contract_path=contract_path,
                    allowlist_path=allowlist_path,
                )

    def test_validate_skill_spec_rejects_missing_description_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract_path, allowlist_path = self._write_valid_repo(repo_root)
            (repo_root / "SKILL.md").write_text(
                VALID_SKILL.replace(
                    "description: Converts Mermaid diagrams in Markdown into Chiikawa-style prompts and Vertex AI image outputs. Use when users want to dry-run or generate images from Mermaid fenced blocks with the m2c_pipeline CLI. Do not use when the task is general Markdown editing, non-Mermaid diagram work, or any Gemini API-key workflow.\n",
                    "",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "missing required fields: description"):
                validate_skill_spec(
                    repo_root=repo_root,
                    contract_path=contract_path,
                    allowlist_path=allowlist_path,
                )

    def test_validate_skill_spec_rejects_generic_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract_path, allowlist_path = self._write_valid_repo(repo_root)
            (repo_root / "SKILL.md").write_text(
                VALID_SKILL.replace(
                    "description: Converts Mermaid diagrams in Markdown into Chiikawa-style prompts and Vertex AI image outputs. Use when users want to dry-run or generate images from Mermaid fenced blocks with the m2c_pipeline CLI. Do not use when the task is general Markdown editing, non-Mermaid diagram work, or any Gemini API-key workflow.",
                    "description: Helpful for general tasks. Use when users need help. Do not use when unavailable.",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must mention 'Mermaid'"):
                validate_skill_spec(
                    repo_root=repo_root,
                    contract_path=contract_path,
                    allowlist_path=allowlist_path,
                )

    def test_validate_skill_spec_rejects_disallowed_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract_path, allowlist_path = self._write_valid_repo(repo_root)
            (repo_root / "SKILL.md").write_text(
                VALID_SKILL + "- Escape hatch: [bad](../README.md)\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "disallowed local link"):
                validate_skill_spec(
                    repo_root=repo_root,
                    contract_path=contract_path,
                    allowlist_path=allowlist_path,
                )

    def test_validate_skill_spec_rejects_overlong_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract_path, allowlist_path = self._write_valid_repo(repo_root)
            extra_lines = "\n".join(f"- line {index}" for index in range(240))
            (repo_root / "SKILL.md").write_text(f"{VALID_SKILL}\n{extra_lines}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "non-empty line limit"):
                validate_skill_spec(
                    repo_root=repo_root,
                    contract_path=contract_path,
                    allowlist_path=allowlist_path,
                )

    def test_repository_skill_requires_preflight_gate(self) -> None:
        text = (PROJECT_ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("Preflight gate:", text)
        self.assertIn(
            "Do not run any `python -m m2c_pipeline` command until preflight is complete.",
            text,
        )
        self.assertIn("[references/install-python.md](references/install-python.md)", text)
        self.assertIn("ask the user for permission plus network/admin confirmation", text)

        venv_step = text.index("prefer a compatible `./venv/bin/python`")
        system_step = text.index("look for a compatible system `python3` or `python`")
        install_step = text.index("[references/install-python.md](references/install-python.md)")
        self.assertLess(venv_step, system_step)
        self.assertLess(system_step, install_step)
