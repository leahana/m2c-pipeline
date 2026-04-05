# Eval: Vertex Live Run

Goal: Verify that the skill chooses the supported live path and keeps auth on Vertex AI.

Task:
- Run `./scripts/bootstrap_env.sh`
- Run `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --translation-mode vertex --output-dir ./output`

Expected behavior:
- The skill prefers the published bootstrap entry point on POSIX systems
- The skill checks Vertex AI credentials before running
- The command keeps `--translation-mode vertex`
- Success is reported as generated PNG files and metadata, not as dry-run logs
