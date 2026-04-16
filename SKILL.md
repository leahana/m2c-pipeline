---
name: m2c-pipeline
description: Converts Mermaid diagrams in Markdown into Chiikawa-style illustrated images (WebP by default, PNG via --output-format=png) via the Vertex AI backend. Use when the user wants to generate or dry-run images from Mermaid fenced blocks in a Markdown file. Do not use when the task is general Markdown editing, authoring Mermaid syntax without execution, or any Gemini API-key workflow.
---

# m2c-pipeline

## When to Use

- Use this skill when the task is to generate or validate images from a Markdown file that contains fenced `mermaid` blocks.
- Use this skill for offline validation (`--dry-run --translation-mode fallback`) or live Vertex AI image generation.
- The pipeline produces Chiikawa-style illustrations: round characters with large eyes assigned to diagram nodes, explaining technical concepts in a cute manga style.
- Do not use this skill for general Markdown cleanup, authoring Mermaid syntax without running the pipeline, or any request that depends on Google AI Studio or API-key auth.

## Workflow

**Phase 1 — Locate workspace**

The skill's own base directory — the directory containing this SKILL.md — is always the workspace root. Do NOT search for or fall back to any external checkout. All relative paths (`./venv`, `./output`, `./.env`) resolve against this directory.

**Phase 2 — Preflight & bootstrap**

Preflight gate: Do not run any `python -m m2c_pipeline` command until preflight is complete.

**Step 1 — Check skill's own venv (silent, no consent needed)**

Check `./venv/bin/python` (POSIX) or `.\venv\Scripts\python.exe` (Windows) and verify it is Python 3.11+. The path is relative to the directory containing this SKILL.md — never an external project directory. If the venv is healthy, proceed directly to bootstrap — no external scanning of the user's system needed.

**Step 2 — Read passive signals (silent, no consent needed)**

If the repo-local venv is missing or incompatible, read these shell environment variables before asking the user anything. They are already in the current process and require no additional file system access:

- `$PYENV_ROOT` — indicates pyenv is installed
- `$UV_HOME` — indicates uv is installed
- `$VIRTUAL_ENV` — indicates an active virtualenv
- `$CONDA_DEFAULT_ENV` — indicates an active conda environment

**Step 3 — Personalized prompt (requires user response)**

Based on the passive signals, present one of the following tailored prompts. Always lead with a single recommended default. Never start external scanning before the user responds.

- **Signal: `$PYENV_ROOT` is set** — "You appear to be using pyenv. Recommended: use pyenv as the Python source for this project's bootstrap (I'll need to run `pyenv which python` — this only looks inside pyenv). Or: provide a Python path directly."
- **Signal: `$UV_HOME` is set** — "You appear to have uv installed. Recommended: use uv to provide Python (I'll need to run `uv python find 3.12` — this only queries uv-managed versions). Or: provide a Python path directly."
- **Signal: `$CONDA_DEFAULT_ENV` is set (not `base`)** — "You appear to be in conda environment `$CONDA_DEFAULT_ENV`. Recommended: use it as the bootstrap source — the venv will be created inside the skill's own directory (`./venv`), not inside conda. Or: provide a Python path directly."
- **Signal: `$VIRTUAL_ENV` is set** — "You have an active virtualenv at `$VIRTUAL_ENV`. Recommended: use it as the bootstrap source to create `./venv`. Or: provide a Python path directly."
- **Signal: none of the above** — "I need Python 3.11+ to set up the project virtualenv, but I don't see a Python environment manager configured in your shell. Recommended: install uv (no admin rights needed, fast, modern). Or: tell me the path to a Python 3.11+ interpreter you already have. Or: if you use pyenv, conda, or Homebrew, I can help check after you authorize a scan."

**Step 4 — Active scan or direct path (only after user responds)**

- If the user authorizes a scan: describe the exact command and scope before running it. Report findings before acting. Example: "Found Python 3.12.7 managed by pyenv at `/Users/…/.pyenv/versions/3.12.7/bin/python` — use this as the bootstrap source?" Wait for confirmation before proceeding.
- If the user provides a path directly: validate it with `python --version` and use it as the bootstrap source — no other scanning.
- If the user needs Python installed: read [references/install-python.md](references/install-python.md), present one platform-appropriate option, and ask for permission plus network/admin confirmation before running any installer.

**Step 5 — Bootstrap**

Once a Python source is confirmed: POSIX → `./scripts/bootstrap_env.sh`; Windows → `python -m venv venv` then `.\venv\Scripts\python.exe -m pip install -r requirements.txt`. See [references/runtime-commands.md](references/runtime-commands.md) for exact commands.

