# Runtime Commands

- Prefer `./venv/bin/python` for every local Python command in this repository.
- Setup flow:
  - `python -m venv venv`
  - `./venv/bin/python -m pip install -r requirements.txt`
  - `cp .env.example .env`
- Offline validation:
  - `./venv/bin/python -m m2c_pipeline <input.md> --dry-run --translation-mode fallback`
- Live generation:
  - `./venv/bin/python -m m2c_pipeline <input.md> --translation-mode vertex --output-dir ./output`

Use the offline command first when the user wants validation without cloud calls or when credentials are not ready yet.
