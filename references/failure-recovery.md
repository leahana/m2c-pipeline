# Failure Recovery

- If offline validation fails, confirm the command includes both `--dry-run` and `--translation-mode fallback`.
- If live validation fails before image generation, check:
  - `M2C_PROJECT_ID`
  - `GOOGLE_APPLICATION_CREDENTIALS`
  - Vertex AI ADC availability
- If image generation fails after prompt translation, inspect the emitted `*_FAILED.txt` file. It should capture the source Mermaid block and the final prompt used for the failed attempt.
- If the environment reports missing `google-genai`, install dependencies with `./venv/bin/python -m pip install -r requirements.txt`.
- If a request tries to route through API keys, stop and keep the fix on the Vertex AI path instead.

The recovery goal is to preserve enough context to retry safely without changing the pipeline's public interface.
