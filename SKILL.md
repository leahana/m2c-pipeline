# m2c-pipeline

## Overview

`m2c-pipeline` turns Mermaid diagrams in Markdown into Chiikawa-style illustration prompts and, in live mode, PNG images. The public runtime entrypoint is documented in [README.md](README.md).

## Prerequisites

- Python 3.11 or newer
- Dependencies installed from [requirements.txt](requirements.txt)
- For live generation, a Vertex AI project and ADC credentials configured from [.env.example](.env.example)

## Inputs

- A Markdown file containing one or more fenced `mermaid` code blocks
- Optional CLI overrides for template, aspect ratio, output directory, concurrency, log level, and translation mode
- Optional `M2C_*` environment variables for default runtime values

## Outputs

- In offline dry-run mode: translated prompts in logs and a successful exit
- In live mode: PNG files with embedded Mermaid and prompt metadata
- On live image-generation failure: `*_FAILED.txt` debug files with the source Mermaid and final prompt

## Usage

```bash
python -m m2c_pipeline path/to/input.md --dry-run --translation-mode fallback
python -m m2c_pipeline path/to/input.md --translation-mode vertex --output-dir ./output
python -m m2c_pipeline --version
```

## Offline Dry Run

```bash
python -m m2c_pipeline tests/fixtures/test_input.md --dry-run --translation-mode fallback
```

This validation path does not require a cloud project, ADC credentials, or a live translation client.

## Constraints

- The published artifact is a single generic skill package
- Live generation is Vertex-only
- Offline mode is limited to prompt generation and dry-run validation
- Local links in this document must stay inside the package allowlist
