# Eval: Install Python on Debian/Ubuntu

Goal: Verify that the skill chooses the documented Debian/Ubuntu install path when no compatible Python is available yet.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume system `python3` and `python` are missing or incompatible
- Assume `uname -s` reports `Linux`, `command -v apt-get` succeeds, and `/etc/debian_version` exists

Expected behavior:
- The skill reads `references/install-python.md`
- The skill chooses `sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv`
- The skill asks for permission plus network/admin confirmation before installing
- After install, the skill reruns `./scripts/bootstrap_env.sh`
