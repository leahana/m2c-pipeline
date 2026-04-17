# Eval: Avoid Conda Base as Runtime Anchor

Goal: Verify that the skill does not anchor the repo runtime to shared `conda base`.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume `$CONDA_DEFAULT_ENV=base` (passive signal indicating conda base is active)
- Assume `$PYENV_ROOT` or `$UV_HOME` is also set (another manager available via passive signal)

Expected behavior:
- The skill recognizes `conda base` as a shared environment, not the preferred runtime anchor
- The skill does not recommend installing this project's dependencies directly into `conda base`
- The skill switches to another compatible interpreter source for bootstrap
- The skill still ends on repo-local `./venv`
