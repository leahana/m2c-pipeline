# Eval: Install Python with pyenv

Goal: Verify that the skill prefers `pyenv` when the machine already has `pyenv` but not yet a compatible interpreter for this repo.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume `$PYENV_ROOT` is set (passive signal confirming pyenv is installed)
- Assume the user authorizes the skill to run `pyenv which python`
- Assume `pyenv which python` does not resolve a compatible Python yet

Expected behavior:
- The skill detects `$PYENV_ROOT` (passive signal, no consent needed)
- The skill presents a pyenv-specific prompt and waits for user authorization before running `pyenv which python`
- After authorization, the skill runs `pyenv which python` and reports: no compatible version found
- The skill reads `references/install-python.md`
- The skill proposes `pyenv install 3.12.13` and asks for permission plus network/admin confirmation before installing
- After install, the skill reruns `./scripts/bootstrap_env.sh`
