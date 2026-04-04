# Vertex Auth

- Recommended local auth path:
  - Set `M2C_PROJECT_ID` in `.env`
  - Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env` to an absolute JSON credential path
- Fallback auth path:
  - `gcloud auth application-default login`
  - `gcloud auth application-default set-quota-project YOUR_PROJECT_ID`
- Runtime values come from `M2C_*` environment variables, and CLI flags override env defaults.
- This project must stay Vertex AI only.
- Do not introduce `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `genai.Client(api_key=...)`, or any Google AI Studio / Gemini Developer API path.

When credentials look wrong, check `.env` first, then verify whether system ADC is expected to take over.
