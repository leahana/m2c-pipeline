# Vertex Auth

This project must stay Vertex AI only.

- Do not use `GOOGLE_API_KEY`
- Do not use `GEMINI_API_KEY`
- Do not use Google AI Studio or the Gemini Developer API
- Do not introduce `genai.Client(api_key=...)`

## Prompt Language Policy

- Write guidance-flow prompts in English by default.
- If the user is clearly Chinese-speaking, keep the operational prompt in English and append `Reply to the user in Chinese.`
- The goal is English prompt logic with a localized user-facing reply only when needed.
- If the user writes in Chinese, reply in Chinese and keep the auth guidance consistent with the same workflow.

## What To Say First

Before a live Vertex AI run, explicitly remind the user that these two variables matter:

- `M2C_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`

Default wording:

> Before running live Vertex mode, confirm `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`. If you already have both values, I can set them for you.

If the user wrote in Chinese, instruct the model to deliver the same message in Chinese.

If the user does not have both values yet, continue with:

> If you do not have them yet, I can guide you through the Google Cloud, `gcloud`, and Vertex AI ADC setup path.

## Preferred Path: `.env`

Prefer the repo-local `.env` path:

1. Make sure the repo has a `.env`
2. Set `M2C_PROJECT_ID`
3. Set `GOOGLE_APPLICATION_CREDENTIALS` to an absolute JSON credential path
4. Run Vertex mode

Example:

```dotenv
M2C_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/adc-or-service-account.json
```

Notes:

- `M2C_PROJECT_ID` is the Google Cloud project ID for the Vertex AI project
- `GOOGLE_APPLICATION_CREDENTIALS` should point to a readable local JSON credential file
- The credential path must be absolute
- If the user already has both values, offer to write them into `.env` directly

Suggested wording:

> If you have `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`, I can help set them for you.

## Fallback Path: System ADC

If the user does not want to set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`, use system ADC instead:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

When using this path:

- `M2C_PROJECT_ID` should still be set in `.env`
- `GOOGLE_APPLICATION_CREDENTIALS` may be left unset
- The Google SDK will fall back to system ADC

Only continue with this path if the user explicitly wants system ADC.

## Docs To Point Users To

If the user is missing credentials or has not configured local auth yet, direct them to:

- Google Cloud docs for installing and signing in to the `gcloud` CLI
- Google Cloud docs for `gcloud auth application-default login`
- Vertex AI docs for Application Default Credentials (ADC)
- Vertex AI docs for local development authentication setup

Do not redirect them toward an API key workflow.

## Live-Run Gate

Only start a live Vertex run after one of these is true:

1. `.env` contains both `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`
2. The user explicitly wants system ADC and has completed `gcloud auth application-default login`

If neither condition is true, pause and clarify the auth path first.

## Quick Verification Checklist

Before the live run:

- Confirm `.env` exists
- Confirm `M2C_PROJECT_ID` is set to a real project ID
- Confirm `GOOGLE_APPLICATION_CREDENTIALS` is set, or the user explicitly chose system ADC
- If `GOOGLE_APPLICATION_CREDENTIALS` is set, confirm the file exists and is readable
- Confirm the input Markdown contains at least one fenced `mermaid` block

## Troubleshooting Order

If live mode fails with an auth-looking error, check in this order:

1. `M2C_PROJECT_ID` in `.env`
2. `GOOGLE_APPLICATION_CREDENTIALS` in `.env`
3. Whether the JSON credential file exists and is readable
4. Whether the user actually completed `gcloud auth application-default login`
5. Whether `gcloud auth application-default set-quota-project YOUR_PROJECT_ID` is also needed

Do not introduce an API key path during troubleshooting.
