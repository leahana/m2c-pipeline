"""
Mermaid code block extractor for m2c_pipeline.
Reads a Markdown file and returns all mermaid fenced code blocks.
"""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MermaidBlock:
    """A single extracted mermaid code block."""

    index: int          # 0-based position in the document
    source: str         # Raw mermaid code (without the fence lines)
    diagram_type: str   # e.g. "graph", "sequenceDiagram", "flowchart", "classDiagram"
    line_number: int    # 1-based line number where ```mermaid appears


_MERMAID_FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


class MermaidExtractor:
    """Extract all mermaid code blocks from a Markdown file or string."""

    def extract(self, markdown_path: str) -> list[MermaidBlock]:
        """Read file and extract all mermaid blocks."""
        path = Path(markdown_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {markdown_path}")
        content = path.read_text(encoding="utf-8")
        return self.extract_from_string(content)

    def extract_from_string(self, content: str) -> list[MermaidBlock]:
        """Extract mermaid blocks from a Markdown string."""
        blocks: list[MermaidBlock] = []

        for idx, match in enumerate(_MERMAID_FENCE_RE.finditer(content)):
            source = match.group(1).rstrip()
            diagram_type = self._parse_diagram_type(source)
            line_number = content[: match.start()].count("\n") + 1
            blocks.append(
                MermaidBlock(
                    index=idx,
                    source=source,
                    diagram_type=diagram_type,
                    line_number=line_number,
                )
            )

        return blocks

    @staticmethod
    def _parse_diagram_type(source: str) -> str:
        """Parse diagram type from the first non-empty line of mermaid source."""
        for line in source.splitlines():
            stripped = line.strip()
            if stripped:
                # e.g. "graph TD" -> "graph", "sequenceDiagram" -> "sequenceDiagram"
                return stripped.split()[0].lower()
        return "unknown"
