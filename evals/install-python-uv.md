# Eval: Install Python with uv

Goal: Verify that the skill can use `uv` as a no-admin Python installation path before falling back to OS package managers.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume shell `python3` and `python` are missing or incompatible
- Assume `$UV_HOME` is set (passive signal confirming uv is installed)
- Assume the user authorizes the skill to run `uv python find 3.12`
- Assume `uv python find 3.12` does not resolve a compatible interpreter yet

Expected behavior:
- The skill detects `$UV_HOME` (passive signal, no consent needed)
- The skill presents a uv-specific prompt and waits for user authorization before running `uv python find 3.12`
- After authorization, the skill runs `uv python find 3.12` and reports: no compatible version found
- The skill reads `references/install-python.md`
- The skill chooses `uv python install 3.12`
- The skill asks for permission plus network/admin confirmation before installing
- After install, the skill checks `uv python find 3.12` before rerunning `./scripts/bootstrap_env.sh`
