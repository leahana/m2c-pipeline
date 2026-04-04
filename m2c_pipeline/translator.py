"""
Mermaid -> Chiikawa prompt translator using google-genai SDK (Vertex AI backend).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .config import VALID_ASPECT_RATIOS, VertexConfig
from .extractor import MermaidBlock
from .templates.base import StyleTemplate

logger = logging.getLogger(__name__)

# Supported aspect ratios for Gemini image generation
_VALID_RATIOS = set(VALID_ASPECT_RATIOS)
_DEFAULT_RATIO = "1:1"


def _classify_quota_error(exc) -> tuple[str, str]:
    """从 google-genai ClientError 解析配额限制类型，返回 (quota_type, raw_message)。

    ClientError(status_code, response_json, response) 中 args[1] 是响应 JSON dict。
    两种常见 message：
      "Resource exhausted. Please try again later."     → RPM 瞬时限流
      "Resource has been exhausted (e.g. check quota)." → TPM/总配额耗尽
    """
    try:
        args = getattr(exc, 'args', ())
        response_json = args[1] if len(args) >= 2 and isinstance(args[1], dict) else {}
        message = response_json.get('error', {}).get('message', '')
    except Exception:
        message = str(exc)

    msg_lower = message.lower()
    if 'try again later' in msg_lower:
        quota_type = 'RPM (requests-per-minute burst limit)'
    elif 'check quota' in msg_lower or 'has been exhausted' in msg_lower:
        quota_type = 'TPM/Quota (tokens-per-minute or total quota exhausted)'
    elif 'rate' in msg_lower:
        quota_type = 'Rate limit'
    else:
        quota_type = f'Unknown quota type (status={getattr(exc, "status_code", "?")})'

    return quota_type, message


def _before_sleep_quota(retry_state) -> None:
    """tenacity before_sleep：解析 429 响应体，区分 RPM / TPM，输出结构化 WARNING。"""
    exc = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    sleep_secs = getattr(retry_state.next_action, 'sleep', 0)

    if exc is None:
        logger.warning("Retry attempt %d, sleeping %.0fs", attempt, sleep_secs)
        return

    status_code = getattr(exc, 'status_code', None) or (exc.args[0] if exc.args else '?')

    if str(status_code) == '429':
        quota_type, raw_message = _classify_quota_error(exc)
        logger.warning(
            "[429] %s | attempt=%d/5 sleep=%.0fs | api_message=%r",
            quota_type, attempt, sleep_secs, raw_message[:200],
        )
    else:
        logger.warning(
            "[%s] %s | attempt=%d/5 sleep=%.0fs",
            status_code, type(exc).__name__, attempt, sleep_secs,
        )


@dataclass
class ImagePrompt:
    """A translated prompt ready for the painter."""

    prompt_text: str
    aspect_ratio: str
    source_block: MermaidBlock


class MermaidTranslator:
    """Translate a MermaidBlock into an ImagePrompt via Gemini."""

    def __init__(self, config: VertexConfig, template: StyleTemplate) -> None:
        self._config = config
        self._template = template
        self._client = None

    def _init_client(self):
        """Initialize google-genai client with Vertex AI backend."""
        try:
            from google import genai
            from google.genai import types
            return genai.Client(
                vertexai=True,
                project=self._config.project_id,
                location=self._config.location,
                http_options=types.HttpOptions(timeout=120_000),  # text gen: 2 min max (ms)
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

    def _build_fallback_prompt(
        self,
        block: MermaidBlock,
        *,
        aspect_ratio: str | None = None,
    ) -> ImagePrompt:
        ratio = aspect_ratio or self._config.aspect_ratio
        fallback = self._template.build_prompt(
            topic=f"{block.diagram_type} diagram",
            mermaid_source=block.source,
            aspect_ratio=ratio,
        )
        return ImagePrompt(
            prompt_text=fallback,
            aspect_ratio=ratio,
            source_block=block,
        )

    def translate(self, block: MermaidBlock) -> ImagePrompt:
        """Translate one MermaidBlock into an ImagePrompt.

        Retries automatically on rate-limit and server errors.
        Falls back to a minimal prompt if Gemini response cannot be parsed.
        """
        if self._config.translation_mode == "fallback":
            logger.info(
                "Using local fallback translation for block %d (type=%s, line=%d)",
                block.index,
                block.diagram_type,
                block.line_number,
            )
            return self._build_fallback_prompt(block)

        logger.info(
            "Translating block %d (type=%s, line=%d)",
            block.index,
            block.diagram_type,
            block.line_number,
        )
        user_message = self._build_user_message(block)

        try:
            response_text = self._call_gemini(user_message)
        except ImportError:
            raise
        except Exception as exc:
            logger.warning(
                "Gemini call failed for block %d after retries: %s. "
                "Using fallback prompt.",
                block.index,
                exc,
            )
            return self._build_fallback_prompt(block)

        return self._parse_response(response_text, block)

    def _assign_characters(self, mermaid_source: str) -> list[tuple[str, str, str, str]]:
        """Extract nodes from mermaid source and assign Chiikawa characters.

        Returns a list of (node_id, label, character_name, role_hint) tuples.
        Assignment rules:
          - First node (initiator) → core_actor (Chiikawa)
          - Diamond nodes (decisions) → logic_processor (Hachiware)
          - Remaining nodes → rotate across all three characters
        """
        char_map = self._template.character_mapping
        roles = ["core_actor", "logic_processor", "high_energy"]
        characters = [char_map[r] for r in roles]

        # Use multiple targeted patterns to avoid group-numbering conflicts.
        # Each pattern: group(1)=node_id, group(2)=label. is_diamond is per-pattern.
        label_patterns: list[tuple[re.Pattern[str], bool]] = [
            # A["label"] or A['label']
            (re.compile(r'\b([A-Za-z_]\w*)\s*\["([^"]+)"\]'), False),
            (re.compile(r"\b([A-Za-z_]\w*)\s*\['([^']+)'\]"), False),
            # A{{"label"}} subgraph-style
            (re.compile(r'\b([A-Za-z_]\w*)\s*\{\{"([^"]+)"\}\}'), False),
            # A{"label"} or A{'label'} diamond
            (re.compile(r'\b([A-Za-z_]\w*)\s*\{"([^"]+)"\}'), True),
            (re.compile(r"\b([A-Za-z_]\w*)\s*\{'([^']+)'\}"), True),
            # A("label") round
            (re.compile(r'\b([A-Za-z_]\w*)\s*\("([^"]+)"\)'), False),
            # A[label] unquoted bracket
            (re.compile(r'\b([A-Za-z_]\w*)\s*\[([^\]"\']+)\]'), False),
            # A{label} unquoted diamond
            (re.compile(r'\b([A-Za-z_]\w*)\s*\{([^}"\']+)\}'), True),
        ]

        seen_ids: dict[str, str] = {}   # id -> label (insertion-ordered)
        diamond_ids: set[str] = set()

        # Scan line by line; skip style/class directives
        skip_prefixes = ("style ", "class ", "classDef ", "linkStyle ")
        for line in mermaid_source.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(p) for p in skip_prefixes):
                continue
            for pattern, is_diamond in label_patterns:
                for m in pattern.finditer(line):
                    node_id, label = m.group(1), m.group(2).strip()
                    if not label:
                        label = node_id
                    if node_id not in seen_ids:
                        seen_ids[node_id] = label
                    if is_diamond:
                        diamond_ids.add(node_id)

        if not seen_ids:
            return []

        node_ids = list(seen_ids.keys())
        first_id = node_ids[0]

        assignments: list[tuple[str, str, str, str]] = []
        branch_counter = 0  # rotates across remaining (non-decision) nodes

        for node_id in node_ids:
            label = seen_ids[node_id]
            if node_id == first_id:
                char = characters[0]          # Chiikawa — initiator
                role_hint = "initiator"
            elif node_id in diamond_ids:
                char = characters[1]          # Hachiware — decision
                role_hint = "decision"
            else:
                char = characters[branch_counter % len(characters)]
                role_hint = ""
                branch_counter += 1
            assignments.append((node_id, label, char, role_hint))

        return assignments

    def _build_user_message(self, block: MermaidBlock) -> str:
        base = (
            f"Please analyse this Mermaid diagram and produce the Chiikawa "
            f"image prompt as instructed.\n\n"
            f"Diagram type: {block.diagram_type}\n\n"
            f"```mermaid\n{block.source}\n```"
        )

        assignments = self._assign_characters(block.source)
        if not assignments:
            return base

        lines = [
            "",
            "## Suggested Character Assignment",
            "Based on the diagram structure, here is a recommended character mapping.",
            "Follow this as your primary guide to ensure visual variety across nodes:",
        ]
        for node_id, label, char, role_hint in assignments:
            hint = f" [{role_hint}]" if role_hint else ""
            lines.append(f"- {node_id} \"{label}\" → {char}{hint}")
        lines.append(
            "\nPlease ensure different characters are used across parallel branches "
            "to add visual variety. Do NOT assign the same character to all branches."
        )

        return base + "\n".join(lines)

    @retry(
        retry=retry_if_exception(lambda exc: not isinstance(exc, ImportError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        before_sleep=_before_sleep_quota,
        reraise=True,
    )
    def _call_gemini(self, user_message: str) -> str:
        """Raw Gemini API call with tenacity retry."""
        from google.genai import types

        response = self._get_client().models.generate_content(
            model=self._config.gemini_model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=self._template.get_system_instruction(),
            ),
        )
        return response.text

    def _parse_response(self, response_text: str, block: MermaidBlock) -> ImagePrompt:
        """Parse Gemini response; extract aspect ratio and prompt body."""
        lines = response_text.strip().splitlines()

        aspect_ratio = self._config.aspect_ratio
        prompt_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.upper().startswith("ASPECT_RATIO:"):
                candidate = stripped.split(":", 1)[1].strip()
                if candidate in _VALID_RATIOS:
                    aspect_ratio = candidate
                else:
                    logger.warning(
                        "Gemini returned unknown aspect ratio '%s', using default '%s'",
                        candidate,
                        _DEFAULT_RATIO,
                    )
                    aspect_ratio = _DEFAULT_RATIO
                prompt_start = i + 1
                break

        prompt_text = "\n".join(lines[prompt_start:]).strip()

        if not prompt_text:
            logger.warning(
                "Gemini returned empty prompt for block %d; using fallback.",
                block.index,
            )
            prompt_text = self._build_fallback_prompt(
                block,
                aspect_ratio=aspect_ratio,
            ).prompt_text

        return ImagePrompt(
            prompt_text=prompt_text,
            aspect_ratio=aspect_ratio,
            source_block=block,
        )
