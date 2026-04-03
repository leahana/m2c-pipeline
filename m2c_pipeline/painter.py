"""
Gemini native image generation for m2c_pipeline.
Uses google-genai SDK with Vertex AI backend.
"""

import logging

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import VertexConfig
from .translator import ImagePrompt, _before_sleep_quota

logger = logging.getLogger(__name__)


class ImagePainter:
    """Generate images from ImagePrompt objects using Gemini native image generation."""

    def __init__(self, config: VertexConfig) -> None:
        self._config = config
        self._client = self._init_client()

    def _init_client(self):
        """Initialize google-genai client with Vertex AI backend."""
        try:
            from google import genai
            from google.genai import types
            return genai.Client(
                vertexai=True,
                project=self._config.project_id,
                location="global",
                http_options=types.HttpOptions(timeout=self._config.request_timeout * 1000),  # ms
            )
        except ImportError as exc:
            raise ImportError(
                "google-genai package not found. "
                "Run: pip install google-genai"
            ) from exc

    def paint(self, image_prompt: ImagePrompt) -> bytes:
        """Generate an image and return raw PNG bytes.

        Args:
            image_prompt: The translated prompt including aspect ratio.

        Returns:
            Raw PNG image bytes.

        Raises:
            RuntimeError: If image generation fails after all retries.
        """
        logger.info(
            "Generating image for block %d (model=%s, prompt_length=%d)",
            image_prompt.source_block.index,
            self._config.image_model,
            len(image_prompt.prompt_text),
        )

        parts = self._call_gemini(image_prompt.prompt_text, image_prompt.aspect_ratio)

        for part in parts:
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data

        raise RuntimeError(
            f"Gemini returned no images for block {image_prompt.source_block.index}. "
            "Possible content policy block. Prompt saved for manual review."
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        before_sleep=_before_sleep_quota,
        reraise=True,
    )
    def _call_gemini(self, prompt_text: str, aspect_ratio: str):
        """Gemini image generation API call with tenacity retry on 429/500."""
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._config.image_model,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                ),
            ),
        )
        return response.candidates[0].content.parts