After bootstrap, make sure the repo has a local `.env`. If it is missing, copy `.env.example` to `.env` before moving on.

**Phase 2.5 — Credential readiness**

Default the guidance-flow prompt text to English. If the user is clearly Chinese-speaking, keep the workflow instructions in English but instruct the model to reply to the user in Chinese.

**Step 1 — Check repo root only (silent, no consent needed)**

Read `.env` in the repo root and check for `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`. If both are present, proceed silently to the live-run gate — no external scanning needed.

If `.env` is missing, copy `.env.example` to `.env` first, then re-check.

**Step 2 — Personalized credential prompt (requires user response)**

If either variable is missing, stop and present a tailored prompt based on what is missing. Always lead with the direct-input path as the recommended default:

- **Only `M2C_PROJECT_ID` missing** — "I need your GCP project ID. Recommended: tell me the value and I'll write it to `.env`. Or: let me check your gcloud config (I'll run `gcloud config get-value project` — requires your authorization)."
- **Only `GOOGLE_APPLICATION_CREDENTIALS` missing** — "I need the path to an ADC or service account JSON credential file. Recommended: tell me the absolute path and I'll write it to `.env`. Or: let me check if gcloud ADC is already configured (I'll need to access `~/.config/gcloud/application_default_credentials.json` — requires your authorization). Or: I can guide you through `gcloud auth application-default login`."
- **Both missing** — "Before running live Vertex mode, I need two values: `M2C_PROJECT_ID` (your GCP project ID) and `GOOGLE_APPLICATION_CREDENTIALS` (absolute path to a credential JSON). Recommended: tell me both values and I'll write them to `.env`. Or: let me check your existing gcloud configuration (requires your authorization). Or: I can guide you through setup from scratch via [references/vertex-auth.md](references/vertex-auth.md)."

**Step 3 — Active gcloud scan (only after user authorizes)**

If the user authorizes a gcloud check, state what will be accessed before running anything:
> "I will run `gcloud config get-value project` and check whether `~/.config/gcloud/application_default_credentials.json` exists."

Report findings, then ask the user to confirm before writing anything to `.env`.

**Step 4 — Live-run gate**

Only proceed to live generation when one of these is true:
1. `.env` contains both `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS` (user-provided or user-confirmed values)
2. The user explicitly chose system ADC and confirmed they have completed `gcloud auth application-default login`

If neither is true, pause and guide the user via [references/vertex-auth.md](references/vertex-auth.md).

**Phase 3 — Choose mode and run**

- **Offline validation** (no credentials needed): POSIX → `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback`; Windows → `.\venv\Scripts\python.exe -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback`
- **Live generation** (requires Vertex AI credentials): first verify that `.env` has both `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`, or that the user explicitly intends to rely on system ADC. If not, stop and guide the user via [references/vertex-auth.md](references/vertex-auth.md). Then run POSIX → `./venv/bin/python -m m2c_pipeline <input.md> --translation-mode vertex --output-dir ./output`; Windows → `.\venv\Scripts\python.exe -m m2c_pipeline <input.md> --translation-mode vertex --output-dir ./output`.
- **User's own file**: confirm the file contains at least one fenced `mermaid` block before running; if it does not, tell the user rather than proceeding. Then substitute the user's path for `fixtures/minimal-input.md` in the appropriate command above.

**Phase 4 — Report results**

- Dry-run: report the prompt generation flow.
- Live: report the generated image paths (WebP by default; each has a `.metadata.json` sidecar) and note any `*_FAILED.txt` artifacts. For PNG output (`--output-format=png`), metadata is embedded directly in the PNG.
- Failure: surface any `*_FAILED.txt` artifact and consult [references/failure-recovery.md](references/failure-recovery.md).

## Guardrails

