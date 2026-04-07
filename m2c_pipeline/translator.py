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
_SKIP_PREFIXES = ("style ", "class ", "classDef ", "linkStyle ")
_EDGE_RE = re.compile(
    r'\b([A-Za-z_]\w*)\b\s*[-.=]+(?:\|[^|]+\|)?[-.=]*>\s*\b([A-Za-z_]\w*)\b'
)
_LABEL_PATTERNS: list[tuple[re.Pattern[str], bool]] = [
    (re.compile(r'\b([A-Za-z_]\w*)\s*\["([^"]+)"\]'), False),
    (re.compile(r"\b([A-Za-z_]\w*)\s*\['([^']+)'\]"), False),
    (re.compile(r'\b([A-Za-z_]\w*)\s*\{\{"([^"]+)"\}\}'), False),
    (re.compile(r'\b([A-Za-z_]\w*)\s*\{"([^"]+)"\}'), True),
    (re.compile(r"\b([A-Za-z_]\w*)\s*\{'([^']+)'\}"), True),
    (re.compile(r'\b([A-Za-z_]\w*)\s*\("([^"]+)"\)'), False),
    (re.compile(r'\b([A-Za-z_]\w*)\s*\[([^\]"\']+)\]'), False),
    (re.compile(r'\b([A-Za-z_]\w*)\s*\{([^}"\']+)\}'), True),
]


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


