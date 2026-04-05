# AGENTS.md

This file provides guidance to coding agents working in this project directory.

## What This Project Does

This repository contains one public pipeline: `m2c_pipeline`.

It extracts Mermaid diagram blocks from Markdown, translates them into Chiikawa-style image prompts with Gemini, generates images through the `google-genai` SDK on the Vertex AI backend, and saves PNG files with embedded metadata.

The public interface is CLI-first:

```bash
python -m m2c_pipeline input.md
```

## Commands

Python command policy for this repository:

- Always prefer the current workspace virtualenv interpreter: `./venv/bin/python`
- If a command needs pip, prefer `./venv/bin/python -m pip`
- Do not use global `python3` when `./venv/bin/python` exists
- Only fall back to a global Python interpreter when the local virtualenv is missing or broken

### Setup

```bash
python -m venv venv
./venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

### Auth

Preferred auth order for this project:

1. Prefer `.env` plus `GOOGLE_APPLICATION_CREDENTIALS`
2. Fallback to system ADC when `GOOGLE_APPLICATION_CREDENTIALS` is not set

This project must use Vertex AI API only.
Do not switch to Google AI Studio / Gemini Developer API.
Do not use `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or `genai.Client(api_key=...)`.

```bash
cp .env.example .env

# Preferred:
# edit .env and set:
#   M2C_PROJECT_ID=YOUR_PROJECT_ID
#   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/adc-or-service-account.json

# Fallback: initialize system ADC instead
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

### Run

```bash
./venv/bin/python -m m2c_pipeline tests/fixtures/test_input.md --dry-run --translation-mode fallback
./venv/bin/python -m m2c_pipeline tests/fixtures/test_input.md --translation-mode vertex --output-dir ./output
```

### Tests

```bash
./venv/bin/python -m unittest \
  tests.test_m2c_config \
  tests.test_m2c_cli \
  tests.test_m2c_extractor \
  tests.test_m2c_pipeline \
  tests.test_m2c_storage \
  tests.test_m2c_translator

./venv/bin/python tests/smoke_test.py --input tests/fixtures/test_input.md
```

## Architecture

The pipeline has four fixed stages:

1. `extractor.py`: find Mermaid fenced blocks and return `MermaidBlock`
2. `translator.py`: convert a `MermaidBlock` into an `ImagePrompt` with Gemini
3. `painter.py`: generate an image with `google-genai`
4. `storage.py`: save PNG bytes and embed metadata

`pipeline.py` orchestrates the full flow and handles dry-run, concurrency, logging, and failed prompt persistence.

## Configuration

- Configuration lives in `VertexConfig` in `m2c_pipeline/config.py`
- Runtime values come from `M2C_*` environment variables
- CLI args override env values through `apply_overrides()`
- Validation requires `M2C_PROJECT_ID` and a supported aspect ratio
- Authentication uses Google ADC for Vertex AI only
- Prefer `.env`-provided `GOOGLE_APPLICATION_CREDENTIALS` over implicit system ADC
- Allow system ADC as the fallback path when `.env` doesn't specify credentials
- Do not add Google AI Studio / Gemini Developer API auth
- Do not add `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or `api_key=` client wiring

## Template System

Templates live under `m2c_pipeline/templates/`.

- `base.py` defines `StyleTemplate`
- `chiikawa.py` is the only implemented template
- `templates/__init__.py` provides the registry

If a new template is added later, register it in the template registry and keep the CLI contract stable.

## Versioning

- Version is managed automatically by [release-please](https://github.com/googleapis/release-please)
- Do not manually edit `m2c_pipeline/version.py` or `.release-please-manifest.json`
- Release workflow: merge to `main` → release-please opens a version-bump PR → merge that PR → tag and GitHub Release are created automatically
- Configuration lives in `release-please-config.json`

## Skill Distribution

The `skill` branch is the remote-install target for CC Switch users.

- It is published automatically by CI (`scripts/ci/publish_skill_branch.py`) at the end of every release-please release.
- It contains only the files listed in `policy/package-allowlist.txt`.
- **Never commit to the `skill` branch manually** — it is always overwritten by CI force-push.
- The branch is protected by a GitHub Ruleset (`Protect skill branch`) that restricts deletion. Force-push remains allowed for CI (personal repo limitation: GitHub Actions bypass is an Organization-only feature).

## Guardrails

- Keep this project `m2c_pipeline`-only; do not reintroduce alternative backends
- Treat `README.md` as the user-facing source of truth for setup and operation
- Treat `SKILL.md` as the agent-oriented operational wrapper
- Treat `SKILL_README.md` as the skill-branch README; it replaces `README.md` on publish
- Prefer `./venv/bin/python` for all local Python commands when the workspace virtualenv exists
- Keep all authentication guidance Vertex AI only
- Treat `.env` plus `GOOGLE_APPLICATION_CREDENTIALS` as the recommended local path
- Treat system ADC as the fallback local path
- Never commit `.env`, output images, failed prompt logs, or local test output
