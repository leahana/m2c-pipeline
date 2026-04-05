---
name: m2c-pipeline
description: Converts Mermaid diagrams in Markdown into Chiikawa-style illustrated PNG images via the Vertex AI backend. Use when the user wants to generate or dry-run images from Mermaid fenced blocks in a Markdown file. Do not use when the task is general Markdown editing, authoring Mermaid syntax without execution, or any Gemini API-key workflow.
---

# m2c-pipeline

## When to Use

- Use this skill when the task is to generate or validate images from a Markdown file that contains fenced `mermaid` blocks.
- Use this skill for offline validation (`--dry-run --translation-mode fallback`) or live Vertex AI image generation.
- The pipeline produces Chiikawa-style illustrations: round characters with large eyes assigned to diagram nodes, explaining technical concepts in a cute manga style.
- Do not use this skill for general Markdown cleanup, authoring Mermaid syntax without running the pipeline, or any request that depends on Google AI Studio or API-key auth.

## Workflow

**Phase 1 — Locate workspace**

If the current directory contains `m2c_pipeline/`, `requirements.txt`, and `SKILL.md`, use it as the repo root. Otherwise locate the checkout first.

**Phase 2 — Preflight & bootstrap**

Preflight gate: Do not run any `python -m m2c_pipeline` command until preflight is complete.

- prefer a compatible `./venv/bin/python`; if present and compatible, proceed to bootstrap (do not skip it — bootstrap always syncs dependencies even when the venv exists).
- If `./venv/bin/python` is missing or incompatible, look for a compatible system `python3` or `python`.
- If neither is available, read [references/install-python.md](references/install-python.md), choose one platform-appropriate path, and ask the user for permission plus network/admin confirmation before running it.
- Once Python is confirmed: POSIX → `./scripts/bootstrap_env.sh`; Windows → `python -m venv venv` then `.\venv\Scripts\python.exe -m pip install -r requirements.txt`. See [references/runtime-commands.md](references/runtime-commands.md) for exact commands.

**Phase 3 — Choose mode and run**

- **Offline validation** (no credentials needed): POSIX → `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback`; Windows → `.\venv\Scripts\python.exe -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback`
- **Live generation** (requires Vertex AI credentials): POSIX → `./venv/bin/python -m m2c_pipeline <input.md> --translation-mode vertex --output-dir ./output`; Windows → `.\venv\Scripts\python.exe -m m2c_pipeline <input.md> --translation-mode vertex --output-dir ./output`. Verify credentials first — see [references/vertex-auth.md](references/vertex-auth.md).
- **User's own file**: confirm the file contains at least one fenced `mermaid` block before running; if it does not, tell the user rather than proceeding. Then substitute the user's path for `fixtures/minimal-input.md` in the appropriate command above.

**Phase 4 — Report results**

- Dry-run: report the prompt generation flow.
- Live: report the generated PNG paths and embedded metadata.
- Failure: surface any `*_FAILED.txt` artifact and consult [references/failure-recovery.md](references/failure-recovery.md).

## Guardrails

- Always prefer the repo-local `./venv/bin/python`; fall back to a global interpreter only when bootstrapping is impossible.
- Never run multiple system installers speculatively. Choose one platform-appropriate path, confirm permissions and network access, then re-run the repo-local bootstrap.
- Keep authentication Vertex AI only. Prefer `.env` plus `GOOGLE_APPLICATION_CREDENTIALS`; fall back to system ADC. Never add `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or `api_key=` wiring.
- Keep the runtime contract stable around `python -m m2c_pipeline`; this skill runs the existing pipeline, it does not invent new backends.
- Do not commit `.env`, `venv/`, generated images, `*_FAILED.txt` artifacts, or local output directories.

## References

### Setup References

- [references/runtime-commands.md](references/runtime-commands.md) — exact bootstrap and CLI commands for POSIX and Windows.
- [references/install-python.md](references/install-python.md) — platform-specific Python install when no compatible interpreter is found.
- [references/vertex-auth.md](references/vertex-auth.md) — credential configuration (`.env`, ADC) and Vertex AI auth troubleshooting.
- [references/failure-recovery.md](references/failure-recovery.md) — handling run failures and `*_FAILED.txt` recovery artifacts.
- [references/input-output-boundaries.md](references/input-output-boundaries.md) — input format requirements, output file naming, and PNG metadata fields.

### Validation Evals

- [evals/offline-dry-run.md](evals/offline-dry-run.md) — verify the offline path works without cloud credentials.
- [evals/vertex-live-run.md](evals/vertex-live-run.md) — verify live image generation with Vertex AI.
- [evals/paint-failure-recovery.md](evals/paint-failure-recovery.md) — verify `*_FAILED.txt` handling when image generation fails.
- [evals/user-provided-input.md](evals/user-provided-input.md) — verify the agent correctly handles a user-provided Markdown file.
- [evals/reuse-existing-venv.md](evals/reuse-existing-venv.md) — verify the agent reuses a healthy venv without recreating it, while still running repo-local bootstrap.
- [evals/install-python-macos.md](evals/install-python-macos.md), [evals/install-python-ubuntu.md](evals/install-python-ubuntu.md), [evals/install-python-windows.md](evals/install-python-windows.md) — verify platform-specific Python installation choices.
