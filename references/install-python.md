# Install or Select Python for Agent-First Setup

Use this reference when the repo does not already have a compatible `./venv/bin/python`, or when you need to classify what the current `python3` or `python` actually is before bootstrapping.

## Runtime Contract

- Always finish on repo-local `./venv/bin/python` or `.\venv\Scripts\python.exe`.
- `pyenv`, `uv`, Conda, Homebrew, Python.org, and distro Python are bootstrap sources, not the final runtime contract.

## Preflight

- Reuse `./venv/bin/python` when it already exists and is `>= 3.11`.
- Otherwise check whether system `python3` or `python` is already `>= 3.11`, then classify the source before using it.
- Prefer existing user-space managers before system-wide installers.
- Before running any installer, ask the user for permission plus network/admin confirmation.
- After Python is available, return to the repo root and run the repo-local bootstrap:
  - POSIX: `./scripts/bootstrap_env.sh`
  - Windows: `python -m venv venv` then `.\venv\Scripts\python.exe -m pip install -r requirements.txt`

## Detection Helpers

- `python3 -c 'import sys; print(sys.executable); print(sys.version)'`
- `echo "$VIRTUAL_ENV"`
- `echo "$CONDA_DEFAULT_ENV"`
- `pyenv which python`
- `uv python find 3.12`

## Existing Environment Rules

### pyenv

Choose this path when `command -v pyenv` succeeds.

- Detection:
  - `command -v pyenv`
  - `pyenv which python`
- Preferred use:
  - If `pyenv which python` resolves to a compatible version, use it as the bootstrap source and rerun the repo-local bootstrap.
  - If `pyenv` exists but no compatible version is installed, install command: `pyenv install 3.12.13`
- Next step:
  - `./scripts/bootstrap_env.sh`

### uv

Choose this path when `command -v uv` succeeds and the repo is not already using a healthy `./venv`.

- Detection:
  - `command -v uv`
  - `uv python find 3.12`
- Preferred use:
  - If `uv python find 3.12` resolves a compatible interpreter, use it only as the bootstrap source and still create repo-local `./venv`.
  - If no compatible interpreter exists yet, install command: `uv python install 3.12`
- Next step:
  - If needed, make sure `uv python find 3.12` resolves first, then run `./scripts/bootstrap_env.sh`

### Conda

Choose this path only when the active Conda env already provides the only compatible interpreter available.

- Detection:
  - `echo "$CONDA_DEFAULT_ENV"`
  - `conda info --envs`
- Preferred use:
  - Reuse a named project env only as a temporary bootstrap source.
  - Do not bootstrap from `conda base` by default.
  - Do not install this project's dependencies directly into shared `base`.
- Next step:
  - `./scripts/bootstrap_env.sh`

### Global Python

Choose this path when `python3` or `python` is already compatible and comes from Homebrew, Python.org, a distro package, or another global install.

- Detection:
  - `python3 -c 'import sys; print(sys.executable)'`
  - `command -v python3`
- Preferred use:
  - Use the compatible interpreter as the bootstrap source.
  - Still create and run the repo-local `./venv`; do not keep the runtime on the global interpreter.
- Next step:
  - `./scripts/bootstrap_env.sh`

## macOS

Choose this path when `uname -s` reports `Darwin`, no compatible `pyenv` or `uv` path is available, and `command -v brew` succeeds.

- Detection:
  - `uname -s`
  - `command -v brew`
- Install command:
  - `brew install python`
- Next step:
  - `./scripts/bootstrap_env.sh`

## Debian/Ubuntu

Choose this path when `uname -s` reports `Linux`, `command -v apt-get` succeeds, and the machine is Debian-family.

- Detection:
  - `uname -s`
  - `command -v apt-get`
  - `test -f /etc/debian_version`
- Install command:
  - `sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv`
- Next step:
  - `./scripts/bootstrap_env.sh`

## Windows

Prefer `winget`. If it is unavailable, try `choco`. If neither package manager is available but WSL is acceptable to the user, use the WSL path.

### winget

- Detection:
  - `Get-Command winget -ErrorAction SilentlyContinue`
- Install command:
  - `winget install -e --id Python.Python.3.12`
- Next step:
  - `python -m venv venv`
  - `.\venv\Scripts\python.exe -m pip install -r requirements.txt`

### choco

- Detection:
  - `Get-Command choco -ErrorAction SilentlyContinue`
- Install command:
  - `choco install python312 -y`
- Next step:
  - `python -m venv venv`
  - `.\venv\Scripts\python.exe -m pip install -r requirements.txt`

### WSL fallback

- Detection:
  - `Get-Command wsl -ErrorAction SilentlyContinue`
- Install command:
  - `wsl --install -d Ubuntu`
- Next step:
  - Use the Debian/Ubuntu path inside WSL, then run the POSIX repo-local bootstrap there.

## Unsupported Hosts

If none of the supported manager or package-manager paths are available:

- Do not invent a new install flow from scratch.
- Ask the user to install any Python `>= 3.11` manually.
- After the user confirms Python is available, rerun the repo-local bootstrap for the current platform.
