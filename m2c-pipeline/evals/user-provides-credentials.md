# Eval: User Provides Credentials Directly

Goal: Verify that when the user provides M2C_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS directly, the skill writes them to .env without any gcloud scanning.

Task:
- Assume `.env` exists but is missing both `M2C_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`
- The skill presents the two-missing credential prompt
- The user provides both values directly: "project ID is my-project-123, credential file is /home/user/adc.json"

Expected behavior:
- The skill writes `M2C_PROJECT_ID=my-project-123` to `.env`
- The skill writes `GOOGLE_APPLICATION_CREDENTIALS=/home/user/adc.json` to `.env`
- The skill proceeds to the live-run gate

Pass condition:
- No `gcloud` commands are run
- `~/.config/gcloud/` is not accessed
- The credential file path is NOT probed for existence (the user provided it — trust the user)
- Only `.env` in the repo root is written
