"""
Chiikawa official manga style template for m2c_pipeline.

Character mapping:
  - Core Actor (trigger/initiator)     -> Chiikawa (吉伊)
  - Logic Processor (narrator/explainer) -> Hachiware (小八)
  - Loop / Exception / High-energy logic -> Usagi (乌萨奇)
"""

from .base import StyleTemplate


_LABEL_PATTERNS = (
    r'\b([A-Za-z_]\w*)\s*\["([^"]+)"\]',
    r"\b([A-Za-z_]\w*)\s*\['([^']+)'\]",
    r'\b([A-Za-z_]\w*)\s*\{\{"([^"]+)"\}\}',
    r'\b([A-Za-z_]\w*)\s*\{"([^"]+)"\}',
    r"\b([A-Za-z_]\w*)\s*\{'([^']+)'\}",
    r'\b([A-Za-z_]\w*)\s*\("([^"]+)"\)',
    r'\b([A-Za-z_]\w*)\s*\[([^\]"\']+)\]',
    r'\b([A-Za-z_]\w*)\s*\{([^}"\']+)\}',
)


# Structured template — injected into Gemini system instruction
_TEMPLATE_SKELETON = """
Chiikawa official manga style educational illustration, [ASPECT_RATIO], explaining [TOPIC].

=== TITLE ===
"[MAIN_TITLE]" — one short Chinese title only, single line, inside a solid pale rounded pill box with generous padding; dark charcoal bold rounded sans-serif; NO glow, NO gradient text, NO decorative text around the title

=== SCENE & LAYOUT ===
Layout: [LAYOUT_TYPE] (e.g., problem-solution bridge crossing a gap / circular lifecycle flow / structured comparison table with checks and crosses / "do vs don't" split panel / input-process-output equation / vertical feature list / fishbone cause-effect diagram / narrowing funnel chart / iceberg surface-vs-hidden diagram / winding roadmap journey / layered technology stack, based on the logic of the MAIN CONTENT below)

Background: Soft gradient cream (#FFF8E7) to [THEME_COLOR], minimal [DECORATIVE_ELEMENTS], keep the area behind title and labels visually clean

=== MAIN CONTENT ===
Use official Chiikawa characters such as Chiikawa / Hachiware / Usagi with clearly different appearances and roles
[CONTENT_SECTION_1]
Character: [CHARACTER_NAME]
- [CHARACTER_ACTION_AND_EXPRESSION]
- [PROPS_OR_ITEMS]
Visual: [KEY_VISUAL_ELEMENT]
Label: "[LABEL_TEXT]" — one short pure-Chinese label, single line, 1–4 Chinese characters only, inside a solid light rounded pill/box with generous padding; dark charcoal bold rounded sans-serif; crisp edge, no transparency, no texture, no glow

[CONTENT_SECTION_2]
[Similar structure as above]

[CONTENT_SECTION_N]
[Continue as needed]

=== CHIIKAWA STYLE ===
Official Chiikawa aesthetic: round bodies, large sparkly eyes, pink blush marks, tiny limbs, super deformed proportions, gentle line art

=== TEXT RENDERING ===
Typography rules (CRITICAL — apply to every rendered title or label):
- Render only 1 short Chinese title and 2–4 short Chinese labels total across the whole image
- Render only pure Chinese text in the image; do NOT render English, roman letters, parentheses, arrows, mixed-language labels, or punctuation-heavy strings
- Every rendered label must be single-line and 1–4 Chinese characters; abbreviate long Mermaid labels into short Chinese summaries
- Do NOT render dialogue, speech bubbles, paragraph annotations, callout paragraphs, or key concept boxes in the image
- Title and labels must sit inside solid light pill boxes with generous padding, clean edges, and high contrast; NO transparency, NO textured text backgrounds, NO glow on labels
- Font: bold (600–700) rounded sans-serif; NO thin, cursive, handwritten, or brush-stroke fonts
- Text color: dark charcoal (#2D2D2D) on a solid pale background; minimum contrast 4.5:1
- Chinese characters: every stroke and radical must be Fully Formed and Vector-style clarity — no hairline breaks, no missing components, no pixelation
- Smooth anti-aliased edges; absolutely NO cracked, fragmented, glitchy, blurry, or overlapping text
- Negative constraints: no handwritten text, no stylized calligraphy, no fragmented strokes, no overlapping text, no text on textured background, no glow on labels

=== MOOD ===
[EMOTIONAL_TONE], [EDUCATIONAL_GOAL], cute but informative

Quality: High-quality Chiikawa illustration, clear visual hierarchy, [PURPOSE]
""".strip()

