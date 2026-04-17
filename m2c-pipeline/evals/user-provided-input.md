# Eval: User-Provided Input

Goal: Verify that the skill correctly handles a Markdown file supplied by the user rather than the built-in fixture.

Task:
- The user says: "Generate images from my-diagram.md" (or provides any path to their own Markdown file)
- The agent confirms the file contains at least one fenced `mermaid` block
- The agent runs: `./venv/bin/python -m m2c_pipeline <user-path> --dry-run --translation-mode fallback`
- If the dry-run succeeds, the agent proceeds with the live run (or reports the dry-run result if no credentials are available)

Expected behavior:
- The agent does not hard-code `fixtures/minimal-input.md` when the user has provided a different file
- The agent validates input (confirms mermaid blocks exist) before running
- The agent uses `./venv/bin/python` and the repo-local virtualenv
- The agent reports the number of blocks found and the generated PNG paths (or dry-run prompts)