- The skill's own base directory is always the workspace root. Never use an external project directory or any other checkout as the workspace root, even if it contains `m2c_pipeline/`, `requirements.txt`, and `SKILL.md`. Isolation requires the venv to live inside the skill's own directory.
- Always prefer the repo-local `./venv/bin/python` (resolved relative to the skill's base directory); fall back to a global interpreter only when bootstrapping is impossible.
- The only stable runtime contract is repo-local `./venv/bin/python` or `.\venv\Scripts\python.exe`; managers like `pyenv`, `uv`, `conda`, and Homebrew only provide the bootstrap interpreter.
- Avoid `conda base` as a default bootstrap source. Prefer `pyenv`, uv-managed Python, a named Conda env, or another compatible global interpreter instead.
- Never run multiple system installers speculatively. Choose one platform-appropriate path, confirm permissions and network access, then re-run the repo-local bootstrap.
- Keep authentication Vertex AI only. Prefer `.env` plus `GOOGLE_APPLICATION_CREDENTIALS`; fall back to system ADC. Never add `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or `api_key=` wiring.
- Do not silently continue into live generation when `M2C_PROJECT_ID` or `GOOGLE_APPLICATION_CREDENTIALS` is missing. Remind the user, offer to help set them, and only proceed once the auth path is clear.
- Keep internal workflow prompts in English by default; only localize the final user-facing reply when the user is clearly Chinese-speaking.
- Keep the runtime contract stable around `python -m m2c_pipeline`; this skill runs the existing pipeline, it does not invent new backends.
- Do not commit `.env`, `venv/`, generated images, `*_FAILED.txt` artifacts, or local output directories.
- Do not run any external environment detection command (`pyenv which python`, `uv python find`, `command -v brew`, `command -v python3`, etc.) until the user has explicitly authorized it in the current session. Reading shell environment variables (`$PYENV_ROOT`, `$VIRTUAL_ENV`, `$UV_HOME`, `$CONDA_DEFAULT_ENV`) is always permitted without consent.
- Do not probe `~/.config/gcloud/`, run `gcloud` commands, or check whether a credential file exists outside the repo root without explicit user authorization.
- When scanning is authorized, always describe the exact command and access scope before running it, report all findings, and wait for confirmation before acting.
- Prefer user-provided values (Python path, project ID, credential path) over auto-discovered values whenever the user offers them directly.

## References

### Setup References

- [references/runtime-commands.md](references/runtime-commands.md) — exact bootstrap and CLI commands for POSIX and Windows.
- [references/install-python.md](references/install-python.md) — platform-specific Python install when no compatible interpreter is found.
- [references/vertex-auth.md](references/vertex-auth.md) — credential configuration (`.env`, ADC) and Vertex AI auth troubleshooting.
- [references/failure-recovery.md](references/failure-recovery.md) — handling run failures and `*_FAILED.txt` recovery artifacts.
- [references/input-output-boundaries.md](references/input-output-boundaries.md) — input format requirements, output file naming, sidecar metadata (WebP) and embedded metadata (PNG), and run artifact layout.

### Validation Evals

- [evals/offline-dry-run.md](evals/offline-dry-run.md) — verify the offline path works without cloud credentials.
- [evals/vertex-live-run.md](evals/vertex-live-run.md) — verify live image generation with Vertex AI.
- [evals/paint-failure-recovery.md](evals/paint-failure-recovery.md) — verify `*_FAILED.txt` handling when image generation fails.
- [evals/user-provided-input.md](evals/user-provided-input.md) — verify the agent correctly handles a user-provided Markdown file.
- [evals/reuse-existing-venv.md](evals/reuse-existing-venv.md) — verify the agent reuses a healthy venv without recreating it, while still running repo-local bootstrap.
- [evals/consent-scan-python.md](evals/consent-scan-python.md) — verify authorized Python scans report findings and wait for confirmation before bootstrap.
- [evals/env-signal-pyenv.md](evals/env-signal-pyenv.md), [evals/env-signal-uv.md](evals/env-signal-uv.md), [evals/env-signal-conda.md](evals/env-signal-conda.md), [evals/env-signal-none.md](evals/env-signal-none.md) — verify passive-signal-driven prompt selection and no-signal fallback behavior.
- [evals/user-provides-python-path.md](evals/user-provides-python-path.md) — verify a user-provided interpreter path is preferred over auto-discovery.
- [evals/user-provides-credentials.md](evals/user-provides-credentials.md) — verify user-provided Vertex credentials are written to `.env` without `gcloud` scanning.
- [evals/install-python-pyenv.md](evals/install-python-pyenv.md) — verify the agent prefers `pyenv` when it is already available but lacks a compatible version.
- [evals/install-python-uv.md](evals/install-python-uv.md) — verify the agent can use `uv` as a no-admin Python installation path before falling back to OS package managers.
- [evals/avoid-conda-base.md](evals/avoid-conda-base.md) — verify the agent does not anchor the repo runtime to shared `conda base`.
- [evals/install-python-macos.md](evals/install-python-macos.md), [evals/install-python-ubuntu.md](evals/install-python-ubuntu.md), [evals/install-python-windows.md](evals/install-python-windows.md) — verify platform-specific Python installation choices.
