import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.check_skill_spec import validate_skill_spec


VALID_SKILL = """---
name: m2c-pipeline
description: Converts Mermaid diagrams in Markdown into Chiikawa-style prompts and Vertex AI image outputs. Use when users want to dry-run or generate images from Mermaid fenced blocks with the m2c_pipeline CLI. Do not use when the task is general Markdown editing, non-Mermaid diagram work, or any Gemini API-key workflow.
---

# m2c-pipeline

## When to Use
- Use this skill for Markdown files that contain fenced Mermaid blocks.
- Skip this skill when the task is not about Mermaid-to-image execution.

## Workflow
1. Inspect the Markdown input and decide whether the request is a dry run or a live generation.
2. Prefer `./venv/bin/python -m m2c_pipeline` and choose `--translation-mode fallback --dry-run` for offline validation.
3. For live runs, keep Vertex AI enabled and capture PNG outputs or `*_FAILED.txt` artifacts.

## Guardrails
- Always prefer `./venv/bin/python` when the workspace virtualenv exists.
- Use `.env` plus `GOOGLE_APPLICATION_CREDENTIALS` first, then fall back to system ADC.
- Do not use `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or any non-Vertex backend.

## References
- Runtime defaults: [runtime](references/runtime-commands.md)
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
            "SKILL.md\nreferences/**\nevals/**\nREADME.md\nLICENSE\n.env.example\nrequirements.txt\nm2c_pipeline/**\n",
            encoding="utf-8",
        )

    def _write_valid_repo(self, root: Path) -> tuple[Path, Path]:
        (root / "references").mkdir()
        (root / "evals").mkdir()
        (root / "references" / "runtime-commands.md").write_text("runtime\n", encoding="utf-8")
        (root / "references" / "vertex-auth.md").write_text("auth\n", encoding="utf-8")
        (root / "references" / "failure-recovery.md").write_text("recovery\n", encoding="utf-8")
        (root / "references" / "input-output-boundaries.md").write_text("io\n", encoding="utf-8")
        (root / "evals" / "offline-dry-run.md").write_text("eval\n", encoding="utf-8")
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
