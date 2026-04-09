# Runtime Commands

- If the current workspace already contains `m2c_pipeline/`, `requirements.txt`, and `SKILL.md`, run setup and CLI commands from that repo root.
- Prefer `./venv/bin/python` for every local Python command in this repository.
- You do not need to activate the shell virtualenv explicitly; prefer direct `./venv/bin/python` invocations.
- Preflight gate: do not run `python -m m2c_pipeline` commands until Python compatibility checks and bootstrap are complete.
- Preflight order:
  - Prefer compatible `./venv/bin/python`
  - Else check compatible system `python3`/`python` and classify the source: `pyenv` -> active venv / uv-managed env -> named Conda env -> Homebrew / Python.org / distro Python
  - Avoid `conda base` as the default bootstrap anchor; use it only if the user explicitly wants that tradeoff
  - Else read `references/install-python.md`, choose one platform path, and ask for permission plus network/admin confirmation
  - When installing a new interpreter, prefer existing user-space managers first: `pyenv`, then `uv`, then platform package managers
- Default POSIX bootstrap entry point:
  - `./scripts/bootstrap_env.sh`
- Default Windows repo-local bootstrap:
  - `python -m venv venv`
  - `.\venv\Scripts\python.exe -m pip install -r requirements.txt`
- Setup flow:
  - `./scripts/bootstrap_env.sh`
  - `cp .env.example .env`
- Offline validation:
  - `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback`
- Live generation:
  - `./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --translation-mode vertex --output-dir ./output`

Use the offline command first when the user wants validation without cloud calls or when credentials are not ready yet.
