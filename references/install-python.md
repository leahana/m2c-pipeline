# Install Python for Agent-First Setup

Use this reference only when the repo does not already have a compatible `./venv/bin/python` and the host does not already provide a compatible `python3` or `python`.

## Preflight

- Reuse `./venv/bin/python` when it already exists and is `>= 3.11`.
- Otherwise check whether system `python3` or `python` is already `>= 3.11`.
- If neither is compatible, choose exactly one platform-appropriate install path below.
- Before running any system installer, ask the user for permission plus network/admin confirmation.
- After Python is installed, return to the repo root and run the repo-local bootstrap:
  - POSIX: `./scripts/bootstrap_env.sh`
  - Windows: `python -m venv venv` then `.\venv\Scripts\python.exe -m pip install -r requirements.txt`

## macOS

Choose this path when `uname -s` reports `Darwin` and `command -v brew` succeeds.

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

If none of the supported package-manager paths are available:

- Do not invent a new install flow from scratch.
- Ask the user to install any Python `>= 3.11` manually.
- After the user confirms Python is available, rerun the repo-local bootstrap for the current platform.
