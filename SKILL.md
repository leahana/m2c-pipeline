---
name: m2c-pipeline
description: Converts Mermaid diagrams in Markdown into Chiikawa-style image prompts and Vertex AI image outputs through the m2c_pipeline CLI. Use when users want to dry-run or generate images from Mermaid fenced blocks, especially inside the current m2c-pipeline source workspace. Do not use when the task is general Markdown editing, non-Mermaid diagram work, or any Gemini API-key workflow.
---

# m2c-pipeline

## When to Use

- Use this skill when the task is to validate or generate images from Markdown files that contain fenced `mermaid` blocks.
- Use this skill when the user needs the repo's supported offline path (`--dry-run --translation-mode fallback`) or the live Vertex AI path.
- Do not use this skill for general Markdown cleanup, Mermaid syntax authoring without execution, or any request that depends on Google AI Studio or API-key auth.

## Workflow

1. Confirm the request is about the `m2c_pipeline` CLI or its Mermaid-to-image pipeline.
2. If the current workspace already contains `m2c_pipeline/`, `requirements.txt`, and `SKILL.md`, treat that repo root as the working directory; otherwise locate the repo checkout first.
3. Preflight gate: Do not run any `python -m m2c_pipeline` command until preflight is complete.
4. In preflight, prefer a compatible `./venv/bin/python`.
5. If `./venv/bin/python` is missing or incompatible, look for a compatible system `python3` or `python`.
6. If no compatible Python is available, inspect the host OS and package managers, read [references/install-python.md](references/install-python.md), choose one supported install command, and ask the user for permission plus network/admin confirmation before running it.
7. After Python is available, use the repo-local bootstrap path: on POSIX run `./scripts/bootstrap_env.sh`; on Windows run `python -m venv venv` and `.\venv\Scripts\python.exe -m pip install -r requirements.txt`.
8. Inspect the input Markdown and decide whether the user needs offline validation or live generation.
9. For first-run validation, prefer `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback` on POSIX, or `.\venv\Scripts\python.exe -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback` on Windows.
10. For user-provided input, keep `python -m m2c_pipeline <input>` as the stable runtime contract behind the repo-local virtualenv.
11. For live generation, keep `--translation-mode vertex`, use the requested output directory, and verify Vertex AI credentials before running.
12. After execution, report either the dry-run prompt flow, the generated PNG locations, or any `*_FAILED.txt` recovery artifact that needs follow-up.

## Guardrails

- Always prefer the repo-local `./venv/bin/python`; only fall back to a global interpreter if using or bootstrapping the workspace virtualenv is impossible.
- When the source repo is the current workspace, run setup and CLI commands from the repo root rather than from ad hoc temporary directories.
- Treat `./scripts/bootstrap_env.sh` as the default repo-local setup entry point on POSIX systems; do not extend it into a system installer.
- When Python is missing, prefer the documented platform install commands in [references/install-python.md](references/install-python.md) instead of inventing new package-manager flows.
- Never run multiple system installers speculatively. Choose one platform-appropriate path, confirm permissions/network needs, then rerun the repo-local bootstrap.
- Keep authentication Vertex AI only. Prefer `.env` plus `GOOGLE_APPLICATION_CREDENTIALS`, then fall back to system ADC if the env var is unset.
- Never switch to Google AI Studio or Gemini Developer API, and never add `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or `api_key=` client wiring.
- Keep the public runtime contract stable around `python -m m2c_pipeline`; this skill is about using and validating the existing pipeline, not inventing a new backend.
- Do not commit `.env`, `venv/`, generated images, `*_FAILED.txt` artifacts, or local output directories.

## References

- Read [references/runtime-commands.md](references/runtime-commands.md) for the exact command policy, setup steps, and test commands.
- Read [references/install-python.md](references/install-python.md) when Python is missing and the agent needs to choose a supported install command for macOS, Debian/Ubuntu, or Windows.
- Read [references/vertex-auth.md](references/vertex-auth.md) when the request touches credentials, `.env`, ADC, or Vertex AI environment variables.
- Read [references/failure-recovery.md](references/failure-recovery.md) when a run fails, translation falls back unexpectedly, or image generation writes debug artifacts.
- Read [references/input-output-boundaries.md](references/input-output-boundaries.md) when you need the expected Markdown input shape or the PNG and metadata output contract.
- Use [evals/offline-dry-run.md](evals/offline-dry-run.md), [evals/vertex-live-run.md](evals/vertex-live-run.md), and [evals/paint-failure-recovery.md](evals/paint-failure-recovery.md) as validation tasks for this skill's core paths.
- Use the install-preflight evals in `evals/install-python-macos.md`, `evals/install-python-ubuntu.md`, and `evals/install-python-windows.md` to verify platform-specific Python installation choices.
