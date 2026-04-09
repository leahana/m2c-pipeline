# Eval: Install Python with uv

Goal: Verify that the skill can use `uv` as a no-admin Python installation path before falling back to OS package managers.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume shell `python3` and `python` are missing or incompatible
- Assume `command -v uv` succeeds
- Assume `uv python find 3.12` does not resolve a compatible interpreter yet

Expected behavior:
- The skill reads `references/install-python.md`
- The skill chooses `uv python install 3.12`
- The skill asks for permission plus network/admin confirmation before installing
- The skill checks `uv python find 3.12` before rerunning `./scripts/bootstrap_env.sh`
