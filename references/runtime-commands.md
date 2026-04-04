# Runtime Commands

- Prefer `./venv/bin/python` for every local Python command in this repository.
- Setup flow:
  - `python -m venv venv`
  - `./venv/bin/python -m pip install -r requirements.txt`
  - `cp .env.example .env`
- Offline validation:
  - `./venv/bin/python -m m2c_pipeline tests/fixtures/test_input.md --dry-run --translation-mode fallback`
- Live generation:
  - `./venv/bin/python -m m2c_pipeline tests/fixtures/test_input.md --translation-mode vertex --output-dir ./output`
- Targeted tests:
  - `./venv/bin/python -m unittest tests.test_m2c_config tests.test_m2c_cli tests.test_m2c_extractor tests.test_m2c_pipeline tests.test_m2c_storage tests.test_m2c_translator`
  - `./venv/bin/python tests/smoke_test.py --input tests/fixtures/test_input.md`

Use the offline command first when the user wants validation without cloud calls or when credentials are not ready yet.
