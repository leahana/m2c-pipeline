# Eval: Offline Dry Run

Goal: Verify that the skill chooses the offline validation path without requiring cloud credentials.

Task:
- Run `./scripts/bootstrap_env.sh`
- Run `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback`

Expected behavior:
- The skill prefers the published bootstrap entry point on POSIX systems
- The skill uses `./venv/bin/python`
- The command stays in offline mode
- The result reports prompt-generation validation rather than PNG creation
