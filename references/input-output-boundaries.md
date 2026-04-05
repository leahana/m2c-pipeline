# Input And Output Boundaries

## Input

- A Markdown file with one or more fenced `mermaid` code blocks.
- Any diagram type is supported — the extractor matches any ` ```mermaid ` block regardless of diagram type. The diagram type is lowercased when stored (e.g. `sequencediagram`, `classdiagram`, `flowchart`).
- Optional CLI overrides: `--template`, `--aspect-ratio`, `--output-dir`, `--max-workers`, `--log-level`, `--translation-mode`, `--dry-run`.

**Minimal input example** (`fixtures/minimal-input.md`):

````markdown
# Minimal Mermaid Smoke Input

```mermaid
flowchart LR
    A[Install dependencies] --> B[Run bootstrap]
    B --> C[Dry run m2c_pipeline]
```
````

## Offline Output (dry-run)

- Successful exit with no files written to the output directory.
- Translation logs show the generated Chiikawa-style prompt for each block.
- No cloud project or credentials required when `--translation-mode fallback` is also set.

## Live Output

- PNG files written to the output directory (default `./output`).
- **Filename format**: `diagram_YYYYMMDD_HHMMSS_NN.png` where `NN` is the zero-padded block index.
- Each PNG has embedded metadata text chunks (readable with PIL or `exiftool`):

| Field | Content |
|-------|---------|
| `mermaid_source` | Original Mermaid code block |
| `image_prompt` | Final prompt sent to the image model |
| `generated_at` | ISO 8601 UTC timestamp |
| `block_index` | Block position in the source document (0-based) |
| `diagram_type` | Detected diagram type, lowercased (e.g. `flowchart`, `sequencediagram`, `classdiagram`) |

## Failure Output

- When image generation fails for a block, the pipeline writes a recovery file to the output directory.
- **Failure filename format**: `diagram_YYYYMMDD_HHMMSS_NN_FAILED.txt`
- The file contains the original Mermaid source and the final prompt that was attempted, enough context to retry manually or adjust the prompt.
- Other blocks in the same run are not affected; the pipeline continues processing remaining blocks.
