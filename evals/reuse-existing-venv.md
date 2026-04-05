# Eval: Reuse Existing Venv

Goal: Verify that the skill reuses a healthy virtualenv without recreating it, while still running the repo-local bootstrap to sync dependencies.

Task:
- The workspace already has a valid `./venv/bin/python` (Python 3.11+) and dependencies installed
- The agent runs preflight and determines `./venv/bin/python` is compatible
- The agent uses the existing repo-local virtualenv as the bootstrap interpreter
- The agent still runs `./scripts/bootstrap_env.sh` before executing the pipeline

Expected behavior:
- The agent checks `./venv/bin/python` first (as required by preflight order)
- If `./venv/bin/python` is healthy, the agent reuses that venv instead of looking for a different interpreter
- The agent does not reinstall system Python or recreate `./venv` when the existing venv is already healthy
- The agent still runs the repo-local bootstrap so requirements stay aligned with the current checkout
- The pipeline runs successfully using the existing virtualenv after bootstrap completes
