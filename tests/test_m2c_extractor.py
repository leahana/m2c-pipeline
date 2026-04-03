import tempfile
import unittest
from pathlib import Path

from m2c_pipeline.extractor import MermaidExtractor


class MermaidExtractorTests(unittest.TestCase):
    def test_extract_from_string_returns_multiple_blocks(self) -> None:
        content = """
# Demo

```mermaid
flowchart LR
A[开始] --> B[结束]
```

```mermaid
sequenceDiagram
Alice->>Bob: hello
```
"""
        extractor = MermaidExtractor()

        blocks = extractor.extract_from_string(content)

        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].diagram_type, "flowchart")
        self.assertEqual(blocks[0].line_number, 4)
        self.assertEqual(blocks[1].diagram_type, "sequencediagram")

    def test_extract_reads_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.md"
            input_path.write_text(
                "```mermaid\nclassDiagram\nA <|-- B\n```",
                encoding="utf-8",
            )

            blocks = MermaidExtractor().extract(str(input_path))

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].diagram_type, "classdiagram")

    def test_extract_raises_when_file_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            MermaidExtractor().extract("/tmp/definitely-missing-mermaid-file.md")


if __name__ == "__main__":
    unittest.main()
