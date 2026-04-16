"""
Gemini native image generation for m2c_pipeline.
Uses google-genai SDK with Vertex AI backend.
"""

import logging
import threading

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .config import VertexConfig
from .translator import ImagePrompt, _before_sleep_with_diagnostics

logger = logging.getLogger(__name__)


class ImagePainter:
    """Generate images from ImagePrompt objects using Gemini native image generation."""

    def __init__(self, config: VertexConfig) -> None:
        self._config = config
        self._client = None
        self._retry_context = threading.local()

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

    def _get_client(self):
        if self._client is None:
            self._client = self._init_client()
        return self._client

    def _begin_retry_capture(self) -> None:
        self._retry_context.events = []
        self._retry_context.last_result = {}

    def _record_retry_event(self, event: dict[str, object]) -> None:
        events = getattr(self._retry_context, "events", None)
        if events is not None:
            events.append(event)

    def _consume_retry_events(self) -> list[dict[str, object]]:
        events = list(getattr(self._retry_context, "events", []))
        self._retry_context.events = []
        return events

    def _set_last_result(self, payload: dict[str, object]) -> None:
        self._retry_context.last_result = payload

    def consume_last_result(self) -> dict[str, object]:
        payload = dict(getattr(self._retry_context, "last_result", {}))
        self._retry_context.last_result = {}
        return payload

    def paint(self, image_prompt: ImagePrompt) -> bytes:
        """Generate an image and return raw image bytes from Vertex AI.

        Args:
            image_prompt: The translated prompt including aspect ratio.

        Returns:
            Raw generated image bytes.

        Raises:
            RuntimeError: If image generation fails after all retries.
        """
        logger.info(
            "Generating image for block %d (model=%s, prompt_length=%d)",
            image_prompt.source_block.index,
            self._config.image_model,
            len(image_prompt.prompt_text),
        )
        self._begin_retry_capture()

        try:
            parts = self._call_gemini(image_prompt.prompt_text, image_prompt.aspect_ratio)
            retry_events = self._consume_retry_events()
        except Exception:
            retry_events = self._consume_retry_events()
            self._set_last_result({"retry_events": retry_events})
            raise

        self._set_last_result(
            {
                "retry_events": retry_events,
                "response_part_count": len(parts),
            }
        )

        for part in parts:
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data

        raise RuntimeError(
            f"Gemini returned no images for block {image_prompt.source_block.index}. "
            "Possible content policy block. Prompt saved for manual review."
        )

    @retry(
        retry=retry_if_exception(lambda exc: not isinstance(exc, ImportError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        before_sleep=_before_sleep_with_diagnostics,
        reraise=True,
    )
    def _call_gemini(self, prompt_text: str, aspect_ratio: str):
        """Gemini image generation API call with tenacity retry on 429/500."""
        from google.genai import types

        response = self._get_client().models.generate_content(
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
