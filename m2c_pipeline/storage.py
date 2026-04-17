"""
Image storage and debug metadata persistence for m2c_pipeline.
"""

import json
import logging
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from .config import VertexConfig
from .extractor import MermaidBlock

logger = logging.getLogger(__name__)


class ImageStorage:
    """Save generated images to disk with format-aware debug metadata."""

    def __init__(self, config: VertexConfig) -> None:
        self._config = config
        self._output_dir = Path(config.output_dir)
        self._output_format = config.output_format
        self._webp_quality = config.webp_quality
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        image_bytes: bytes,
        source_block: MermaidBlock,
        prompt_text: str,
        *,
        aspect_ratio: str | None = None,
    ) -> Path:
        """Save image bytes in the configured output format.

        PNG output keeps embedded text chunks for backwards compatibility.
        WebP output writes a ``.metadata.json`` sidecar next to the image.
        """
        from PIL import Image

        generated_at = datetime.now(timezone.utc).isoformat()
        filename = self._generate_filename(source_block, self._output_format)
        output_path = self._output_dir / filename
        debug_metadata = self._build_debug_metadata(
            source_block=source_block,
            prompt_text=prompt_text,
            generated_at=generated_at,
            image_filename=output_path.name,
            aspect_ratio=aspect_ratio,
        )

        with Image.open(BytesIO(image_bytes)) as image:
            debug_metadata["source_image_format"] = (image.format or "unknown").lower()
            debug_metadata["source_image_bytes"] = len(image_bytes)
            self._save_image(output_path, image)

        try:
            self._persist_debug_metadata(output_path, debug_metadata)
        except Exception as exc:
            if self._output_format == "webp":
                # Sidecar JSON is the only metadata carrier for WebP — treat
                # a write failure as a storage error so callers surface it.
                # Remove partial outputs so callers never see a "successful"
                # image without the required metadata sidecar.
                self._cleanup_incomplete_output(output_path)
                raise
            logger.warning(
                "Failed to write debug metadata for %s: %s. "
                "Image is saved but debug metadata may be incomplete.",
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
    def _generate_filename(block: MermaidBlock, output_format: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"diagram_{timestamp}_{block.index:02d}.{output_format}"

    def _build_debug_metadata(
        self,
        *,
        source_block: MermaidBlock,
        prompt_text: str,
        generated_at: str,
        image_filename: str,
        aspect_ratio: str | None,
    ) -> dict[str, object]:
        metadata: dict[str, object] = {
            "mermaid_source": source_block.source,
            "image_prompt": prompt_text,
            "generated_at": generated_at,
            "block_index": source_block.index,
            "diagram_type": source_block.diagram_type,
            "line_number": source_block.line_number,
            "image_model": self._config.image_model,
            "template_name": self._config.template_name,
            "translation_mode": self._config.translation_mode,
            "translation_seed": self._config.translation_seed,
            "translation_temperature": self._config.translation_temperature,
            "translation_top_p": self._config.translation_top_p,
            "output_format": self._output_format,
            "image_file": image_filename,
        }
        if aspect_ratio is not None:
            metadata["aspect_ratio"] = aspect_ratio
        if self._output_format == "webp":
            metadata["webp_quality"] = self._webp_quality
        return metadata

    def _save_image(self, output_path: Path, image) -> None:
        normalized = self._normalize_image_mode(image)
        if self._output_format == "png":
            normalized.save(output_path, format="PNG")
            return
        normalized.save(
            output_path,
            format="WEBP",
            quality=self._webp_quality,
            method=6,
        )

    def _persist_debug_metadata(
        self,
        image_path: Path,
        debug_metadata: dict[str, object],
    ) -> None:
        if self._output_format == "png":
            self._write_png_metadata(image_path, debug_metadata)
            return
        debug_metadata["output_image_bytes"] = image_path.stat().st_size
        self._write_sidecar_metadata(image_path, debug_metadata)

    @staticmethod
    def _cleanup_incomplete_output(image_path: Path) -> None:
        for path in (image_path, image_path.with_suffix(".metadata.json")):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning(
                    "Failed to remove incomplete output %s after metadata write error: %s",
                    path,
                    exc,
                )

    @staticmethod
    def _normalize_image_mode(image):
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        target_mode = "RGBA" if has_alpha else "RGB"
        if image.mode != target_mode:
            return image.convert(target_mode)
        return image

    @staticmethod
    def _write_png_metadata(
        image_path: Path,
        debug_metadata: dict[str, object],
    ) -> None:
        """Embed metadata into PNG using PIL PngInfo text chunks."""
        from PIL import Image, PngImagePlugin

        with Image.open(image_path) as image:
            meta = PngImagePlugin.PngInfo()
            for key, value in debug_metadata.items():
                meta.add_text(key, str(value))
            image.save(image_path, format="PNG", pnginfo=meta)

    @staticmethod
    def _write_sidecar_metadata(
        image_path: Path,
        debug_metadata: dict[str, object],
    ) -> None:
        metadata_path = image_path.with_suffix(".metadata.json")
        metadata_path.write_text(
            json.dumps(debug_metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