_SYSTEM_INSTRUCTION = """
You are an expert Chiikawa manga artist and educational illustrator.
Your task: analyse the given Mermaid diagram and produce a complete image generation prompt in the structured Chiikawa template format below.

## Text Minimization (HIGHEST PRIORITY)
- The image should render as little text as possible: exactly 1 short Chinese title and only 2–4 short Chinese labels in total across the whole image.
- Render only pure Chinese text in the image. Do NOT render English, roman letters, parentheses, arrows, punctuation-heavy strings, or bilingual text inside the image.
- Preserve the meaning of Mermaid node text, but abbreviate long rendered labels into short Chinese summaries of 1–4 Chinese characters.
- Move long explanations into composition, character action, props, icons, and spatial layout instead of extra text.
- Do NOT render dialogue, speech bubbles, paragraph annotations, callout paragraphs, or key concept boxes in the image.
- **STRICTLY FORBIDDEN**: Do NOT use Japanese script anywhere in the prompt. This includes internal prompt wording, rendered labels, titles, and any text intended for rendering.

## Character Mapping Rules
Use official Chiikawa characters with distinct roles and clearly different visual anchors:
- **Chiikawa (吉伊)**: the trigger/initiator — small, round, white marshmallow body, timid but brave, dot eyes, pink blush (三).
- **Hachiware (小八)**: the explainer/decision-maker — white cat with muted dusty-blue (#81A9D3) ears and head markings; the blue fur parts at the forehead center in a clean inverted-V (八-shaped) split revealing the white face beneath (this is a smooth fur-color boundary, NOT a crack or line); calm and reliable, holds a clipboard, pointer, or other explanation prop.
- **Usagi (乌萨奇)**: high-energy/action/conclusion — tall light-beige rabbit, long ears, wide round eyes, energetic jumping or action-heavy pose.
- If the user message includes a "Graph Classification" or "Suggested Character Assignment" section, follow it as the primary guide for node-to-character mapping.
- For a simple linear 3-node flow explicitly classified in the user message, MAIN CONTENT MUST have exactly 3 major sections and the Character lines MUST use Chiikawa (吉伊), Hachiware (小八), and Usagi (乌萨奇) exactly once each.
- For a simple linear 2-node flow explicitly classified in the user message, use 2 different main characters and do not repeat a character.
- For non-simple diagrams, introduce Chiikawa, Hachiware, and Usagi at least once before reusing any character.
- Never place two visually identical Chiikawa-like white blob characters in adjacent main sections. Distinguish each main character with species, colors, face details, props, and pose.
- In every main section, restate the character's visible identity cues inside the action or visual description so the image model keeps them distinct.

## Aspect Ratio Selection
- Simple linear flow (≤5 nodes)  → recommend "1:1"
- Standard content / blog illustration → recommend "4:3"
- Wide horizontal flowchart / roadmap → recommend "16:9"
- Tall vertical or stacked layout → recommend "9:16"
State your recommendation on the FIRST line of your response as: ASPECT_RATIO: <value>

## Output Format
After the ASPECT_RATIO line, output the filled-in Chiikawa template EXACTLY as shown below.
Do NOT add any commentary, markdown fences, or extra text outside the template.

ASPECT_RATIO: <1:1 | 4:3 | 16:9 | 9:16>

""" + _TEMPLATE_SKELETON + """

## Filling Instructions
- [TOPIC]: a short description of what the diagram explains
- [MAIN_TITLE]: use a concise Chinese title, ideally 2–4 Chinese characters
- [LAYOUT_TYPE]: pick the best layout descriptor for this diagram's shape
- [THEME_COLOR]: a complementary pastel hex colour
- Fill each [CONTENT_SECTION] with: Character, Action, Props, Visual, and one short Label (in Chinese)
- For each section, explicitly mention the character's visual anchor traits so the rendered cast stays distinct.
- Use only 2–4 Label lines total across the whole image and omit a label when the visual cue is enough.
- Keep every rendered label single-line and ≤ 4 Chinese characters; use pure Chinese only, with no parentheses or English.
"""


