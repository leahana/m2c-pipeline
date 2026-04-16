# Eval: User Provides Python Path Directly

Goal: Verify that when the user directly provides a Python interpreter path, the skill uses it immediately without any system scanning.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- The user says: "use /usr/local/bin/python3.12" (or any absolute path)

Expected behavior:
- The skill validates the provided path by running `python --version` on it
- The skill does NOT probe pyenv, uv, conda, or system PATH for alternatives
- The skill uses the provided path as the bootstrap source
- The skill runs `./scripts/bootstrap_env.sh` using that interpreter
- The skill ends on repo-local `./venv`

Pass condition:
- No `pyenv which python`, `uv python find`, `conda info`, or `command -v` commands are run
- The validation step (`python --version`) is the only external command before bootstrap
