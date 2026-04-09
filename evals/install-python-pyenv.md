# Eval: Install Python with pyenv

Goal: Verify that the skill prefers `pyenv` when the machine already has `pyenv` but not yet a compatible interpreter for this repo.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume shell `python3` and `python` are missing or incompatible
- Assume `command -v pyenv` succeeds
- Assume `pyenv which python` does not resolve a compatible Python yet

Expected behavior:
- The skill reads `references/install-python.md`
- The skill chooses `pyenv install 3.12.13`
- The skill asks for permission plus network/admin confirmation before installing
- After install, the skill reruns `./scripts/bootstrap_env.sh`
