---
name: m2c-pipeline
description: Converts Mermaid diagrams in Markdown into Chiikawa-style image prompts and Vertex AI image outputs through the m2c_pipeline CLI. Use when users want to dry-run or generate images from Mermaid fenced blocks. Do not use when the task is general Markdown editing, non-Mermaid diagram work, or any Gemini API-key workflow.
---

# m2c-pipeline

## When to Use

- Use this skill when the task is to validate or generate images from Markdown files that contain fenced `mermaid` blocks.
- Use this skill when the user needs the repo's supported offline path (`--dry-run --translation-mode fallback`) or the live Vertex AI path.
- Do not use this skill for general Markdown cleanup, Mermaid syntax authoring without execution, or any request that depends on Google AI Studio or API-key auth.

## Workflow

1. Confirm the request is about the `m2c_pipeline` CLI or its Mermaid-to-image pipeline.
2. Inspect the input Markdown and decide whether the user needs offline validation or live generation.
3. For offline validation, prefer `./venv/bin/python -m m2c_pipeline <input> --dry-run --translation-mode fallback`.
4. For live generation, keep `--translation-mode vertex`, use the requested output directory, and verify Vertex AI credentials before running.
5. After execution, report either the dry-run prompt flow, the generated PNG locations, or any `*_FAILED.txt` recovery artifact that needs follow-up.

## Guardrails

- Always prefer `./venv/bin/python` in this repository; only fall back to a global interpreter if the local virtualenv is missing or broken.
- Keep authentication Vertex AI only. Prefer `.env` plus `GOOGLE_APPLICATION_CREDENTIALS`, then fall back to system ADC if the env var is unset.
- Never switch to Google AI Studio or Gemini Developer API, and never add `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or `api_key=` client wiring.
- Keep the public runtime contract stable around `python -m m2c_pipeline`; this skill is about using and validating the existing pipeline, not inventing a new backend.
- Do not commit `.env`, generated images, `*_FAILED.txt` artifacts, or local output directories.

## References

- Read [references/runtime-commands.md](references/runtime-commands.md) for the exact command policy, setup steps, and test commands.
- Read [references/vertex-auth.md](references/vertex-auth.md) when the request touches credentials, `.env`, ADC, or Vertex AI environment variables.
- Read [references/failure-recovery.md](references/failure-recovery.md) when a run fails, translation falls back unexpectedly, or image generation writes debug artifacts.
- Read [references/input-output-boundaries.md](references/input-output-boundaries.md) when you need the expected Markdown input shape or the PNG and metadata output contract.
- Use [evals/offline-dry-run.md](evals/offline-dry-run.md), [evals/vertex-live-run.md](evals/vertex-live-run.md), and [evals/paint-failure-recovery.md](evals/paint-failure-recovery.md) as validation tasks for this skill's core paths.
