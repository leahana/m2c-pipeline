"""
Image storage with PNG metadata writing for m2c_pipeline.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import VertexConfig
from .extractor import MermaidBlock

logger = logging.getLogger(__name__)


class ImageStorage:
    """Save generated images to disk with embedded PNG metadata."""

    def __init__(self, config: VertexConfig) -> None:
        self._output_dir = Path(config.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        image_bytes: bytes,
        source_block: MermaidBlock,
        prompt_text: str,
    ) -> Path:
        """Save image bytes as PNG with metadata. Returns the saved file path.

        Metadata written into PNG chunks:
          - mermaid_source: original mermaid code
          - image_prompt:   the prompt used
          - generated_at:   ISO 8601 UTC timestamp
          - block_index:    position in the source document
          - diagram_type:   mermaid diagram type
        """
        filename = self._generate_filename(source_block)
        output_path = self._output_dir / filename

        output_path.write_bytes(image_bytes)

        try:
            self._write_metadata(
                image_path=output_path,
                mermaid_source=source_block.source,
                prompt_text=prompt_text,
                block_index=source_block.index,
                diagram_type=source_block.diagram_type,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write PNG metadata for %s: %s. "
                "Image is saved but without metadata.",
                output_path,
                exc,
            )

        logger.info("Saved image: %s", output_path)
        return output_path

    def save_failed_prompt(
        self,
        source_block: MermaidBlock,
        prompt_text: str,
    ) -> Path:
        """Save the failed prompt to a .txt file for manual retry."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"diagram_{timestamp}_{source_block.index:02d}_FAILED.txt"
        output_path = self._output_dir / filename

        content = (
            f"# Failed image prompt — block {source_block.index}\n"
            f"# Diagram type: {source_block.diagram_type}\n"
            f"# Source line: {source_block.line_number}\n\n"
            f"## Original Mermaid Source\n\n"
            f"```mermaid\n{source_block.source}\n```\n\n"
            f"## Image Prompt\n\n{prompt_text}\n"
        )
        output_path.write_text(content, encoding="utf-8")
        logger.warning("Saved failed prompt to: %s", output_path)
        return output_path

    @staticmethod
    def _generate_filename(block: MermaidBlock) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"diagram_{timestamp}_{block.index:02d}.png"

    @staticmethod
    def _write_metadata(
        image_path: Path,
        mermaid_source: str,
        prompt_text: str,
        block_index: int,
        diagram_type: str,
    ) -> None:
        """Embed metadata into PNG using PIL PngInfo text chunks."""
        from PIL import Image, PngImagePlugin

        img = Image.open(image_path)
        meta = PngImagePlugin.PngInfo()
        meta.add_text("mermaid_source", mermaid_source)
        meta.add_text("image_prompt", prompt_text)
        meta.add_text("generated_at", datetime.now(timezone.utc).isoformat())
        meta.add_text("block_index", str(block_index))
        meta.add_text("diagram_type", diagram_type)
        img.save(image_path, format="PNG", pnginfo=meta)