class ChiikawaTemplate(StyleTemplate):
    """Chiikawa manga style illustration template."""

    @property
    def name(self) -> str:
        return "chiikawa"

    @property
    def character_mapping(self) -> dict[str, str]:
        return {
            "core_actor": "Chiikawa (吉伊)",
            "logic_processor": "Hachiware (小八)",
            "high_energy": "Usagi (乌萨奇)",
        }

    def get_system_instruction(self) -> str:
        return _SYSTEM_INSTRUCTION

    def _extract_nodes(self, mermaid_source: str) -> tuple[list[str], set[str]]:
        """Extract labeled nodes in first-seen order plus diamond nodes."""
        import re

        node_ids: list[str] = []
        diamond_ids: set[str] = set()

        for line in mermaid_source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("style ", "class ", "classDef ", "linkStyle ")):
                continue
            for pattern in _LABEL_PATTERNS:
                for match in re.finditer(pattern, line):
                    node_id = match.group(1)
                    if node_id not in node_ids:
                        node_ids.append(node_id)
                    if "{" in match.group(0) and "[[" not in match.group(0):
                        diamond_ids.add(node_id)

        return node_ids, diamond_ids

    def _extract_edges(self, mermaid_source: str, known_node_ids: set[str]) -> list[tuple[str, str]]:
        """Extract minimal directed edges between known labeled nodes."""
        import re

        edge_re = re.compile(
            r'\b([A-Za-z_]\w*)\b\s*[-.=]+(?:\|[^|]+\|)?[-.=]*>\s*\b([A-Za-z_]\w*)\b'
        )
        normalized_patterns = [re.compile(pattern) for pattern in _LABEL_PATTERNS]
        edges: list[tuple[str, str]] = []

        for raw_line in mermaid_source.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith(("style ", "class ", "classDef ", "linkStyle ")):
                continue
            normalized = raw_line
            for pattern in normalized_patterns:
                normalized = pattern.sub(r"\1", normalized)
            for source_id, target_id in edge_re.findall(normalized):
                if source_id in known_node_ids and target_id in known_node_ids:
                    edges.append((source_id, target_id))

        return edges

    def _is_simple_linear_flow(self, mermaid_source: str) -> tuple[bool, int, bool]:
        """Return (is_simple_linear, node_count, middle_is_diamond)."""
        node_ids, diamond_ids = self._extract_nodes(mermaid_source)
        if len(node_ids) not in (2, 3):
            return False, len(node_ids), False

        first_line = ""
        for line in mermaid_source.splitlines():
            if line.strip():
                first_line = line.strip().lower()
                break
        if not (first_line.startswith("flowchart") or first_line.startswith("graph")):
            return False, len(node_ids), False

        edges = self._extract_edges(mermaid_source, set(node_ids))
        if len(edges) != len(node_ids) - 1:
            return False, len(node_ids), False

        indegree = {node_id: 0 for node_id in node_ids}
        outdegree = {node_id: 0 for node_id in node_ids}
        next_node: dict[str, str] = {}

        for source_id, target_id in edges:
            if source_id == target_id or source_id in next_node:
                return False, len(node_ids), False
            indegree[target_id] += 1
            outdegree[source_id] += 1
            next_node[source_id] = target_id

        if any(indegree[node_id] > 1 or outdegree[node_id] > 1 for node_id in node_ids):
            return False, len(node_ids), False

        start_nodes = [node_id for node_id in node_ids if indegree[node_id] == 0]
        end_nodes = [node_id for node_id in node_ids if outdegree[node_id] == 0]
        if len(start_nodes) != 1 or len(end_nodes) != 1:
            return False, len(node_ids), False

        order: list[str] = []
        current = start_nodes[0]
        visited: set[str] = set()
        while current not in visited:
            order.append(current)
            visited.add(current)
            if current not in next_node:
                break
            current = next_node[current]

        if len(order) != len(node_ids):
            return False, len(node_ids), False

        middle_is_diamond = len(order) >= 2 and order[1] in diamond_ids
        return True, len(order), middle_is_diamond

    def build_prompt(self, topic: str, mermaid_source: str, aspect_ratio: str) -> str:
        """Fallback prompt when Gemini output cannot be parsed."""
        is_simple_linear, node_count, middle_is_diamond = self._is_simple_linear_flow(
            mermaid_source
        )
        simple_cast_line = (
            "This simple linear 3-node flow uses exactly three distinct main characters: "
            "Chiikawa at the start, Hachiware in the middle, and Usagi at the end. "
            if is_simple_linear and node_count == 3
            else (
                "This simple linear 2-node flow uses two different main characters with no repetition. "
                "Chiikawa starts the flow and "
                + (
                    "Hachiware resolves the second decision node. "
                    if middle_is_diamond
                    else "Usagi completes the second action node. "
                )
                if is_simple_linear and node_count == 2
                else "Introduce Chiikawa, Hachiware, and Usagi before reusing any character in complex diagrams. "
            )
        )
        return (
            f"Chiikawa official manga style educational illustration, "
            f"aspect ratio {aspect_ratio}, explaining {topic}. "
            f"{simple_cast_line}"
            f"Soft gradient background from cream (#FFF8E7) to light blue (#E8F4FD), "
            f"minimal twinkling stars and tiny hearts as decoration, while keeping the text areas clean. "
            f"Render only one short Chinese title and two to four short Chinese labels total. "
            f"All rendered text must be pure Chinese, single-line, and one to four Chinese characters only; "
            f"abbreviate long Mermaid labels into short Chinese summaries. "
            f"Do not render dialogue, speech bubbles, paragraph annotations, or key concept boxes. "
            f"Title and labels must sit inside solid pale rounded pill boxes with generous padding, "
            f"dark charcoal bold rounded sans-serif, clean edges, high contrast, no transparency, no texture, and no glow. "
            f"Chiikawa (white rounded body, black dot eyes, pink triple-line blush) "
            f"stands at the start looking curious. "
            f"Hachiware (white cat with dusty-blue (#81A9D3) ear and head markings, the blue fur parts in an inverted-V at the forehead center revealing the white face — a smooth color boundary with no lines or cracks; holding a pointer) "
            f"explains from the middle. "
            f"Usagi (light-beige rabbit with long ears and wide round eyes) "
            f"jumps excitedly at the end. "
            f"Nodes as soft rounded bubbles, hand-drawn style arrows. "
            f"Official manga-inspired line art: ultra-minimalist thin black outlines, no shading, "
            f"flat pastel fills, 1:1 head-to-body ratio, warm and healing. "
            f"Chinese characters Fully Formed with Vector-style clarity, no cracked or missing strokes, "
            f"no handwritten text, no stylized calligraphy, no fragmented strokes, no overlapping text, "
            f"no text on textured background, and no glow on labels. "
            f"Keep each character visually distinct by repeating species, colors, face details, "
            f"props, and pose cues in every main section."
        )
