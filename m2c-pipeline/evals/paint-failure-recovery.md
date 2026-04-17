# Eval: Paint Failure Recovery

Goal: Verify that the skill handles image-generation failures without changing the pipeline contract.

Task:
- Simulate or inspect a live run where translation succeeds but the paint stage fails

Expected behavior:
- The skill points to the emitted `*_FAILED.txt` artifact
- The response explains that the file should contain the Mermaid source and the final prompt
- The follow-up keeps the retry path on Vertex AI and does not switch to API keys
