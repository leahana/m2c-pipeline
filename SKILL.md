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

- First classify the bootstrap interpreter source instead of blindly trusting the first `python3` on `PATH`.
- prefer a compatible `./venv/bin/python`; if present and compatible, proceed to bootstrap (do not skip it — bootstrap always syncs dependencies even when the venv exists).
- If `./venv/bin/python` is missing or incompatible, look for a compatible system `python3` or `python` and classify it before using it:
  - `pyenv`: preferred user-space host interpreter. If `pyenv which python` resolves to a compatible version, use it as the bootstrap base. If `pyenv` exists but no compatible version is installed, consult [references/install-python.md](references/install-python.md).
  - Active virtualenv or `.venv`: acceptable bootstrap base when compatible, including uv-created environments. Do not switch the runtime contract to `uv run`; still end at repo-local `./venv`.
  - Conda: a named project env is an acceptable temporary bootstrap base, but do not anchor this skill to `conda base`, and do not install the project into shared `base`.
  - Homebrew, Python.org, distro, or another global Python: acceptable fallback when compatible.
- If the interpreter source is ambiguous, resolve it before bootstrap with `python -c 'import sys; print(sys.executable)'`, `echo $VIRTUAL_ENV`, `echo $CONDA_DEFAULT_ENV`, `pyenv which python`, or `uv python find`.
- If no compatible interpreter is available, read [references/install-python.md](references/install-python.md), choose one platform-appropriate path, and ask the user for permission plus network/admin confirmation before running it. Prefer existing user-space managers in this order when available: `pyenv`, `uv`, then OS-level installers such as Homebrew, `apt`, `winget`, or `choco`.
- Once Python is confirmed: POSIX → `./scripts/bootstrap_env.sh`; Windows → `python -m venv venv` then `.\venv\Scripts\python.exe -m pip install -r requirements.txt`. See [references/runtime-commands.md](references/runtime-commands.md) for exact commands.
- After bootstrap, make sure the repo has a local `.env`. If it is missing, copy `.env.example` to `.env` before moving on.

**Phase 2.5 — Credential readiness**

- Default the guidance-flow prompt text to English.
- If the user is clearly a Chinese-speaking user, keep the workflow instructions in English but explicitly instruct the model to reply to the user in Chinese.
- A good pattern is: keep the operational prompt in English, then append `Reply to the user in Chinese.` when needed.
- Before any live Vertex AI run, explicitly remind the user that `.env` should define both `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`.
- If either variable is missing, pause and guide the user instead of guessing values.
- Default prompt wording: "Before running live Vertex mode, confirm `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`. If you already have both values, I can set them for you."
- When the user is Chinese-speaking, instruct the model to deliver that same message in Chinese.
- If the user does not have the values yet, point them to [references/vertex-auth.md](references/vertex-auth.md) and explain the two common paths:
  - Preferred: put `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS` in `.env`
  - Fallback: use system ADC via `gcloud auth application-default login` and `gcloud auth application-default set-quota-project YOUR_PROJECT_ID`
- When guiding the user, mention that they may need the Google Cloud / `gcloud` docs and Vertex AI ADC setup docs, and keep the guidance Vertex-only.

**Phase 3 — Choose mode and run**

- **Offline validation** (no credentials needed): POSIX → `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback`; Windows → `.\venv\Scripts\python.exe -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback`
- **Live generation** (requires Vertex AI credentials): first verify that `.env` has both `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`, or that the user explicitly intends to rely on system ADC. If not, stop and guide the user via [references/vertex-auth.md](references/vertex-auth.md). Then run POSIX → `./venv/bin/python -m m2c_pipeline <input.md> --translation-mode vertex --output-dir ./output`; Windows → `.\venv\Scripts\python.exe -m m2c_pipeline <input.md> --translation-mode vertex --output-dir ./output`.
- **User's own file**: confirm the file contains at least one fenced `mermaid` block before running; if it does not, tell the user rather than proceeding. Then substitute the user's path for `fixtures/minimal-input.md` in the appropriate command above.

**Phase 4 — Report results**

- Dry-run: report the prompt generation flow.
- Live: report the generated PNG paths and embedded metadata.
- Failure: surface any `*_FAILED.txt` artifact and consult [references/failure-recovery.md](references/failure-recovery.md).

## Guardrails

- Always prefer the repo-local `./venv/bin/python`; fall back to a global interpreter only when bootstrapping is impossible.
- The only stable runtime contract is repo-local `./venv/bin/python` or `.\venv\Scripts\python.exe`; managers like `pyenv`, `uv`, `conda`, and Homebrew only provide the bootstrap interpreter.
- Avoid `conda base` as a default bootstrap source. Prefer `pyenv`, uv-managed Python, a named Conda env, or another compatible global interpreter instead.
- Never run multiple system installers speculatively. Choose one platform-appropriate path, confirm permissions and network access, then re-run the repo-local bootstrap.
- Keep authentication Vertex AI only. Prefer `.env` plus `GOOGLE_APPLICATION_CREDENTIALS`; fall back to system ADC. Never add `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or `api_key=` wiring.
- Do not silently continue into live generation when `M2C_PROJECT_ID` or `GOOGLE_APPLICATION_CREDENTIALS` is missing. Remind the user, offer to help set them, and only proceed once the auth path is clear.
- Keep internal workflow prompts in English by default; only localize the final user-facing reply when the user is clearly Chinese-speaking.
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
- [evals/install-python-pyenv.md](evals/install-python-pyenv.md) — verify the agent prefers `pyenv` when it is already available but lacks a compatible version.
- [evals/install-python-uv.md](evals/install-python-uv.md) — verify the agent can use `uv` as a no-admin Python installation path before falling back to OS package managers.
- [evals/avoid-conda-base.md](evals/avoid-conda-base.md) — verify the agent does not anchor the repo runtime to shared `conda base`.
- [evals/install-python-macos.md](evals/install-python-macos.md), [evals/install-python-ubuntu.md](evals/install-python-ubuntu.md), [evals/install-python-windows.md](evals/install-python-windows.md) — verify platform-specific Python installation choices.
