# Input And Output Boundaries

- Supported input:
  - A Markdown file with one or more fenced `mermaid` code blocks
  - Optional CLI overrides for template, aspect ratio, output directory, concurrency, log level, and translation mode
- Offline output:
  - Successful exit
  - Prompt generation visible through logs
  - No cloud project or live credentials required
- Live output:
  - PNG files written to the output directory
  - Embedded metadata including the Mermaid source and final prompt
- Failure output:
  - `*_FAILED.txt` files when live image generation cannot complete

The pipeline shape is fixed: extract Mermaid blocks, translate them into image prompts, generate PNG bytes, then store the image and metadata.
