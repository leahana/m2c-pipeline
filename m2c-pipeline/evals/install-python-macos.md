# Eval: Install Python on macOS

Goal: Verify that the skill chooses the documented macOS install path when no compatible Python is available yet.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume system `python3` and `python` are missing or incompatible
- Assume `uname -s` reports `Darwin` and `command -v brew` succeeds

Expected behavior:
- The skill reads `references/install-python.md`
- The skill chooses `brew install python`
- The skill asks for permission plus network/admin confirmation before installing
- After install, the skill reruns `./scripts/bootstrap_env.sh`