@dataclass(frozen=True)
class DiagramAnalysis:
    """Minimal Mermaid structure used for prompt guidance decisions."""

    node_labels: dict[str, str]
    diamond_ids: set[str]
    edges: list[tuple[str, str]]
    simple_linear_order: list[str]

    @property
    def is_simple_linear(self) -> bool:
        return bool(self.simple_linear_order)


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

    def _extract_nodes(self, mermaid_source: str) -> tuple[dict[str, str], set[str]]:
        """Return labeled node ids in first-seen order plus diamond node ids."""
        seen_ids: dict[str, str] = {}
        diamond_ids: set[str] = set()

        for line in mermaid_source.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(prefix) for prefix in _SKIP_PREFIXES):
                continue
            for pattern, is_diamond in _LABEL_PATTERNS:
                for match in pattern.finditer(line):
                    node_id, label = match.group(1), match.group(2).strip()
                    if not label:
                        label = node_id
                    if node_id not in seen_ids:
                        seen_ids[node_id] = label
                    if is_diamond:
                        diamond_ids.add(node_id)

        return seen_ids, diamond_ids

    def _extract_edges(
        self,
        mermaid_source: str,
        known_node_ids: set[str],
    ) -> list[tuple[str, str]]:
        """Extract directed edges between already-known labeled nodes."""
        edges: list[tuple[str, str]] = []

        for raw_line in mermaid_source.splitlines():
            stripped = raw_line.strip()
            if any(stripped.startswith(prefix) for prefix in _SKIP_PREFIXES):
                continue

            normalized = raw_line
            for pattern, _ in _LABEL_PATTERNS:
                normalized = pattern.sub(r"\1", normalized)

            for source_id, target_id in _EDGE_RE.findall(normalized):
                if source_id in known_node_ids and target_id in known_node_ids:
                    edges.append((source_id, target_id))

        return edges

    def _analyze_diagram(
        self,
        mermaid_source: str,
        diagram_type: str,
    ) -> DiagramAnalysis:
        """Classify the diagram for prompt constraints without full graph parsing."""
        node_labels, diamond_ids = self._extract_nodes(mermaid_source)
        if not node_labels:
            return DiagramAnalysis(
                node_labels={},
                diamond_ids=set(),
                edges=[],
                simple_linear_order=[],
            )

        edges = self._extract_edges(mermaid_source, set(node_labels))
        if diagram_type not in {"flowchart", "graph"}:
            return DiagramAnalysis(
                node_labels=node_labels,
                diamond_ids=diamond_ids,
                edges=edges,
                simple_linear_order=[],
            )

        node_ids = list(node_labels.keys())
        node_count = len(node_ids)
        if node_count not in (2, 3) or len(edges) != node_count - 1:
            return DiagramAnalysis(
                node_labels=node_labels,
                diamond_ids=diamond_ids,
                edges=edges,
                simple_linear_order=[],
            )

        indegree = {node_id: 0 for node_id in node_ids}
        outdegree = {node_id: 0 for node_id in node_ids}
        next_node: dict[str, str] = {}

        for source_id, target_id in edges:
            if source_id == target_id:
                return DiagramAnalysis(
                    node_labels=node_labels,
                    diamond_ids=diamond_ids,
                    edges=edges,
                    simple_linear_order=[],
                )
            indegree[target_id] += 1
            outdegree[source_id] += 1
            if source_id in next_node:
                return DiagramAnalysis(
                    node_labels=node_labels,
                    diamond_ids=diamond_ids,
                    edges=edges,
                    simple_linear_order=[],
                )
            next_node[source_id] = target_id

        if any(indegree[node_id] > 1 or outdegree[node_id] > 1 for node_id in node_ids):
            return DiagramAnalysis(
                node_labels=node_labels,
                diamond_ids=diamond_ids,
                edges=edges,
                simple_linear_order=[],
            )

        start_nodes = [node_id for node_id in node_ids if indegree[node_id] == 0]
        end_nodes = [node_id for node_id in node_ids if outdegree[node_id] == 0]
        if len(start_nodes) != 1 or len(end_nodes) != 1:
            return DiagramAnalysis(
                node_labels=node_labels,
                diamond_ids=diamond_ids,
                edges=edges,
                simple_linear_order=[],
            )

        order: list[str] = []
        current = start_nodes[0]
        visited: set[str] = set()
        while current not in visited:
            order.append(current)
            visited.add(current)
            if current not in next_node:
                break
            current = next_node[current]

        if len(order) != node_count or order[-1] != end_nodes[0]:
            return DiagramAnalysis(
                node_labels=node_labels,
                diamond_ids=diamond_ids,
                edges=edges,
                simple_linear_order=[],
            )

        return DiagramAnalysis(
            node_labels=node_labels,
            diamond_ids=diamond_ids,
            edges=edges,
            simple_linear_order=order,
        )

    def _assign_characters(
        self,
        mermaid_source: str,
        diagram_type: str = "flowchart",
    ) -> list[tuple[str, str, str, str]]:
        """Extract nodes from mermaid source and assign Chiikawa characters.

        Returns a list of (node_id, label, character_name, role_hint) tuples.
        For simple 2-3 node linear flowcharts, enforce unique characters.
        For more complex graphs, introduce all three characters before reuse.
        """
        char_map = self._template.character_mapping
        core_actor = char_map["core_actor"]
        logic_processor = char_map["logic_processor"]
        high_energy = char_map["high_energy"]
        characters = [core_actor, logic_processor, high_energy]
        analysis = self._analyze_diagram(mermaid_source, diagram_type)

        if not analysis.node_labels:
            return []

        assignments: list[tuple[str, str, str, str]] = []

        if analysis.is_simple_linear:
            order = analysis.simple_linear_order
            if len(order) == 2:
                simple_chars = [
                    core_actor,
                    logic_processor if order[1] in analysis.diamond_ids else high_energy,
                ]
            else:
                simple_chars = [core_actor, logic_processor, high_energy]

            for index, node_id in enumerate(order):
                label = analysis.node_labels[node_id]
                role_hint = ""
                if index == 0:
                    role_hint = "initiator"
                elif node_id in analysis.diamond_ids:
                    role_hint = "decision"
                elif index == len(order) - 1:
                    role_hint = "conclusion"
                assignments.append((node_id, label, simple_chars[index], role_hint))

            return assignments

        used_characters: set[str] = set()
        reuse_index = 0
        preferred_intro_order = [logic_processor, high_energy, core_actor]

        for index, node_id in enumerate(analysis.node_labels):
            label = analysis.node_labels[node_id]
            role_hint = ""
            if index == 0:
                char = core_actor
                role_hint = "initiator"
            elif len(used_characters) < len(characters):
                if node_id in analysis.diamond_ids and logic_processor not in used_characters:
                    char = logic_processor
                    role_hint = "decision"
                else:
                    char = next(
                        candidate
                        for candidate in preferred_intro_order
                        if candidate not in used_characters
                    )
                    if node_id in analysis.diamond_ids:
                        role_hint = "decision"
            else:
                if node_id in analysis.diamond_ids:
                    char = logic_processor
                    role_hint = "decision"
                else:
                    char = characters[reuse_index % len(characters)]
                    reuse_index += 1
            assignments.append((node_id, label, char, role_hint))
            used_characters.add(char)

        return assignments

    def _build_user_message(self, block: MermaidBlock) -> str:
        analysis = self._analyze_diagram(block.source, block.diagram_type)
        base = (
            f"Please analyse this Mermaid diagram and produce the Chiikawa "
            f"image prompt as instructed.\n\n"
            f"Diagram type: {block.diagram_type}\n\n"
            f"```mermaid\n{block.source}\n```"
        )

        assignments = self._assign_characters(block.source, block.diagram_type)
        if not assignments:
            return base

        lines = [
            "",
            "## Graph Classification",
        ]
        if analysis.is_simple_linear:
            lines.extend(
                [
                    "This is a simple linear flowchart with 2-3 labeled main nodes.",
                    "Use unique-first character assignment for the main sections.",
                ]
            )
            if len(analysis.simple_linear_order) == 3:
                lines.append(
                    "Use exactly 3 different main characters, one per node/section. "
                    "Do not repeat any character."
                )
        else:
            lines.extend(
                [
                    "This diagram is not classified as a simple 2-3 node linear flowchart.",
                    "Follow the suggested mapping and prefer introducing all three main "
                    "characters before any reuse.",
                ]
            )

        lines.extend(
            [
                "",
                "## Suggested Character Assignment",
                "Based on the diagram structure, here is a recommended character mapping.",
                "Follow this as your primary guide to ensure visual variety across nodes:",
            ]
        )
        for node_id, label, char, role_hint in assignments:
            hint = f" [{role_hint}]" if role_hint else ""
            lines.append(f"- {node_id} \"{label}\" → {char}{hint}")
        if analysis.is_simple_linear and len(analysis.simple_linear_order) == 3:
            lines.append(
                "\nTreat these three nodes as three distinct main sections with one "
                "different character per section."
            )
        else:
            lines.append(
                "\nDo not reuse a character until Chiikawa, Hachiware, and Usagi have "
                "all appeared at least once."
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
