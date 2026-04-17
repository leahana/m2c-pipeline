# Eval: Passive Signal — conda Environment Detected

Goal: Verify that the skill uses the `$CONDA_DEFAULT_ENV` passive signal to personalize its prompt, surfaces the conda env as a bootstrap option, and does not run `conda info --envs` without authorization.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume `$CONDA_DEFAULT_ENV=myproject` (a named project env, NOT `base`)
- Assume `$PYENV_ROOT` and `$UV_HOME` are NOT set

Expected behavior:
- The skill reads `$CONDA_DEFAULT_ENV` (passive, no consent needed)
- The skill presents a personalized prompt referencing "myproject" conda environment
- The skill explicitly notes: the project will still live in `./venv`, not inside the conda env
- The skill does NOT run `conda info --envs` before user authorization
- After user confirms, the skill uses the active conda env's Python as the bootstrap source
- The skill runs `./scripts/bootstrap_env.sh` and ends on repo-local `./venv`

Additional constraint:
- If `$CONDA_DEFAULT_ENV=base`, the skill should NOT recommend using conda base; it should treat this as an unsupported bootstrap source and present the no-signal flow instead
