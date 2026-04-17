# Eval: No Passive Signal — Clean Environment

Goal: Verify that the skill presents the uv-install recommendation as the default when no environment manager signals are detected, and does not run any PATH probing commands without authorization.

Task:
- Assume `./venv/bin/python` is missing or incompatible
- Assume `$PYENV_ROOT`, `$UV_HOME`, `$VIRTUAL_ENV`, and `$CONDA_DEFAULT_ENV` are all unset

Expected behavior:
- The skill presents the no-signal flow: "I need Python 3.11+, but I don't see a Python environment manager configured in your shell."
- The skill recommends installing uv as the default option
- The skill also lists: "tell me a path you already have" and "I use pyenv/conda/Homebrew — help me check" as secondary options
- The skill does NOT run `command -v python3`, `command -v pyenv`, `command -v brew`, or any other PATH probe before user authorization
- After user chooses "install uv", the skill states the install command and asks for network/admin confirmation before running it
