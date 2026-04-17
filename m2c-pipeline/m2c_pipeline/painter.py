"""
Gemini native image generation for m2c_pipeline.
Uses google-genai SDK with Vertex AI backend.
"""

import logging
import re
import threading
from io import BytesIO

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
        self._image_client = None
        self._selector_client = None
        self._retry_context = threading.local()

    def _init_image_client(self):
        """Initialize the Gemini image-generation client."""
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

    def _init_selector_client(self):
        """Initialize the Gemini multimodal selector client."""
        try:
            from google import genai
            from google.genai import types
            return genai.Client(
                vertexai=True,
                project=self._config.project_id,
                location=self._config.location,
                http_options=types.HttpOptions(timeout=self._config.request_timeout * 1000),
            )
        except ImportError as exc:
            raise ImportError(
                "google-genai package not found. "
                "Run: pip install google-genai"
            ) from exc

    def _get_image_client(self):
        if self._image_client is None:
            self._image_client = self._init_image_client()
        return self._image_client

    def _get_selector_client(self):
        if self._selector_client is None:
            self._selector_client = self._init_selector_client()
        return self._selector_client

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
            "Generating image for block %d (model=%s, prompt_length=%d, image_size=%s, candidate_count=%d, seed=%s)",
            image_prompt.source_block.index,
            self._config.image_model,
            len(image_prompt.prompt_text),
            self._config.image_size,
            self._config.image_candidate_count,
            self._config.image_seed,
        )
        self._begin_retry_capture()

        try:
            candidate_images = self._call_gemini(
                image_prompt.prompt_text,
                image_prompt.aspect_ratio,
            )
            retry_events = self._consume_retry_events()
        except Exception:
            retry_events = self._consume_retry_events()
            self._set_last_result({"retry_events": retry_events})
            raise

        if not candidate_images:
            self._set_last_result(
                {
                    "retry_events": retry_events,
                    "candidate_image_count": 0,
                    "selected_candidate_index": None,
                    "selection_method": "no_candidates_returned",
                    "selector_seed": None,
                }
            )
            raise RuntimeError(
                f"Gemini returned no images for block {image_prompt.source_block.index}. "
                "Possible content policy block. Prompt saved for manual review."
            )

        selected_candidate_index = 0
        selection_method = "single_candidate"
        selector_seed = None
        if self._config.image_candidate_count > 1 and len(candidate_images) > 1:
            try:
                selected_candidate_index = self._select_best_candidate(
                    image_prompt,
                    candidate_images,
                )
                selection_method = "vision_selector"
                selector_seed = self._config.translation_seed
            except Exception as exc:
                logger.warning(
                    "Candidate selection failed for block %d; falling back to the first image: %s",
                    image_prompt.source_block.index,
                    exc,
                )
                selected_candidate_index = 0
                selection_method = f"fallback_first_candidate_after_{type(exc).__name__}"

        self._set_last_result(
            {
                "retry_events": retry_events,
                "candidate_image_count": len(candidate_images),
                "selected_candidate_index": selected_candidate_index,
                "selection_method": selection_method,
                "selector_seed": selector_seed,
            }
        )

        return candidate_images[selected_candidate_index]

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

        response = self._get_image_client().models.generate_content(
            model=self._config.image_model,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                candidate_count=self._config.image_candidate_count,
                seed=self._config.image_seed,
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=self._config.image_size,
                ),
            ),
        )
        images = []
        for candidate in response.candidates or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", ()) or ():
                inline_data = getattr(part, "inline_data", None)
                data = getattr(inline_data, "data", None)
                if data:
                    images.append(data)
        return images

    def _select_best_candidate(
        self,
        image_prompt: ImagePrompt,
        candidate_images: list[bytes],
    ) -> int:
        from PIL import Image
        from google.genai import types

        contents: list[object] = []
        for index, image_bytes in enumerate(candidate_images):
            with Image.open(BytesIO(image_bytes)) as image:
                contents.append(f"Candidate {index}")
                contents.append(image.copy())

        contents.append(self._build_selection_prompt(image_prompt, len(candidate_images)))
        response = self._get_selector_client().models.generate_content(
            model=self._config.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.0,
                top_p=0.1,
                seed=self._config.translation_seed,
                candidate_count=1,
                max_output_tokens=32,
            ),
        )
        return self._parse_best_index(response.text or "", len(candidate_images))

    @staticmethod
    def _build_selection_prompt(image_prompt: ImagePrompt, candidate_count: int) -> str:
        return (
            "You are comparing illustration candidates for Chinese text legibility.\n"
            f"Mermaid source:\n{image_prompt.source_block.source}\n\n"
            f"Prompt used for generation:\n{image_prompt.prompt_text}\n\n"
            f"There are {candidate_count} candidates labelled Candidate 0 through "
            f"Candidate {candidate_count - 1}.\n"
            "Choose the one that best satisfies all of these priorities:\n"
            "1. Chinese title and labels have fully formed strokes and radicals.\n"
            "2. Text is crisp, not blurry, not fragmented, and not overlapping.\n"
            "3. The image keeps text minimal: one short title and a few short labels.\n"
            "4. The Chinese text best matches the intended Mermaid labels.\n"
            "Return exactly one line in this format:\n"
            "BEST_INDEX: <number>"
        )

    @staticmethod
    def _parse_best_index(response_text: str, candidate_count: int) -> int:
        match = re.search(r"BEST_INDEX:\s*(\d+)", response_text)
        if not match:
            raise ValueError(f"Selector returned an unparsable response: {response_text!r}")

        best_index = int(match.group(1))
        if not 0 <= best_index < candidate_count:
            raise ValueError(
                f"Selector returned out-of-range candidate index {best_index} "
                f"for {candidate_count} candidates."
            )
        return best_index
